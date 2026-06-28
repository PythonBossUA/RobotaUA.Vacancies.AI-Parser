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

The project consists of **three independent modules**:

```
ScraperAnalytics/
│
├── config.py          # Scraping and API configuration parameters
├── scraper.py         # Data collection module from job portals
├── analytics.py       # Data analysis and visualization module
├── scraped_data.csv   # Raw data (created after running scraper.py)
└── analytics_results/ # Analysis results (created after running analytics.py)
    ├── top_technologies.png
    ├── tech_distribution.png
    ├── salary_by_tech.png
    ├── tech_categories.png
    ├── statistics_report.txt
    ├── cleaned_data.csv
    └── technology_frequencies.json
```

---

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

**Required libraries:**
- `curl_cffi` - Cloudflare protection bypass
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
python scraper.py
```

**What happens:**
- Connects to robota.ua API via GraphQL
- Collects information about Python vacancies
- For each vacancy, loads the full description
- Uses AI (via OpenRouter) to extract technologies from descriptions
- Saves results to `scraped_data.csv`

**Execution time:** ~5-15 minutes depending on the number of vacancies

### 4. Run the Analysis

```bash
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

## 🕷️ Scraper Module (`scraper.py`)

### Main Functions

#### `scraping()`
Main function that launches the data collection process.

**Algorithm:**
1. Creates a session with browser impersonation (curl_cffi)
2. Makes API request to get vacancy list
3. For each vacancy, loads full description
4. Groups descriptions into chunks of 10
5. Sends chunks to AI for technology extraction
6. Saves results to CSV
7. Proceeds to next page with delay

#### `get_vacancy_description(session: Session) -> Optional[str]`
Gets full vacancy description by ID.

**Features:**
- Automatic retry on errors (up to 3 attempts)
- Timeout protection (30 seconds)
- Logging of all errors

#### `get_vacancies_stack(session: Session, descriptions: dict) -> dict`
Uses AI to extract technologies from vacancy descriptions.

**Features:**
- Chunk processing to optimize API requests
- Special handling for HTTP 429 (Rate Limit) - infinite retries
- Fallback to empty list on errors
- JSON parsing from AI free text

#### `clean_vacancy_text(html_text: str) -> str`
Cleans HTML from tags and formats text.

**Operations:**
- HTML tag removal (BeautifulSoup)
- Special character replacement
- URL removal
- Whitespace normalization

### Rate Limiting & Ethics

**Server respect:**
- ✅ 2-second delay between pages
- ✅ 0.5-second delay between vacancy details
- ✅ Maximum 3 retry attempts
- ✅ Browser impersonation to reduce load
- ✅ GraphQL instead of HTML scraping

**429 (Rate Limit) handling:**
```python
elif ai_res.status_code == 429:
    logger.warning(f"Rate limited (429), waiting before retry")
    time.sleep(min(0.5, config.RETRY_DELAY))
    attempt -= 1  # Don't count this attempt
    continue  # Infinite retry
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
| `stack` | list[str] | Technology list (JSON) |

**Example entry:**
```csv
id,title,description,salary,company,city,stack
11094614,Python Developer,Backend development...,50000,TechCorp,Kyiv,"['PYTHON', 'DJANGO', 'POSTGRESQL', 'DOCKER']"
```

---

## 📊 Analytics Module (`analytics.py`)

### Main Functions

#### `run_full_analysis()`
Runs the full analysis pipeline:
1. Data loading
2. Cleaning and validation
3. Technology extraction
4. Visualization creation
5. Report generation

#### Data Analysis

**`load_data()`** - CSV loading with validation  
**`clean_stack_data()`** - parse stack column from string to list  
**`extract_all_technologies()`** - count frequency of all technologies  
**`create_technology_categories()`** - categorize by type

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
- Typical stack size for Python developers
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
- First run `scraper.py`
- Verify that scraping completed successfully

### Empty charts / No data

**Solution:**
- Check that CSV has `stack` column
- Ensure AI correctly extracted technologies
- Check `scraper.py` logs for errors

---

## 🔮 Roadmap

### Planned Improvements

- [ ] Asynchronous scraping (`asyncio` + `aiohttp`)
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

**Version:** 1.0.0

**Python:** 3.11+

</div>
