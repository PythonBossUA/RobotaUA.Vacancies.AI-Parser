"""
DEPRECATED: This file is kept for backwards compatibility.
Use the modular version in the scraper/ directory instead.

To run the scraper, use:
    python -m scraper.main
or:
    from scraper import scraping
    scraping()
"""

from scraper import scraping

if __name__ == "__main__":
    scraping()
