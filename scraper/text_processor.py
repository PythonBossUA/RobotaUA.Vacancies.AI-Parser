"""Text cleaning and HTML processing utilities."""

import re
from bs4 import BeautifulSoup


def clean_vacancy_text(html_text: str) -> str:
    """Clean HTML and normalize text."""
    soup = BeautifulSoup(html_text, "html.parser")
    text = soup.get_text(separator=" ")

    text = text.replace(" ", " ").replace("\t", " ")
    text = re.sub(r"(\w)\?(\w)", r"\1'\2", text)
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text
