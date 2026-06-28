"""Visualization generation utilities."""

import logging
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from collections import Counter
import pandas as pd

logger = logging.getLogger(__name__)

plt.style.use("seaborn-v0_8-darkgrid")
sns.set_palette("husl")

OUTPUT_DIR = Path("analytics_results")
OUTPUT_DIR.mkdir(exist_ok=True)


def visualize_top_technologies(tech_counter: Counter, top_n: int = 20) -> None:
    """Create bar chart of most demanded technologies."""
    logger.info(f"Creating top {top_n} technologies chart...")

    most_common = tech_counter.most_common(top_n)
    techs, counts = zip(*most_common)

    fig, ax = plt.subplots(figsize=(14, 8))
    bars = ax.barh(
        range(len(techs)), counts, color=sns.color_palette("viridis", len(techs))
    )

    ax.set_yticks(range(len(techs)))
    ax.set_yticklabels(techs)
    ax.invert_yaxis()
    ax.set_xlabel("Number of Vacancies", fontsize=12, fontweight="bold")
    ax.set_title(
        f"Top {top_n} Most Demanded Technologies", fontsize=14, fontweight="bold"
    )
    ax.grid(axis="x", alpha=0.3)

    for i, (bar, count) in enumerate(zip(bars, counts)):
        ax.text(count + 1, i, str(count), va="center", fontsize=10, fontweight="bold")

    plt.tight_layout()
    output_path = OUTPUT_DIR / "top_technologies.png"
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    logger.info(f"Saved chart to {output_path}")
    plt.close()


def visualize_technology_distribution(df: pd.DataFrame) -> None:
    """Create distribution chart of technologies per vacancy."""
    logger.info("Creating technology distribution chart...")

    fig, ax = plt.subplots(figsize=(12, 6))

    stack_counts = df["stack_count"].value_counts().sort_index()
    ax.bar(
        stack_counts.index,
        stack_counts.values,
        color="skyblue",
        edgecolor="black",
        alpha=0.7,
    )

    ax.set_xlabel("Number of Technologies per Vacancy", fontsize=12, fontweight="bold")
    ax.set_ylabel("Number of Vacancies", fontsize=12, fontweight="bold")
    ax.set_title(
        "Distribution of Technologies per Vacancy", fontsize=14, fontweight="bold"
    )
    ax.grid(axis="y", alpha=0.3)

    for x, y in zip(stack_counts.index, stack_counts.values):
        ax.text(
            x, y + 0.5, str(y), ha="center", va="bottom", fontsize=10, fontweight="bold"
        )

    plt.tight_layout()
    output_path = OUTPUT_DIR / "tech_distribution.png"
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    logger.info(f"Saved chart to {output_path}")
    plt.close()


def analyze_salary_by_stack(
    df: pd.DataFrame, tech_counter: Counter, top_n: int = 15
) -> None:
    """Analyze average salary for top technologies."""
    logger.info("Analyzing salary by technology stack...")

    df_with_salary = df[df["salary"].notna()].copy()

    if len(df_with_salary) == 0:
        logger.warning("No salary data available, skipping salary analysis")
        return

    top_techs = [tech for tech, _ in tech_counter.most_common(top_n)]

    tech_salaries = {}
    for tech in top_techs:
        salaries = df_with_salary[
            df_with_salary["stack_cleaned"].apply(lambda x: tech in x)
        ]["salary"]
        if len(salaries) > 0:
            tech_salaries[tech] = salaries.mean()

    if not tech_salaries:
        logger.warning("Could not calculate salaries for any technology")
        return

    sorted_salaries = sorted(tech_salaries.items(), key=lambda x: x[1], reverse=True)
    techs, salaries = zip(*sorted_salaries)

    fig, ax = plt.subplots(figsize=(14, 8))
    bars = ax.barh(
        range(len(techs)), salaries, color=sns.color_palette("coolwarm", len(techs))
    )

    ax.set_yticks(range(len(techs)))
    ax.set_yticklabels(techs)
    ax.invert_yaxis()
    ax.set_xlabel("Average Salary (UAH)", fontsize=12, fontweight="bold")
    ax.set_title("Average Salary by Technology", fontsize=14, fontweight="bold")
    ax.grid(axis="x", alpha=0.3)

    for i, (bar, salary) in enumerate(zip(bars, salaries)):
        ax.text(
            salary + 500,
            i,
            f"{salary:,.0f}",
            va="center",
            fontsize=10,
            fontweight="bold",
        )

    plt.tight_layout()
    output_path = OUTPUT_DIR / "salary_by_tech.png"
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    logger.info(f"Saved chart to {output_path}")
    plt.close()


def visualize_technology_categories(categorized: dict) -> None:
    """Create pie chart of technology categories."""
    logger.info("Creating technology categories chart...")

    category_totals = {
        cat: sum(counter.values())
        for cat, counter in categorized.items()
        if sum(counter.values()) > 0
    }

    if not category_totals:
        logger.warning("No category data to visualize")
        return

    fig, ax = plt.subplots(figsize=(10, 10))

    colors = sns.color_palette("Set2", len(category_totals))
    wedges, texts, autotexts = ax.pie(
        category_totals.values(),
        labels=category_totals.keys(),
        autopct="%1.1f%%",
        colors=colors,
        startangle=90,
        textprops={"fontsize": 11, "fontweight": "bold"},
    )

    ax.set_title(
        "Technology Distribution by Category", fontsize=14, fontweight="bold", pad=20
    )

    plt.tight_layout()
    output_path = OUTPUT_DIR / "tech_categories.png"
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    logger.info(f"Saved chart to {output_path}")
    plt.close()
