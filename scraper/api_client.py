"""GraphQL API client for robota.ua."""

import asyncio
import logging
from typing import Optional
from curl_cffi.requests import AsyncSession
import config
from .rate_limiter import RateLimiter

logger = logging.getLogger(__name__)

HEADERS = {
    "origin": config.REFERER.rstrip("/"),
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
    "variables": {"id": None, "trackView": False},
    "query": """query getPublishedVacancy($id: ID!, $trackView: Boolean) {
  publishedVacancy(id: $id, trackView: $trackView) {
    ...PublishedVacancyPage
    __typename
  }
}

fragment PublishedVacancyPage on Vacancy {
  fullDescription
  __typename
}""",
}


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


async def get_base_request(session: AsyncSession, page: int) -> Optional[list[dict]]:
    """
    Fetch list of vacancies for a given page.

    Returns:
        List of vacancy items or None if request failed.
    """
    payload = get_next_payload(page)

    for attempt in range(config.MAX_RETRIES):
        try:
            response = await session.post(
                config.BASE_URL,
                headers=HEADERS,
                json=payload,
                timeout=config.REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            json_data = response.json()

            if "errors" in json_data:
                logger.warning(f"API returned errors: {json_data['errors']}")
                return None

            items = json_data.get("data", {}).get("publishedVacancies", {}).get("items")
            return items

        except Exception as e:
            logger.warning(
                f"Request attempt {attempt + 1}/{config.MAX_RETRIES} failed for page {page}: {e}"
            )
            if attempt < config.MAX_RETRIES - 1:
                await asyncio.sleep(config.RETRY_DELAY)
            else:
                logger.error(f"All retry attempts failed for page {page}")
                return None


async def get_vacancy_description(
    session: AsyncSession,
    vacancy_id: str,
    semaphore: asyncio.Semaphore,
    rate_limiter: RateLimiter,
) -> tuple[str, Optional[str]]:
    """
    Fetch single vacancy description with concurrency control.

    Returns:
        Tuple of (vacancy_id, description or None)
    """
    async with semaphore:
        await rate_limiter.acquire()

        payload = create_detail_payload(vacancy_id)

        for attempt in range(config.MAX_RETRIES):
            try:
                response = await session.post(
                    config.BASE_DETAIL_URL,
                    headers=HEADERS,
                    json=payload,
                    timeout=config.REQUEST_TIMEOUT,
                )
                response.raise_for_status()
                data = response.json()
                description = (
                    data.get("data", {})
                    .get("publishedVacancy", {})
                    .get("fullDescription")
                )

                if description:
                    logger.info(f"✓ Fetched description for vacancy {vacancy_id}")
                    return vacancy_id, description
                else:
                    logger.warning(f"Empty description for vacancy {vacancy_id}")
                    return vacancy_id, ""

            except Exception as e:
                logger.warning(
                    f"Error fetching vacancy {vacancy_id} (attempt {attempt + 1}/{config.MAX_RETRIES}): {e}"
                )
                if attempt < config.MAX_RETRIES - 1:
                    await asyncio.sleep(config.RETRY_DELAY)

        logger.error(
            f"Failed to fetch vacancy {vacancy_id} after {config.MAX_RETRIES} attempts"
        )
        return vacancy_id, None
