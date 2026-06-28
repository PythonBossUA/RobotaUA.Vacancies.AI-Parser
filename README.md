# 📊 Tech Market Demand Analyzer

> Automated system for analyzing the IT job market in Ukraine. The project collects data from job portals, analyzes technology requirements, and visualizes results to support career development decisions.

<div align="center">

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![Status](https://img.shields.io/badge/Status-Active-success.svg)

</div>

---

## 🎯 Project Goal

Understand **which technologies** are most in-demand in the job market right now, enabling developers to make informed decisions about skill development.

---

## ⚙️ Architecture

The project consists of **two main modules** with clear separation of concerns:

```
ScraperAnalytics/
│
├── config.py                    # Shared configuration parameters
├── .env                         # API keys (not in git)
├── requirements.txt             # Python dependencies
│
├── scraper.py                   # Legacy entry point (deprecated)
├── analytics.py                 # Legacy entry point (deprecated)
│
├── scraper/                     # 📥 Data collection module
│   ├── __init__.py
│   ├── main.py                  # Main orchestration & entry point
│   ├── api_client.py            # GraphQL API client for robota.ua
│   ├── ai_extractor.py          # AI-powered technology extraction
│   ├── rate_limiter.py          # Token bucket rate limiting
│   ├── text_processor.py        # HTML cleaning & text normalization
│   └── data_writer.py           # CSV writing & data cleaning
│
├── analytics/                   # 📊 Data analysis module
│   ├── __init__.py
│   ├── main.py                  # Main orchestration & entry point
│   ├── data_loader.py           # CSV loading & validation
│   ├── data_cleaner.py          # Data preprocessing & cleaning
│   ├── visualizations.py        # Chart generation (4 visualizations)
│   └── reports.py               # Report generation & data export
│
├── scraped_data.csv             # Raw data (created by scraper/)
└── analytics_results/           # Analysis output (created by analytics/)
    ├── top_technologies.png
    ├── tech_distribution.png
    ├── salary_by_tech.png
    ├── tech_categories.png
    ├── statistics_report.txt
    ├── cleaned_data.csv
    └── technology_frequencies.json
```

### Modular Design Principles

**Scraper Module (`scraper/`):**
- **Single Responsibility:** Each file handles one specific concern
- **Async-First:** All network I/O uses `asyncio` for 3-5x faster performance
- **Rate Limited:** Token bucket pattern prevents server overload
- **Resilient:** Retry logic with exponential backoff

**Analytics Module (`analytics/`):**
- **Separation of Concerns:** Data loading → Cleaning → Visualization → Reporting
- **Pure Functions:** Each function has clear inputs/outputs
- **Reusable Components:** Visualizations can be generated independently

**Communication Contract:**
- Modules communicate ONLY via `scraped_data.csv` file
- No direct imports between `scraper/` and `analytics/`
- CSV schema is the interface contract

---

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

**Required libraries:**
- `curl-cffi` - Cloudflare protection bypass with async support
- `beautifulsoup4` - HTML parsing
- `pandas` - data processing
- `matplotlib` - visualization
- `seaborn` - chart styling
- `python-dotenv` - environment variables management

### 2. API Key Setup

Create a `.env` file in the project root:

```env
OPENROUTER_API_KEY=your_api_key_here
```

Get your API key at [OpenRouter.ai](https://openrouter.ai/)

### 3. Run the Scraper

```bash
# New modular way (recommended)
python -m scraper

# Or legacy way (still works)
python scraper.py
```

**What happens:**
- Connects to robota.ua API via GraphQL
- Collects information about Python vacancies (configurable in `config.py`)
- **Async processing:** Fetches multiple vacancy descriptions concurrently (up to 5 at once)
- Uses AI (via OpenRouter) to extract technologies from descriptions
- Saves results to `scraped_data.csv`

**Execution time:** ~2-5 minutes depending on the number of vacancies (3-5x faster than sync version)

### 4. Run the Analysis

```bash
# New modular way (recommended)
python -m analytics

# Or legacy way (still works)
python analytics.py
```

**What happens:**
- Loads data from `scraped_data.csv`
- Cleans and normalizes data
- Creates 4 visualizations
- Generates a text report with statistics
- Saves processed data to JSON

**Result:** `analytics_results/` folder with charts and reports

---

## 📋 Configuration (`config.py`)

### Main Parameters

| Parameter | Description | Default Value |
|-----------|-------------|---------------|
| `SEARCH_KEYWORD` | Keyword for vacancy search | `"python"` |
| `RESULTS_PER_PAGE` | Results per page | `20` |
| `REQUEST_DELAY` | Delay between page requests (sec) | `2.0` |
| `MAX_RETRIES` | Maximum retry attempts on error | `3` |
| `RETRY_DELAY` | Delay before retry (sec) | `2` |
| `REQUEST_TIMEOUT` | Request timeout (sec) | `30` |
| `CSV_FILENAME` | Output CSV filename | `"scraped_data.csv"` |
| `REQUEST_CHUNK` | Chunk size for AI processing | `10` |
| `MAX_CONCURRENT_DETAILS` | Max concurrent detail requests | `5` |
| `MAX_CONCURRENT_AI_REQUESTS` | Max concurrent AI requests | `3` |

### API Endpoints

```python
BASE_URL = "https://dracula.robota.ua/?q=getPublishedVacanciesList"
BASE_DETAIL_URL = "https://dracula.robota.ua/?q=getPublishedVacancy"
BASE_OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
```

### AI Model

```python
MODEL = "openai/gpt-oss-120b:free"  # Free OpenRouter model
```

**Alternatives:**
- `anthropic/claude-3-haiku` - faster, more accurate
- `meta-llama/llama-3.1-70b-instruct` - good balance
- `google/gemini-flash-1.5` - economical option

---

## 🕷️ Scraper Module (`scraper/`)

### Module Structure

#### `main.py` - Orchestration
Main function that launches the data collection process.

**Algorithm:**
1. Creates async session with browser impersonation (curl_cffi)
2. Makes API request to get vacancy list (paginated)
3. For each page, loads all vacancy descriptions concurrently (max 5 at once)
4. Groups descriptions into chunks of 10
5. Sends chunks to AI for technology extraction (max 3 concurrent)
6. Saves results to CSV
7. Proceeds to next page with 2s delay

#### `api_client.py` - GraphQL Client
Handles all HTTP interactions with robota.ua.

**Key Functions:**
- `get_base_request(session, page)` - Fetch list of vacancies for a page
- `get_vacancy_description(session, vacancy_id, semaphore, rate_limiter)` - Fetch single vacancy detail with concurrency control

**Features:**
- Automatic retry on errors (up to 3 attempts)
- Timeout protection (30 seconds)
- Browser impersonation to bypass Cloudflare
- Logging of all errors

#### `ai_extractor.py` - Technology Extraction
Uses AI to extract technologies from vacancy descriptions.

**Key Functions:**
- `get_vacancies_stack(session, descriptions)` - Main orchestrator
- `get_vacancies_stack_chunk(session, chunk, chunk_idx, semaphore, rate_limiter)` - Process one chunk

**Features:**
- Chunk processing (10 vacancies per request) to optimize API usage
- Special handling for HTTP 429 (Rate Limit) - infinite retries with backoff
- Fallback to empty list `[]` on parse errors
- JSON extraction from AI free text using substring search

#### `rate_limiter.py` - Rate Limiting
Token bucket pattern implementation for async requests.

**RateLimiter Class:**
```python
rate_limiter = RateLimiter(0.2)  # Min 0.2s between requests
await rate_limiter.acquire()  # Wait if needed
```

#### `text_processor.py` - Text Cleaning
Cleans HTML from tags and formats text.

**Operations:**
- HTML tag removal (BeautifulSoup)
- Special character replacement
- URL removal
- Whitespace normalization

#### `data_writer.py` - CSV Operations
Writes data to CSV and normalizes data structures.

**Functions:**
- `write_csv(data, path)` - Append data with headers
- `clean_data(raw_data)` - Normalize nested structures (salary, company, city)

### Rate Limiting & Ethics

**Server respect:**
- ✅ 2-second delay between pages
- ✅ 0.2-second minimum delay between vacancy details (max 5 req/sec)
- ✅ 1.0-second minimum delay between AI requests
- ✅ Maximum 3 retry attempts (except 429 rate limits)
- ✅ Browser impersonation to reduce load
- ✅ GraphQL instead of HTML scraping

**429 (Rate Limit) handling:**
```python
elif ai_res.status_code == 429:
    logger.warning(f"Rate limited (429), waiting 2s before retry")
    await asyncio.sleep(2.0)
    continue  # Infinite retry for rate limits
```

### Output Data (CSV)

`scraped_data.csv` structure:

| Column | Type | Description |
|--------|------|-------------|
| `id` | int | Vacancy ID |
| `title` | str | Job title |
| `description` | str | Short description |
| `salary` | int/null | Salary (if specified) |
| `company` | str | Company name |
| `city` | str | City |
| `stack` | list[str] | Technology list (JSON-encoded) |

**Example entry:**
```csv
id,title,description,salary,company,city,stack
11094614,Python Developer,Backend development...,50000,TechCorp,Kyiv,"['PYTHON', 'DJANGO', 'POSTGRESQL', 'DOCKER']"
```

---

## 📊 Analytics Module (`analytics/`)

### Module Structure

#### `main.py` - Orchestration
Runs the full analysis pipeline:
1. Data loading (`data_loader.py`)
2. Cleaning and validation (`data_cleaner.py`)
3. Technology extraction
4. Visualization creation (`visualizations.py`)
5. Report generation (`reports.py`)

#### `data_loader.py` - Data Loading
**`load_data(csv_path)`** - CSV loading with validation
- Checks file existence
- Validates required columns (id, title, stack)
- Returns pandas DataFrame or None

#### `data_cleaner.py` - Data Preprocessing
**Functions:**
- `clean_stack_data(df)` - Parse stack column from string "[...]" to actual list
- `extract_all_technologies(df)` - Count frequency of all technologies across vacancies
- `create_technology_categories(tech_counter)` - Categorize technologies by type (Languages, Frameworks, Databases, etc.)

#### `visualizations.py` - Chart Generation
Creates 4 professional visualizations at 300 DPI.

**Functions:**
- `visualize_top_technologies(tech_counter, top_n)` - Bar chart
- `visualize_technology_distribution(df)` - Histogram
- `analyze_salary_by_stack(df, tech_counter, top_n)` - Salary analysis
- `visualize_technology_categories(categorized)` - Pie chart

#### `reports.py` - Report Generation
**Functions:**
- `generate_statistics_report(df, tech_counter)` - Text report with detailed statistics
- `save_processed_data(df, tech_counter)` - Export to JSON and cleaned CSV

### Visualizations

#### 1. Top Technologies (`top_technologies.png`)
Horizontal bar chart of top-20 technologies by vacancy count.

**What it shows:**
- Absolute mention count
- Comparative popularity
- Market trends

#### 2. Tech Distribution (`tech_distribution.png`)
Distribution of number of technologies per vacancy.

**What it shows:**
- Typical stack size for developers
- Requirement variance (from minimalists to full-stack)

#### 3. Salary by Tech (`salary_by_tech.png`)
Average salaries by technology (top-15).

**What it shows:**
- Which technologies pay more
- ROI of learning new skills
- Premium technologies vs commodity

#### 4. Tech Categories (`tech_categories.png`)
Pie chart of distribution by category.

**Categories:**
- **Languages** - programming languages
- **Web Frameworks** - web frameworks
- **Databases** - databases
- **Cloud & DevOps** - cloud services and tools
- **Data & ML** - data science tools
- **Tools & Other** - other technologies

### Reports

#### `statistics_report.txt`
Text report with detailed statistics:

```
================================================================================
TECH MARKET DEMAND ANALYSIS REPORT
================================================================================

Total Vacancies Analyzed: 245
Unique Technologies Found: 87
Average Technologies per Vacancy: 8.34
Median Technologies per Vacancy: 8

================================================================================
TOP 30 MOST DEMANDED TECHNOLOGIES
================================================================================

 1. PYTHON                       - 245 vacancies (100.0%)
 2. DJANGO                        - 156 vacancies ( 63.7%)
 3. POSTGRESQL                    - 142 vacancies ( 58.0%)
...
```

#### `technology_frequencies.json`
JSON file for programmatic data access:

```json
{
  "PYTHON": 245,
  "DJANGO": 156,
  "POSTGRESQL": 142,
  ...
}
```

#### `cleaned_data.csv`
Cleaned dataset for further analysis with additional columns:
- `stack_cleaned` - technology list (list)
- `stack_count` - number of technologies (int)

---

## 🛠️ Advanced Features

### Changing Target Language/Technology

In `config.py`:
```python
SEARCH_KEYWORD = "java"  # or "javascript", "golang", etc.
```

### Adjusting Data Volume

```python
RESULTS_PER_PAGE = 50  # More results per request
REQUEST_DELAY = 3.0     # Longer delay = safer
```

### Using More Accurate AI Model

```python
MODEL = "anthropic/claude-3-haiku"  # Paid, but more accurate
```

**Model Comparison:**

| Model | Accuracy | Speed | Price |
|-------|----------|-------|-------|
| `openai/gpt-oss-120b:free` | ⭐⭐⭐ | ⚡⚡⚡ | 🆓 |
| `meta-llama/llama-3.1-70b-instruct` | ⭐⭐⭐⭐ | ⚡⚡ | 💰 |
| `anthropic/claude-3-haiku` | ⭐⭐⭐⭐⭐ | ⚡⚡⚡ | 💰💰 |

---

## 📈 Using the Results

### For Developers

**Questions the analysis answers:**

1. **What to learn?** - Top technologies show the most in-demand skills
2. **Where to grow?** - Salary by Tech shows what pays more
3. **What stack to build?** - Distribution shows typical combinations
4. **Which niche?** - Categories show directions (Web, Data, Cloud)

### For Recruiters

- Current market requirements
- Typical salary expectations
- Popular technology combinations

### For Business

- IT hiring trends
- Scarce skills
- Labor market pricing

---

## 🔍 Output Data Examples

### Top-10 Technologies (example)

```
1. PYTHON           245 vacancies (100.0%)
2. DJANGO           156 vacancies ( 63.7%)
3. POSTGRESQL       142 vacancies ( 58.0%)
4. DOCKER           128 vacancies ( 52.2%)
5. FASTAPI          98  vacancies ( 40.0%)
6. REDIS            87  vacancies ( 35.5%)
7. KUBERNETES       76  vacancies ( 31.0%)
8. AWS              71  vacancies ( 29.0%)
9. MONGODB          65  vacancies ( 26.5%)
10. CELERY          62  vacancies ( 25.3%)
```

### Salary Statistics (example)

```
Vacancies with Salary Data: 187 (76.3%)
Average Salary: 48,500 UAH
Median Salary: 45,000 UAH
Min Salary: 25,000 UAH
Max Salary: 120,000 UAH
```

---

## ⚠️ Known Limitations

### Technical

1. **AI Parsing** - May have errors in technology extraction (especially abbreviations)
2. **Rate Limits** - OpenRouter may limit free requests
3. **API Changes** - robota.ua may change GraphQL API

### Data

1. **Salaries** - Not all vacancies specify salary (~75% of data)
2. **Regional** - Data only for Ukraine
3. **Timeliness** - Reflects state at the time of execution

### Ethical

1. **Public Data** - Only public information is scraped
2. **No Auth** - No authorization required
3. **Rate Limiting** - Respectful attitude to server

---

## 🐛 Troubleshooting

### Error: `OPENROUTER_API_KEY not found`

**Solution:**
```bash
# Create .env file
echo "OPENROUTER_API_KEY=your_key" > .env
```

### Error: `Rate limited (429)`

**Solution:**
- Wait a few minutes
- Reduce `REQUEST_CHUNK` in config.py
- Use a paid model with higher limit

### Error: `scraped_data.csv not found`

**Solution:**
- First run `python -m scraper.main` or `python scraper.py`
- Verify that scraping completed successfully

### Empty charts / No data

**Solution:**
- Check that CSV has `stack` column
- Ensure AI correctly extracted technologies
- Check scraper logs for errors

### ModuleNotFoundError: No module named 'scraper'

**Solution:**
- Make sure you're running from the project root directory
- The `scraper/` and `analytics/` directories must contain `__init__.py` files

---

## 🔮 Roadmap

### Completed
- ✅ Asynchronous scraping (`asyncio` + `curl_cffi`)
- ✅ Modular architecture with clear separation of concerns
- ✅ Token bucket rate limiting
- ✅ Comprehensive error handling and retry logic

### Planned Improvements
- [ ] Support for multiple job portals (dou.ua, work.ua)
- [ ] NLP for automatic discovery of new technologies
- [ ] Correlation analysis (experience vs salary vs technologies)
- [ ] Temporal trends (comparison with previous runs)
- [ ] Web dashboard for interactive visualization
- [ ] Telegram bot for notifications
- [ ] Docker containerization

---

## 📄 License

MIT License - free use for any purpose.

---

## 🤝 Contributing

Pull requests are welcome!

**Priority areas:**
- Adding new data sources
- Improving AI prompts for accuracy
- New visualization types
- Performance optimization

---

## 📧 Contact

Questions and suggestions are welcome in Issues.

---

<div align="center">

**Last Updated:** June 28, 2026

**Version:** 2.0.0 (Modular Architecture)

**Python:** 3.11+

</div>
