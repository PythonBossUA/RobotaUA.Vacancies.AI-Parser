import os
from dotenv import load_dotenv

load_dotenv()

"""
Configuration file for the scraper.
Modify these parameters to customize scraping behavior.
"""

# Search parameters
SEARCH_KEYWORD = "python"
RESULTS_PER_PAGE = 20

# Server-friendly settings
REQUEST_DELAY = 2.0  # Delay between page requests in seconds (be respectful!)
MAX_RETRIES = 3  # Maximum retry attempts for failed requests
RETRY_DELAY = 2  # Delay before retry in seconds
REQUEST_TIMEOUT = 30  # Request timeout in seconds

# Output settings
CSV_FILENAME = "scraped_data.csv"

# API endpoints
BASE_URL = "https://dracula.robota.ua/?q=getPublishedVacanciesList"
BASE_DETAIL_URL = "https://dracula.robota.ua/?q=getPublishedVacancy"
REFERER = "https://robota.ua/"

# Logging
LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL

# AI integration
REQUEST_CHUNK = 10
BASE_OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_HEADERS = {
    "Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}",
    "Content-Type": "application/json",
}
ZERO_PROMPT = """
You are an expert in analyzing IT job postings. Your task is to extract all technologies, tools, programming languages, frameworks, databases, and other technical skills from MULTIPLE job descriptions provided below.

INSTRUCTIONS:
1. Process EACH job description separately
2. For every vacancy, find ALL technologies required or mentioned for the position
3. INCLUDE for each vacancy:
   - Programming languages (Python, JavaScript, Go, etc.)
   - Frameworks (Django, React, FastAPI, etc.)
   - Databases (PostgreSQL, MongoDB, Redis, etc.)
   - Tools and platforms (Docker, Kubernetes, AWS, Git, etc.)
   - Libraries (NumPy, Pandas, etc.)
   - Methodologies (Agile, Scrum, etc.)
   - Other technical skills and requirements

4. DO NOT INCLUDE:
   - Soft skills (communication, teamwork, leadership)
   - Company names
   - Job titles
   - Non-technical requirements
   
5. IGNORE:
   - Company manifests, mission statements, and marketing fluff
   - Test assignments and interview process descriptions
   - Links to social media, messengers, and company websites
   - Legal disclaimers and data processing consents
   Focus ONLY on the technical stack and requirements.

RESPONSE FORMAT:
Return the result ONLY in JSON format as a SINGLE OBJECT (dictionary) where each KEY is the vacancy_id (string) and each VALUE is an array of technologies found for that vacancy. Do NOT wrap the result in an array. Do NOT add any additional explanations, comments, or text before/after the JSON.

{
  "11094614": ["Python", "BigQuery", "SQL", "Power BI"],
  "11213282": ["Python", "Django", "PostgreSQL", "Docker"]
}

IMPORTANT:
- Use vacancy_id as a STRING key (e.g., "11094614", not 11094614)
- Each technology list must contain unique items (no duplicates WITHIN a single vacancy)
- Use the original technology names as they appear in the job descriptions
- If a vacancy has no technologies found, return an empty list for that key: "12345678": []
- Preserve the vacancy_id exactly as provided in the input
- Process ALL provided vacancies, do not skip any
- DO NOT add any text outside the JSON structure

JOB DESCRIPTIONS:
"""
MODEL = "openai/gpt-oss-120b:free"

# Async settings
MAX_CONCURRENT_DETAILS = 5
MAX_CONCURRENT_AI_REQUESTS = 3
