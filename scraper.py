import asyncio
from curl_cffi.requests import AsyncSession
from pathlib import Path
from itertools import batched
import re
from bs4 import BeautifulSoup
import json
import csv
import time
import logging
from typing import Optional
import config


logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

HEADERS = {
    "origin": config.REFERER.rstrip('/'),
    "referer": config.REFERER,
    "content-type": "application/json",
}

LIST_PAYLOAD = {
    "operationName": "getPublishedVacanciesList",
    "variables": {
        "pagination": {"count": config.RESULTS_PER_PAGE, "page": 0},
        "filter": {
            "keywords": config.SEARCH_KEYWORD,
            "militaryVacancyDisplayMode": "APPENDED",
            "metroBranches": [],
            "additionalKeywords": "",
            "clusterKeywords": [],
            "location": {"longitude": 0, "latitude": 0},
            "salary": 0,
            "districtIds": [],
            "microDistrictIds": [],
            "scheduleIds": [],
            "rubrics": [],
            "showAgencies": True,
            "showOnlyNoCvApplyVacancies": False,
            "showOnlySpecialNeeds": False,
            "showOnlyWithoutExperience": False,
            "showOnlyNotViewed": False,
            "showWithoutSalary": True,
            "isReservation": False,
            "isForVeterans": False,
            "isOfficeWithGenerator": False,
            "isOfficeWithShelter": False,
            "gender": None,
            "branchIds": [],
        },
        "sort": "BY_BUSINESS_SCORE",
        "isBrowser": True,
    },
    "query": """query getPublishedVacanciesList($filter: PublishedVacanciesFilterInput!, $pagination: PublishedVacanciesPaginationInput!, $sort: PublishedVacanciesSortType!) {
      publishedVacancies(filter: $filter, pagination: $pagination, sort: $sort) {
        totalCount
        items {
          ...PublishedVacanciesItem
          __typename
        }
        __typename
      }
    }

    fragment PublishedVacanciesItem on Vacancy {
      id
      title
      description
      salary { amount comment amountFrom amountTo __typename }
      company {
        id logoUrl name
        honors { badge { iconUrl tooltipDescription locations isFavorite __typename } __typename }
        __typename
      }
      city { id name __typename }
      __typename
    }
    """,
}

DETAIL_PAYLOAD_TEMPLATE = {
    "operationName": "getPublishedVacancy",
    "variables": {
        "id": None,
        "trackView": False
    },
    "query": """query getPublishedVacancy($id: ID!, $trackView: Boolean) {
  publishedVacancy(id: $id, trackView: $trackView) {
    ...PublishedVacancyPage
    __typename
  }
}

fragment PublishedVacancyPage on Vacancy {
  fullDescription
  __typename
}"""
}

BASE_URL = config.BASE_URL
BASE_DETAIL_URL = config.BASE_DETAIL_URL
CSV_NAME = config.CSV_FILENAME

# Concurrency control - max concurrent detail requests
MAX_CONCURRENT_DETAILS = config.MAX_CONCURRENT_DETAILS  # Respectful to server - not too many parallel connections
MAX_CONCURRENT_AI_REQUESTS = config.MAX_CONCURRENT_AI_REQUESTS  # Limit AI API concurrent requests


class RateLimiter:
    """Token bucket rate limiter for async requests."""

    def __init__(self, rate: float):
        """
        Args:
            rate: Minimum seconds between requests
        """
        self.rate = rate
        self.last_request = 0
        self._lock = asyncio.Lock()

    async def acquire(self):
        """Wait until we can make another request."""
        async with self._lock:
            now = time.time()
            time_since_last = now - self.last_request

            if time_since_last < self.rate:
                sleep_time = self.rate - time_since_last
                await asyncio.sleep(sleep_time)

            self.last_request = time.time()


def get_next_payload(page: int) -> dict:
    """Create payload for specific page number."""
    payload = LIST_PAYLOAD.copy()
    payload["variables"] = payload["variables"].copy()
    payload["variables"]["pagination"] = payload["variables"]["pagination"].copy()
    payload["variables"]["pagination"]["page"] = page
    return payload


def create_detail_payload(vacancy_id: str) -> dict:
    """Create payload for specific vacancy detail."""
    payload = DETAIL_PAYLOAD_TEMPLATE.copy()
    payload["variables"] = payload["variables"].copy()
    payload["variables"]["id"] = vacancy_id
    return payload


def clean_vacancy_text(html_text: str) -> str:
    """Clean HTML and normalize text."""
    soup = BeautifulSoup(html_text, "html.parser")
    text = soup.get_text(separator=" ")

    text = text.replace(' ', ' ').replace('\t', ' ')
    text = re.sub(r'(\w)\?(\w)', r"\1'\2", text)
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


async def get_vacancy_description(
    session: AsyncSession,
    vacancy_id: str,
    semaphore: asyncio.Semaphore,
    rate_limiter: RateLimiter
) -> tuple[str, Optional[str]]:
    """
    Fetch single vacancy description with concurrency control.

    Returns:
        Tuple of (vacancy_id, description or None)
    """
    async with semaphore:  # Limit concurrent connections
        await rate_limiter.acquire()  # Rate limiting

        payload = create_detail_payload(vacancy_id)

        for attempt in range(config.MAX_RETRIES):
            try:
                response = await session.post(
                    BASE_DETAIL_URL,
                    headers=HEADERS,
                    json=payload,
                    timeout=config.REQUEST_TIMEOUT
                )
                response.raise_for_status()
                data = response.json()
                description = data.get("data", {}).get("publishedVacancy", {}).get("fullDescription")

                if description:
                    logger.info(f"✓ Fetched description for vacancy {vacancy_id}")
                    return vacancy_id, description
                else:
                    logger.warning(f"Empty description for vacancy {vacancy_id}")
                    return vacancy_id, ""

            except Exception as e:
                logger.warning(f"Error fetching vacancy {vacancy_id} (attempt {attempt + 1}/{config.MAX_RETRIES}): {e}")
                if attempt < config.MAX_RETRIES - 1:
                    await asyncio.sleep(config.RETRY_DELAY)

        logger.error(f"Failed to fetch vacancy {vacancy_id} after {config.MAX_RETRIES} attempts")
        return vacancy_id, None


async def get_vacancies_stack_chunk(
    session: AsyncSession,
    chunk: list[tuple[str, str]],
    chunk_idx: int,
    semaphore: asyncio.Semaphore,
    rate_limiter: RateLimiter
) -> dict[str, list[str]]:
    """
    Process one chunk of vacancies with AI extraction.
    Uses unlimited retries until successful.

    Args:
        chunk: List of (vacancy_id, description) tuples
        chunk_idx: Chunk number for logging

    Returns:
        Dictionary mapping vacancy_id to list of technologies
    """
    async with semaphore:  # Limit concurrent AI requests
        await rate_limiter.acquire()  # Rate limiting for AI API

        raw_vacancies = "\n".join([
            f"\n=== VACANCY ID: {id_} ===\n{description}"
            for id_, description in chunk
        ])
        parsed_vacancies = clean_vacancy_text(raw_vacancies)

        attempt = 0

        # Unlimited retries until success
        while True:
            attempt += 1
            try:
                ai_res = await session.post(
                    config.BASE_OPENROUTER_URL,
                    headers=config.OPENROUTER_HEADERS,
                    json={
                        "model": config.MODEL,
                        "messages": [
                            {
                                "role": "user",
                                "content": config.ZERO_PROMPT + parsed_vacancies
                            }
                        ]
                    },
                    timeout=max(100, config.REQUEST_TIMEOUT)
                )

                if ai_res.status_code == 200:
                    ai_data = ai_res.json()
                    ai_answer = ai_data["choices"][0]["message"]["content"]

                    # Extract JSON from response
                    start = ai_answer.find("{")
                    end = ai_answer.rfind("}") + 1

                    if start == -1 or end == 0:
                        logger.warning(f"AI response doesn't contain valid JSON (chunk {chunk_idx}, attempt {attempt})")
                        await asyncio.sleep(0.5)
                        continue

                    data = json.loads(ai_answer[start:end])
                    result = {key: [tech.upper() for tech in data[key]] for key in data}
                    logger.info(f"✓ Successfully parsed AI chunk {chunk_idx} (after {attempt} attempt(s))")
                    return result

                elif ai_res.status_code == 429:
                    # Rate limit - wait longer and retry
                    logger.warning(f"Rate limited (429) for AI chunk {chunk_idx}, waiting 2s before retry (attempt {attempt})")
                    await asyncio.sleep(2.0)
                    continue

                else:
                    logger.warning(f"AI request failed with status {ai_res.status_code} (chunk {chunk_idx}, attempt {attempt})")
                    await asyncio.sleep(0.5)
                    continue

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse AI JSON (chunk {chunk_idx}, attempt {attempt}): {e}")
                await asyncio.sleep(0.5)
                continue

            except Exception as e:
                logger.error(f"AI request error (chunk {chunk_idx}, attempt {attempt}): {e}")
                await asyncio.sleep(1.0)
                continue


async def get_vacancies_stack(
    session: AsyncSession,
    descriptions: dict[str, str]
) -> dict[str, list[str]]:
    """
    Extract technology stacks from descriptions using AI (async with concurrency control).

    Returns:
        Dictionary mapping vacancy_id to list of technologies
    """
    stack = {}

    # Create semaphore and rate limiter for AI requests
    ai_semaphore = asyncio.Semaphore(MAX_CONCURRENT_AI_REQUESTS)
    ai_rate_limiter = RateLimiter(1.0)  # 1 second between AI requests

    # Process chunks concurrently (but with limits)
    chunks = list(batched(descriptions.items(), config.REQUEST_CHUNK))

    tasks = [
        get_vacancies_stack_chunk(session, list(chunk), idx, ai_semaphore, ai_rate_limiter)
        for idx, chunk in enumerate(chunks, 1)
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Merge results
    for result in results:
        if isinstance(result, dict):
            stack.update(result)
        else:
            logger.error(f"AI chunk processing error: {result}")

    return stack


async def get_base_request(
    session: AsyncSession,
    page: int
) -> Optional[list[dict]]:
    """
    Fetch list of vacancies for a given page.

    Returns:
        List of vacancy items or None if request failed.
    """
    payload = get_next_payload(page)

    for attempt in range(config.MAX_RETRIES):
        try:
            response = await session.post(
                BASE_URL,
                headers=HEADERS,
                json=payload,
                timeout=config.REQUEST_TIMEOUT
            )
            response.raise_for_status()
            json_data = response.json()

            if "errors" in json_data:
                logger.warning(f"API returned errors: {json_data['errors']}")
                return None

            items = json_data.get("data", {}).get("publishedVacancies", {}).get("items")
            return items

        except Exception as e:
            logger.warning(f"Request attempt {attempt + 1}/{config.MAX_RETRIES} failed for page {page}: {e}")
            if attempt < config.MAX_RETRIES - 1:
                await asyncio.sleep(config.RETRY_DELAY)
            else:
                logger.error(f"All retry attempts failed for page {page}")
                return None


def write_csv(data: list[dict], path: Path) -> None:
    """Write data to CSV file with proper headers."""
    with open(path, "a", newline="", encoding="utf-8") as cf:
        is_file_empty = path.stat().st_size == 0
        writer = csv.DictWriter(cf, fieldnames=data[0].keys())

        if is_file_empty:
            writer.writeheader()

        writer.writerows(data)


def clean_data(raw_data: list[dict[str, str]]) -> None:
    """Clean and normalize scraped data in-place."""
    for element in raw_data:
        element["id"] = int(element["id"])
        element["description"] = element["description"].replace(" ", " ").strip(" \n\t")
        element["salary"] = (
            element["salary"]["amount"] or None
            if isinstance(element["salary"], dict)
            else None
        )
        element["company"] = (
            element["company"]["name"] if isinstance(element["company"], dict) else None
        )
        element["city"] = (
            element["city"]["name"] if isinstance(element["city"], dict) else None
        )
        element.pop("__typename", None)


async def scraping_async() -> None:
    """Main async scraping function with concurrency control and rate limiting."""
    path = Path(CSV_NAME)

    # Clear file for new data
    try:
        path.unlink(missing_ok=True)
    except PermissionError:
        logger.warning(f"Permission denied to delete {CSV_NAME}, truncating instead")
        with open(CSV_NAME, "w", encoding="utf-8"):
            ...

    logger.info("Starting async scraping process with curl_cffi...")
    logger.info(f"Concurrency limits: {MAX_CONCURRENT_DETAILS} details, {MAX_CONCURRENT_AI_REQUESTS} AI requests")
    total_vacancies = 0

    # Create curl_cffi AsyncSession with browser impersonation
    async with AsyncSession(impersonate="chrome") as session:
        page_number = 0

        while True:
            page_number += 1
            logger.info(f"\n{'='*60}")
            logger.info(f"📄 Scraping page {page_number}...")
            logger.info(f"{'='*60}")

            # Fetch page list
            data = await get_base_request(session, page_number - 1)

            if data is None:
                logger.error("Failed to fetch data, stopping scraper")
                break

            if not data:
                logger.info("No more vacancies found, reached the end")
                break

            logger.info(f"Found {len(data)} vacancies on page {page_number}")

            # Fetch all vacancy descriptions concurrently (with limits)
            semaphore = asyncio.Semaphore(MAX_CONCURRENT_DETAILS)
            rate_limiter = RateLimiter(0.2)  # 0.2s between detail requests (5 req/sec max)

            vacancy_ids = [element["id"] for element in data]

            logger.info(f"Fetching {len(vacancy_ids)} vacancy descriptions (max {MAX_CONCURRENT_DETAILS} concurrent)...")
            tasks = [
                get_vacancy_description(session, vid, semaphore, rate_limiter)
                for vid in vacancy_ids
            ]

            descriptions_results = await asyncio.gather(*tasks)

            # Build description dict
            raw_stack = {}
            for vid, description in descriptions_results:
                raw_stack[vid] = description if description is not None else ""

            success_count = sum(1 for _, desc in descriptions_results if desc)
            logger.info(f"✓ Successfully fetched {success_count}/{len(vacancy_ids)} descriptions")

            # Get AI analysis of tech stacks (async with concurrency control)
            logger.info(f"Processing with AI ({len(raw_stack)} descriptions in chunks of {config.REQUEST_CHUNK})...")
            stacks = await get_vacancies_stack(session, raw_stack)

            # Attach stacks to vacancy data
            for element in data:
                element["stack"] = stacks.get(element["id"], [])

            clean_data(data)
            write_csv(data, path)
            total_vacancies += len(data)
            logger.info(f"✓ Saved {len(data)} vacancies from page {page_number}")

            # Check if last page
            if len(data) < config.RESULTS_PER_PAGE:
                logger.info("Last page reached (partial results)")
                break

            # Rate limiting between pages - be respectful
            logger.info(f"⏳ Waiting {config.REQUEST_DELAY}s before next page...")
            await asyncio.sleep(config.REQUEST_DELAY)

    logger.info(f"\n{'='*60}")
    logger.info(f"✅ Scraping completed! Total vacancies: {total_vacancies}")
    logger.info(f"{'='*60}")


def scraping() -> None:
    """Synchronous wrapper for async scraping function."""
    asyncio.run(scraping_async())


if __name__ == "__main__":
    scraping()
