# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Tech Market Demand Analyzer - scrapes job boards (currently robota.ua via GraphQL), uses AI to extract technology stacks from job descriptions, and generates statistical visualizations to identify in-demand tech skills.

## Commands

### Run the complete pipeline
```bash
# 1. Scrape job data (5-15 minutes, creates scraped_data.csv)
python scraper.py

# 2. Analyze and visualize (creates analytics_results/ folder)
python analytics.py
```

### Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Configure API key (required for scraping)
cp .env.sample .env
# Edit .env and add your OpenRouter API key
```

### Development/Testing
```bash
# Test with small dataset - edit config.py:
# RESULTS_PER_PAGE = 5
# LOG_LEVEL = "DEBUG"

# Scrape different technology
# Edit config.py: SEARCH_KEYWORD = "java"
```

## Architecture

### Two-Stage Pipeline (Strict SRP)

**Stage 1: Scraping (scraper.py) - ASYNC**
- GraphQL API → Raw vacancy data → AI extraction → CSV output
- Uses `asyncio` + `aiohttp` for concurrent requests with rate limiting
- Modules communicate ONLY via `scraped_data.csv` file
- No direct imports between scraper.py and analytics.py

**Stage 2: Analytics (analytics.py)**
- CSV input → Cleaning → Frequency analysis → 4 visualizations + reports

### Data Flow
```
robota.ua GraphQL API
    ↓ (scraper.py: pagination loop)
List of vacancy IDs
    ↓ (scraper.py: detail requests with 0.5s delay)
Full job descriptions (HTML)
    ↓ (scraper.py: BeautifulSoup cleaning)
Plain text descriptions
    ↓ (scraper.py: chunked AI processing via OpenRouter)
Technology lists per vacancy
    ↓ (scraper.py: CSV writer)
scraped_data.csv [id, title, description, salary, company, city, stack]
    ↓ (analytics.py: pandas pipeline)
analytics_results/ [4 PNGs + TXT report + JSON + cleaned CSV]
```

### Key Technical Decisions

**Async Architecture:** Uses `asyncio` + `curl_cffi.requests.AsyncSession` for 3-5x faster scraping through concurrent requests with browser impersonation. Semaphores limit concurrent connections (5 detail requests, 3 AI requests) to respect server load.

**AI Tech Extraction:** OpenRouter API processes 10 job descriptions per request (chunked). Prompt in `config.ZERO_PROMPT` instructs model to return JSON dictionary `{"vacancy_id": ["TECH1", "TECH2"]}`. Parsing uses substring extraction (`find("{")`/`rfind("}")`) because AI may add text outside JSON.

**Rate Limiting Strategy (Token Bucket Pattern):**
- 2.0s between page requests (pagination) - sequential
- 0.2s minimum between detail requests (5 req/sec max) - concurrent with semaphore
- 1.0s minimum between AI requests - concurrent with semaphore
- `asyncio.Semaphore` limits: 5 concurrent detail requests, 3 concurrent AI requests
- HTTP 429 triggers retry with 2s backoff (doesn't count against MAX_RETRIES)
- All other errors: max 3 retries then fail gracefully

**CSV as Contract:** Column order matters for analytics compatibility: `id, title, description, salary, company, city, stack`. Stack column contains JSON-encoded list as string (parsed in analytics with `json.loads()`).

## Configuration (config.py)

All scraping behavior controlled via `config.py`:
- `SEARCH_KEYWORD` - Target technology to search
- `RESULTS_PER_PAGE` - Vacancies per API page (default 20)
- `REQUEST_DELAY` / `REQUEST_CHUNK` - Rate limiting knobs
- `MODEL` - OpenRouter model ID (free: `openai/gpt-oss-120b:free`)
- `ZERO_PROMPT` - AI instruction template for tech extraction

Environment variables in `.env`:
- `OPENROUTER_API_KEY` - Required, never commit

## Module Interfaces

### scraper.py exports nothing (runs as script)
Entry point: `scraping()` → `scraping_async()` (async wrapper)
Side effects: Creates/overwrites `scraped_data.csv`

Key async functions:
- `scraping_async()` - Main async orchestration loop
- `get_base_request()` - Fetches page of vacancies from GraphQL (sequential)
- `get_vacancy_description()` - Fetches single vacancy detail (concurrent via semaphore)
- `get_vacancies_stack()` - AI extraction with chunking and retry logic (concurrent)
- `get_vacancies_stack_chunk()` - Process one AI chunk with rate limiting
- `clean_vacancy_text()` - BeautifulSoup HTML→text cleanup (sync)

Key classes:
- `RateLimiter` - Token bucket implementation for minimum delay between requests

### analytics.py exports nothing (runs as script)
Entry point: `run_full_analysis()` function at bottom
Side effects: Creates `analytics_results/` directory with 7 files

Key functions:
- `load_data()` - CSV validation and pandas loading
- `clean_stack_data()` - Parse string "[...]" to actual lists
- `extract_all_technologies()` - Counter across all vacancies
- `create_technology_categories()` - Hardcoded grouping (Languages/Frameworks/Databases/Cloud/Data/Tools)
- Four `visualize_*()` functions - matplotlib/seaborn charts at 300 DPI

### config.py exports constants only
No functions, just module-level variables
Uses `os.environ['OPENROUTER_API_KEY']` from dotenv

## Known Constraints

**AI Parsing Fragility:** OpenRouter free model sometimes returns malformed JSON or adds commentary. Scraper handles this with substring extraction and falls back to empty list `[]` on parse failure. Vacancy isn't skipped, just gets no tech stack.

**Salary Data Sparsity:** Only ~75% of vacancies include salary. Analytics filters out `NaN` before salary-based calculations.

**Single Data Source:** Only robota.ua implemented. Adding dou.ua/work.ua requires new GraphQL schema and possibly different Cloudflare bypass technique.

**Async Concurrency Limits:** Hardcoded to 5 detail / 3 AI concurrent requests. May need tuning based on server response times and rate limit policies.

## Critical Implementation Notes

**Async architecture:** All network I/O uses `curl_cffi.requests.AsyncSession` with `asyncio` and Chrome browser impersonation. Concurrency controlled via `asyncio.Semaphore`. Rate limiting via custom `RateLimiter` class (token bucket pattern).

**AI prompt modification:** If changing `ZERO_PROMPT`, ensure response format stays as JSON dict with string keys. Analytics expects `stack` column to be parseable as list.

**Category expansion:** When adding tech categories in `create_technology_categories()`, maintain the "Tools & Other" catch-all as last category for uncategorized items.

**Matplotlib threading:** Analytics creates/closes figures explicitly (`plt.close()`) to avoid memory leaks when generating multiple charts.

**GraphQL payload structure:** `LIST_PAYLOAD` and `DETAIL_PAYLOAD` in scraper.py are fragile - robota.ua may change schema. If scraping breaks, check GraphQL operation names and field structure first.
