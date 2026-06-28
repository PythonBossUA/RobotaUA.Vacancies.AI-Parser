"""Data cleaning and preprocessing utilities."""

import json
import logging
import pandas as pd
from collections import Counter

logger = logging.getLogger(__name__)


def clean_stack_data(df: pd.DataFrame) -> pd.DataFrame:
    """Clean and parse stack column from string to list."""
    logger.info("Cleaning stack data...")

    def parse_stack(stack_str):
        """Parse stack string to list of technologies."""
        if pd.isna(stack_str) or stack_str == "[]" or stack_str == "":
            return []

        try:
            if isinstance(stack_str, str):
                stack_list = json.loads(stack_str.replace("'", '"'))
            else:
                stack_list = stack_str

            return [tech.strip().upper() for tech in stack_list if tech.strip()]
        except:
            return [
                tech.strip().upper()
                for tech in str(stack_str).split(",")
                if tech.strip()
            ]

    df["stack_cleaned"] = df["stack"].apply(parse_stack)
    df["stack_count"] = df["stack_cleaned"].apply(len)

    initial_count = len(df)
    df = df[df["stack_count"] > 0].copy()
    removed = initial_count - len(df)

    if removed > 0:
        logger.warning(f"Removed {removed} vacancies with no stack data")

    logger.info(f"Cleaned {len(df)} vacancies with valid stack data")
    return df


def extract_all_technologies(df: pd.DataFrame) -> Counter:
    """Extract and count all technologies across all vacancies."""
    logger.info("Extracting technology frequencies...")

    all_techs = []
    for stack_list in df["stack_cleaned"]:
        all_techs.extend(stack_list)

    tech_counter = Counter(all_techs)
    logger.info(f"Found {len(tech_counter)} unique technologies")

    return tech_counter


def create_technology_categories(tech_counter: Counter) -> dict:
    """Categorize technologies by type."""
    logger.info("Categorizing technologies...")

    categories = {
        "Languages": [
            "PYTHON",
            "JAVASCRIPT",
            "JAVA",
            "C++",
            "C#",
            "GO",
            "RUBY",
            "PHP",
            "TYPESCRIPT",
            "KOTLIN",
            "SWIFT",
            "RUST",
        ],
        "Web Frameworks": [
            "DJANGO",
            "FLASK",
            "FASTAPI",
            "REACT",
            "VUE",
            "ANGULAR",
            "EXPRESS",
            "SPRING",
            "LARAVEL",
            "RAILS",
            "NEXTJS",
            "NUXT",
        ],
        "Databases": [
            "POSTGRESQL",
            "MYSQL",
            "MONGODB",
            "REDIS",
            "ELASTICSEARCH",
            "CASSANDRA",
            "ORACLE",
            "MSSQL",
            "SQLITE",
            "DYNAMODB",
        ],
        "Cloud & DevOps": [
            "AWS",
            "DOCKER",
            "KUBERNETES",
            "AZURE",
            "GCP",
            "TERRAFORM",
            "JENKINS",
            "GITLAB",
            "GITHUB",
            "CI/CD",
            "ANSIBLE",
        ],
        "Data & ML": [
            "PANDAS",
            "NUMPY",
            "TENSORFLOW",
            "PYTORCH",
            "SCIKIT-LEARN",
            "KERAS",
            "SPARK",
            "HADOOP",
            "AIRFLOW",
            "KAFKA",
        ],
        "Tools & Other": [],
    }

    categorized = {cat: Counter() for cat in categories}
    uncategorized = set()

    for tech, count in tech_counter.items():
        found = False
        for category, keywords in categories.items():
            if category == "Tools & Other":
                continue
            if any(keyword in tech or tech in keyword for keyword in keywords):
                categorized[category][tech] = count
                found = True
                break

        if not found:
            categorized["Tools & Other"][tech] = count
            uncategorized.add(tech)

    return categorized
