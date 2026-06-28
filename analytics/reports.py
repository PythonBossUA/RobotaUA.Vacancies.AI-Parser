"""Report generation utilities."""

import json
import logging
from pathlib import Path
from collections import Counter
import pandas as pd

logger = logging.getLogger(__name__)

OUTPUT_DIR = Path("analytics_results")


def generate_statistics_report(df: pd.DataFrame, tech_counter: Counter) -> None:
    """Generate and save text report with statistics."""
    logger.info("Generating statistics report...")

    report_lines = [
        "=" * 80,
        "TECH MARKET DEMAND ANALYSIS REPORT",
        "=" * 80,
        "",
        f"Total Vacancies Analyzed: {len(df)}",
        f"Unique Technologies Found: {len(tech_counter)}",
        f"Average Technologies per Vacancy: {df['stack_count'].mean():.2f}",
        f"Median Technologies per Vacancy: {df['stack_count'].median():.0f}",
        "",
        "=" * 80,
        "TOP 30 MOST DEMANDED TECHNOLOGIES",
        "=" * 80,
        "",
    ]

    for i, (tech, count) in enumerate(tech_counter.most_common(30), 1):
        percentage = (count / len(df)) * 100
        report_lines.append(
            f"{i:2}. {tech:30} - {count:4} vacancies ({percentage:5.1f}%)"
        )

    df_with_salary = df[df["salary"].notna()]
    if len(df_with_salary) > 0:
        report_lines.extend(
            [
                "",
                "=" * 80,
                "SALARY STATISTICS",
                "=" * 80,
                "",
                f"Vacancies with Salary Data: {len(df_with_salary)} ({len(df_with_salary)/len(df)*100:.1f}%)",
                f"Average Salary: {df_with_salary['salary'].mean():,.0f} UAH",
                f"Median Salary: {df_with_salary['salary'].median():,.0f} UAH",
                f"Min Salary: {df_with_salary['salary'].min():,.0f} UAH",
                f"Max Salary: {df_with_salary['salary'].max():,.0f} UAH",
            ]
        )

    report_lines.extend(["", "=" * 80, "REPORT END", "=" * 80])

    report_text = "\n".join(report_lines)

    output_path = OUTPUT_DIR / "statistics_report.txt"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report_text)

    logger.info(f"Saved statistics report to {output_path}")
    print("\n" + report_text)


def save_processed_data(df: pd.DataFrame, tech_counter: Counter) -> None:
    """Save processed data for future analysis."""
    logger.info("Saving processed data...")

    df_output_path = OUTPUT_DIR / "cleaned_data.csv"
    df.to_csv(df_output_path, index=False)
    logger.info(f"Saved cleaned data to {df_output_path}")

    tech_freq_path = OUTPUT_DIR / "technology_frequencies.json"
    with open(tech_freq_path, "w", encoding="utf-8") as f:
        json.dump(dict(tech_counter.most_common()), f, indent=2, ensure_ascii=False)
    logger.info(f"Saved technology frequencies to {tech_freq_path}")
