"""Main scraping orchestration module."""

import asyncio
import logging
from pathlib import Path
from curl_cffi.requests import AsyncSession
import config
from .api_client import get_base_request, get_vacancy_description
from .ai_extractor import get_vacancies_stack
from .data_writer import write_csv, clean_data
from .rate_limiter import RateLimiter

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def scraping_async() -> None:
    """Main async scraping function with concurrency control and rate limiting."""
    path = Path(config.CSV_FILENAME)

    try:
        path.unlink(missing_ok=True)
    except PermissionError:
        logger.warning(
            f"Permission denied to delete {config.CSV_FILENAME}, truncating instead"
        )
        with open(config.CSV_FILENAME, "w", encoding="utf-8"):
            ...

    logger.info("Starting async scraping process with curl_cffi...")
    logger.info(
        f"Concurrency limits: {config.MAX_CONCURRENT_DETAILS} details, {config.MAX_CONCURRENT_AI_REQUESTS} AI requests"
    )
    total_vacancies = 0

    async with AsyncSession(impersonate="chrome") as session:
        page_number = 0

        while True:
            page_number += 1
            logger.info(f"\n{'='*60}")
            logger.info(f"📄 Scraping page {page_number}...")
            logger.info(f"{'='*60}")

            data = await get_base_request(session, page_number - 1)

            if data is None:
                logger.error("Failed to fetch data, stopping scraper")
                break

            if not data:
                logger.info("No more vacancies found, reached the end")
                break

            logger.info(f"Found {len(data)} vacancies on page {page_number}")

            semaphore = asyncio.Semaphore(config.MAX_CONCURRENT_DETAILS)
            rate_limiter = RateLimiter(0.2)

            vacancy_ids = [element["id"] for element in data]

            logger.info(
                f"Fetching {len(vacancy_ids)} vacancy descriptions (max {config.MAX_CONCURRENT_DETAILS} concurrent)..."
            )
            tasks = [
                get_vacancy_description(session, vid, semaphore, rate_limiter)
                for vid in vacancy_ids
            ]

            descriptions_results = await asyncio.gather(*tasks)

            raw_stack = {}
            for vid, description in descriptions_results:
                raw_stack[vid] = description if description is not None else ""

            success_count = sum(1 for _, desc in descriptions_results if desc)
            logger.info(
                f"✓ Successfully fetched {success_count}/{len(vacancy_ids)} descriptions"
            )

            logger.info(
                f"Processing with AI ({len(raw_stack)} descriptions in chunks of {config.REQUEST_CHUNK})..."
            )
            stacks = await get_vacancies_stack(session, raw_stack)

            for element in data:
                element["stack"] = stacks.get(element["id"], [])

            clean_data(data)
            write_csv(data, path)
            total_vacancies += len(data)
            logger.info(f"✓ Saved {len(data)} vacancies from page {page_number}")

            if len(data) < config.RESULTS_PER_PAGE:
                logger.info("Last page reached (partial results)")
                break

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
