"""AI-powered technology extraction from job descriptions."""

import asyncio
import json
import logging
from itertools import batched
from curl_cffi.requests import AsyncSession
import config
from .rate_limiter import RateLimiter
from .text_processor import clean_vacancy_text

logger = logging.getLogger(__name__)


async def get_vacancies_stack_chunk(
    session: AsyncSession,
    chunk: list[tuple[str, str]],
    chunk_idx: int,
    semaphore: asyncio.Semaphore,
    rate_limiter: RateLimiter,
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
    async with semaphore:
        await rate_limiter.acquire()

        raw_vacancies = "\n".join(
            [
                f"\n=== VACANCY ID: {id_} ===\n{description}"
                for id_, description in chunk
            ]
        )
        parsed_vacancies = clean_vacancy_text(raw_vacancies)

        attempt = 0

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
                                "content": config.ZERO_PROMPT + parsed_vacancies,
                            }
                        ],
                    },
                    timeout=max(100, config.REQUEST_TIMEOUT),
                )

                if ai_res.status_code == 200:
                    ai_data = ai_res.json()
                    ai_answer = ai_data["choices"][0]["message"]["content"]

                    start = ai_answer.find("{")
                    end = ai_answer.rfind("}") + 1

                    if start == -1 or end == 0:
                        logger.warning(
                            f"AI response doesn't contain valid JSON (chunk {chunk_idx}, attempt {attempt})"
                        )
                        await asyncio.sleep(0.5)
                        continue

                    data = json.loads(ai_answer[start:end])
                    result = {key: [tech.upper() for tech in data[key]] for key in data}
                    logger.info(
                        f"✓ Successfully parsed AI chunk {chunk_idx} (after {attempt} attempt(s))"
                    )
                    return result

                elif ai_res.status_code == 429:
                    logger.warning(
                        f"Rate limited (429) for AI chunk {chunk_idx}, waiting 2s before retry (attempt {attempt})"
                    )
                    await asyncio.sleep(2.0)
                    continue

                else:
                    logger.warning(
                        f"AI request failed with status {ai_res.status_code} (chunk {chunk_idx}, attempt {attempt})"
                    )
                    await asyncio.sleep(0.5)
                    continue

            except json.JSONDecodeError as e:
                logger.error(
                    f"Failed to parse AI JSON (chunk {chunk_idx}, attempt {attempt}): {e}"
                )
                await asyncio.sleep(0.5)
                continue

            except Exception as e:
                logger.error(
                    f"AI request error (chunk {chunk_idx}, attempt {attempt}): {e}"
                )
                await asyncio.sleep(1.0)
                continue


async def get_vacancies_stack(
    session: AsyncSession, descriptions: dict[str, str]
) -> dict[str, list[str]]:
    """
    Extract technology stacks from descriptions using AI (async with concurrency control).

    Returns:
        Dictionary mapping vacancy_id to list of technologies
    """
    stack = {}

    ai_semaphore = asyncio.Semaphore(config.MAX_CONCURRENT_AI_REQUESTS)
    ai_rate_limiter = RateLimiter(1.0)

    chunks = list(batched(descriptions.items(), config.REQUEST_CHUNK))

    tasks = [
        get_vacancies_stack_chunk(
            session, list(chunk), idx, ai_semaphore, ai_rate_limiter
        )
        for idx, chunk in enumerate(chunks, 1)
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    for result in results:
        if isinstance(result, dict):
            stack.update(result)
        else:
            logger.error(f"AI chunk processing error: {result}")

    return stack
