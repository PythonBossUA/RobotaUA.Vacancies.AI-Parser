"""
Scraper module for collecting job vacancy data from robota.ua.

This module provides async scraping functionality with rate limiting,
AI-powered technology extraction, and CSV output.

Usage:
    python -m scraper
    # OR
    from scraper import scraping
    scraping()
"""

__all__ = ["scraping"]


def __getattr__(name):
    """Lazy import to avoid RuntimeWarning when using python -m scraper."""
    if name == "scraping":
        from .__main__ import scraping

        return scraping
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
