"""Data loading utilities."""

import logging
from typing import Optional
import pandas as pd
import config

logger = logging.getLogger(__name__)


def load_data(csv_path: str = config.CSV_FILENAME) -> Optional[pd.DataFrame]:
    """Load and validate scraped data from CSV."""
    try:
        df = pd.read_csv(csv_path)
        logger.info(f"Loaded {len(df)} vacancies from {csv_path}")

        if df.empty:
            logger.error("CSV file is empty")
            return None

        required_columns = ["id", "title", "stack"]
        missing = [col for col in required_columns if col not in df.columns]
        if missing:
            logger.error(f"Missing required columns: {missing}")
            return None

        return df
    except FileNotFoundError:
        logger.error(f"File {csv_path} not found. Run scraper first.")
        return None
    except Exception as e:
        logger.error(f"Error loading data: {e}")
        return None
