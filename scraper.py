from curl_cffi import Session
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
DETAIL_PAYLOAD = {
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


def get_next_payload() -> None:
    """Increment page number in payload."""
    LIST_PAYLOAD["variables"]["pagination"]["page"] += 1


def inject_vacancy_id_in_payload(vacancy_id: str) -> None:
    DETAIL_PAYLOAD["variables"]["id"] = vacancy_id


def get_vacancy_description(session: Session) -> Optional[str]:
    for attempt in range(config.MAX_RETRIES):
        try:
            res = session.post(
                BASE_DETAIL_URL,
                headers=HEADERS,
                json=DETAIL_PAYLOAD,
                timeout=config.REQUEST_TIMEOUT
            )
            res.raise_for_status()
            return res.json().get("data", {}).get("publishedVacancy", {}).get("fullDescription")
        except Exception as e:
            logger.warning(f"Failed to get vacancy description (attempt {attempt + 1}/{config.MAX_RETRIES}): {e}")
            if attempt < config.MAX_RETRIES - 1:
                time.sleep(config.RETRY_DELAY)
            else:
                logger.error("All retry attempts failed for vacancy description")
                return None


def clean_vacancy_text(html_text: str) -> str:
    soup = BeautifulSoup(html_text, "html.parser")
    text = soup.get_text(separator=" ")

    text = text.replace(' ', ' ').replace('\t', ' ')
    text = re.sub(r'(\w)\?(\w)', r"\1'\2", text)
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


# AI Integration
def get_vacancies_stack(session: Session, descriptions: dict[str, str]) -> dict[str, list[str]]:
    stack = {}

    for chunk_idx, chunk in enumerate(batched(descriptions.items(), config.REQUEST_CHUNK), 1):
        raw_vacancies = "\n".join([
            f"\n=== VACANCY ID: {id_} ===\n{description}"
            for id_, description in chunk
        ])
        parsed_vacancies = clean_vacancy_text(raw_vacancies)

        attempt = 0
        max_attempts = max(10, config.MAX_RETRIES)
        success = False

        while attempt < max_attempts and not success:
            attempt += 1
            try:
                ai_res = session.post(
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
                    ai_answer = ai_res.json()["choices"][0]["message"]["content"]
                    start = ai_answer.find("{")
                    end = ai_answer.rfind("}") + 1

                    if start == -1 or end == 0:
                        logger.warning(f"AI response doesn't contain valid JSON (chunk {chunk_idx}, attempt {attempt}/{max_attempts})")
                        time.sleep(min(0.5, config.RETRY_DELAY))
                        continue

                    data = json.loads(ai_answer[start:end])
                    for key in data:
                        stack[key] = [tech.upper() for tech in data[key]]
                    logger.info(f"Successfully parsed chunk {chunk_idx}")
                    success = True

                elif ai_res.status_code == 429:
                    # Rate limit - always retry with exponential backoff
                    logger.warning(f"Rate limited (429) for chunk {chunk_idx}, waiting {retry_after}s before retry")
                    time.sleep(min(0.5, config.RETRY_DELAY))
                    # Don't increment attempt counter for rate limits - keep retrying
                    attempt -= 1
                    continue

                else:
                    logger.warning(f"AI request failed with status {ai_res.status_code} (chunk {chunk_idx}, attempt {attempt}/{max_attempts})")
                    time.sleep(min(0.5, config.RETRY_DELAY))

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse AI JSON response (chunk {chunk_idx}, attempt {attempt}/{max_attempts}): {e}")
                time.sleep(min(0.5, config.RETRY_DELAY))

            except Exception as e:
                logger.error(f"AI request error (chunk {chunk_idx}, attempt {attempt}/{max_attempts}): {e}")
                time.sleep(min(0.5, config.RETRY_DELAY))

        # If all attempts failed, return empty lists for this chunk
        if not success:
            logger.error(f"Failed to process chunk {chunk_idx} after {max_attempts} attempts")
            for id_, _ in chunk:
                stack[id_] = []

    return stack



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


def get_base_request(session: Session) -> Optional[list[dict]]:
    """
    Make request to API with retries and error handling.

    Returns:
        List of vacancy items or None if request failed.
    """
    for attempt in range(config.MAX_RETRIES):
        try:
            response = session.post(BASE_URL, headers=HEADERS, json=LIST_PAYLOAD, timeout=config.REQUEST_TIMEOUT)
            response.raise_for_status()

            json_data = response.json()

            # Check if response contains errors
            if "errors" in json_data:
                logger.warning(f"API returned errors: {json_data['errors']}")
                return None

            # Extract items from response
            return json_data.get("data", {}).get("publishedVacancies", {}).get("items")

        except Exception as e:
            logger.warning(f"Request attempt {attempt + 1}/{config.MAX_RETRIES} failed: {e}")
            if attempt < config.MAX_RETRIES - 1:
                time.sleep(config.RETRY_DELAY)
            else:
                logger.error(f"All retry attempts failed for page {LIST_PAYLOAD['variables']['pagination']['page']}")
                return None


def scraping() -> None:
    """Main scraping function with proper error handling and rate limiting."""
    path = Path(CSV_NAME)

    # Clear file for new data
    try:
        path.unlink(missing_ok=True)
    except PermissionError:
        logger.warning(f"Permission denied to delete {CSV_NAME}, truncating instead")
        with open(CSV_NAME, "w", encoding="utf-8"):
            ...

    logger.info("Starting scraping process...")
    total_vacancies = 0

    # Create curl_cffi session with browser impersonation
    with Session(impersonate="chrome") as session:
        page_number = 0

        while True:
            page_number += 1
            logger.info(f"Scraping page {page_number}...")

            # Make request with error handling
            data = get_base_request(session)

            # Check if we got valid data
            if data is None:
                logger.error("Failed to fetch data, stopping scraper")
                break

            if not data:
                logger.info("No more vacancies found, reached the end")
                break

            # Process vacancy descriptions with rate limiting
            raw_stack = {}
            for idx, element in enumerate(data, 1):
                inject_vacancy_id_in_payload(element["id"])
                description = get_vacancy_description(session)

                if description:
                    logger.info(f"{idx} Success to get detail vacancy description, id: {element['id']}")
                    raw_stack[element["id"]] = description
                else:
                    logger.warning(f"Failed to get description for vacancy {element['id']}, skipping")
                    raw_stack[element["id"]] = ""

                # Rate limiting between detail requests (respect the server)
                if idx < len(data):
                    time.sleep(0.5)

            # Get AI analysis of tech stacks
            stacks = get_vacancies_stack(session, raw_stack)

            # Attach stacks to vacancy data
            for element in data:
                element["stack"] = stacks.get(element["id"], [])

            clean_data(data)
            write_csv(data, path)
            total_vacancies += len(data)
            logger.info(f"Saved {len(data)} vacancies from page {page_number}")

            # Check if this is the last page (less than expected count)
            if len(data) < config.RESULTS_PER_PAGE:
                logger.info("Last page reached (partial results)")
                break

            # Increment page for next iteration
            get_next_payload()

            # Rate limiting: be respectful to the server
            logger.info(f"Waiting {config.REQUEST_DELAY}s before next page request...")
            time.sleep(config.REQUEST_DELAY)

    logger.info(f"Scraping completed! Total vacancies scraped: {total_vacancies}")


if __name__ == "__main__":
    scraping()
