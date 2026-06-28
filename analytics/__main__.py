"""Main analytics orchestration module."""

import logging
import config
from .data_loader import load_data
from .data_cleaner import (
    clean_stack_data,
    extract_all_technologies,
    create_technology_categories,
)
from .visualizations import (
    visualize_top_technologies,
    visualize_technology_distribution,
    analyze_salary_by_stack,
    visualize_technology_categories,
)
from .reports import generate_statistics_report, save_processed_data

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def run_full_analysis() -> None:
    """Run complete analysis pipeline."""
    logger.info("Starting full analysis pipeline...")

    df = load_data()
    if df is None:
        return

    df = clean_stack_data(df)
    if len(df) == 0:
        logger.error("No valid data after cleaning")
        return

    tech_counter = extract_all_technologies(df)

    visualize_top_technologies(tech_counter, top_n=20)
    visualize_technology_distribution(df)
    analyze_salary_by_stack(df, tech_counter, top_n=15)

    categorized = create_technology_categories(tech_counter)
    visualize_technology_categories(categorized)

    generate_statistics_report(df, tech_counter)
    save_processed_data(df, tech_counter)

    logger.info("Analysis complete! Results saved to analytics_results/")
    print("\n✅ Analysis complete! Check the 'analytics_results' folder for results.")


if __name__ == "__main__":
    run_full_analysis()
