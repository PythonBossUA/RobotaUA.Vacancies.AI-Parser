# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Tech Market Demand Analyzer - scrapes job boards (currently robota.ua via GraphQL), uses AI to extract technology stacks from job descriptions, and generates statistical visualizations to identify in-demand tech skills.

## Commands

### Run the complete pipeline
```bash
# 1. Scrape job data (5-15 minutes, creates scraped_data.csv)
python scraper.py
# OR using the modular version:
python -m scraper

# 2. Analyze and visualize (creates analytics_results/ folder)
python analytics.py
# OR using the modular version:
python -m analytics
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

### Modular Structure

The project is organized into two main modules with clear separation of concerns:

```
ScraperAnalytics/
├── config.py                    # Shared configuration
├── scraper.py                   # Legacy entry point (deprecated)
├── analytics.py                 # Legacy entry point (deprecated)
│
├── scraper/                     # Scraping module
│   ├── __init__.py
│   ├── main.py                  # Orchestration & entry point
│   ├── api_client.py            # GraphQL API interactions
│   ├── ai_extractor.py          # AI-powered tech extraction
│   ├── rate_limiter.py          # Token bucket rate limiting
│   ├── text_processor.py        # HTML cleaning & normalization
│   └── data_writer.py           # CSV writing & data cleaning
│
└── analytics/                   # Analytics module
    ├── __init__.py
    ├── main.py                  # Orchestration & entry point
    ├── data_loader.py           # CSV loading & validation
    ├── data_cleaner.py          # Data cleaning & preprocessing
    ├── visualizations.py        # Chart generation (matplotlib/seaborn)
    └── reports.py               # Report generation & data export
```

### Two-Stage Pipeline (Strict SRP)

**Stage 1: Scraping (scraper/) - ASYNC**
- GraphQL API → Raw vacancy data → AI extraction → CSV output
- Uses `asyncio` + `curl_cffi` for concurrent requests with rate limiting
- Modules communicate ONLY via `scraped_data.csv` file
- No direct imports between scraper/ and analytics/

**Stage 2: Analytics (analytics/)**
- CSV input → Cleaning → Frequency analysis → 4 visualizations + reports

### Data Flow
```
robota.ua GraphQL API
    ↓ (api_client.py: pagination loop)
List of vacancy IDs
    ↓ (api_client.py: detail requests with 0.2s rate limit)
Full job descriptions (HTML)
    ↓ (text_processor.py: BeautifulSoup cleaning)
Plain text descriptions
    ↓ (ai_extractor.py: chunked AI processing via OpenRouter)
Technology lists per vacancy
    ↓ (data_writer.py: CSV writer)
scraped_data.csv [id, title, description, salary, company, city, stack]
    ↓ (data_loader.py + data_cleaner.py: pandas pipeline)
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

### scraper/ package

**Entry point:** `scraper.main.scraping()` → `scraping_async()` (async wrapper)
**Side effects:** Creates/overwrites `scraped_data.csv`

**Submodules:**

- `api_client.py` - GraphQL API interactions
  - `get_base_request(session, page)` - Fetch page of vacancies (sequential)
  - `get_vacancy_description(session, vacancy_id, semaphore, rate_limiter)` - Fetch single vacancy detail (concurrent)
  
- `ai_extractor.py` - AI-powered technology extraction
  - `get_vacancies_stack(session, descriptions)` - Main AI extraction orchestrator
  - `get_vacancies_stack_chunk(session, chunk, chunk_idx, semaphore, rate_limiter)` - Process one AI chunk with retry logic
  
- `rate_limiter.py` - Rate limiting
  - `RateLimiter` class - Token bucket implementation for minimum delay between requests
  
- `text_processor.py` - HTML/text cleaning
  - `clean_vacancy_text(html_text)` - BeautifulSoup HTML→text cleanup (sync)
  
- `data_writer.py` - CSV writing
  - `write_csv(data, path)` - Append data to CSV with headers
  - `clean_data(raw_data)` - Normalize data structures in-place

### analytics/ package

**Entry point:** `analytics.main.run_full_analysis()` function
**Side effects:** Creates `analytics_results/` directory with 7 files

**Submodules:**

- `data_loader.py` - CSV loading
  - `load_data(csv_path)` - CSV validation and pandas loading
  
- `data_cleaner.py` - Data preprocessing
  - `clean_stack_data(df)` - Parse string "[...]" to actual lists
  - `extract_all_technologies(df)` - Counter across all vacancies
  - `create_technology_categories(tech_counter)` - Hardcoded grouping (Languages/Frameworks/Databases/Cloud/Data/Tools)
  
- `visualizations.py` - Chart generation
  - `visualize_top_technologies(tech_counter, top_n)` - Bar chart of top technologies
  - `visualize_technology_distribution(df)` - Distribution histogram
  - `analyze_salary_by_stack(df, tech_counter, top_n)` - Salary analysis chart
  - `visualize_technology_categories(categorized)` - Pie chart by category
  
- `reports.py` - Report generation
  - `generate_statistics_report(df, tech_counter)` - Text report with statistics
  - `save_processed_data(df, tech_counter)` - Export to JSON/CSV

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

**GraphQL payload structure:** `LIST_PAYLOAD` and `DETAIL_PAYLOAD_TEMPLATE` in `api_client.py` are fragile - robota.ua may change schema. If scraping breaks, check GraphQL operation names and field structure first.

**Modular design:** Each submodule has a single responsibility. When modifying functionality:
- API changes → `api_client.py`
- Rate limiting tuning → `rate_limiter.py`
- AI prompt/parsing → `ai_extractor.py`
- HTML cleaning → `text_processor.py`
- Visualization style → `visualizations.py`
- Report format → `reports.py`

**Backwards compatibility:** Root-level `scraper.py` and `analytics.py` are deprecated wrappers that import from the modular versions. New code should use `python -m scraper.main` or `from scraper import scraping`.
