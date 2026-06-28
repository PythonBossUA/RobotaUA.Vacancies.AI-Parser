import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from collections import Counter
import json
import logging
from typing import Optional
import config

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Configure matplotlib for better-looking plots
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")

OUTPUT_DIR = Path("analytics_results")
OUTPUT_DIR.mkdir(exist_ok=True)


def load_data(csv_path: str = config.CSV_FILENAME) -> Optional[pd.DataFrame]:
    """Load and validate scraped data from CSV."""
    try:
        df = pd.read_csv(csv_path)
        logger.info(f"Loaded {len(df)} vacancies from {csv_path}")

        if df.empty:
            logger.error("CSV file is empty")
            return None

        required_columns = ['id', 'title', 'stack']
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


def clean_stack_data(df: pd.DataFrame) -> pd.DataFrame:
    """Clean and parse stack column from string to list."""
    logger.info("Cleaning stack data...")

    def parse_stack(stack_str):
        """Parse stack string to list of technologies."""
        if pd.isna(stack_str) or stack_str == '[]' or stack_str == '':
            return []

        try:
            # Try to parse as JSON
            if isinstance(stack_str, str):
                stack_list = json.loads(stack_str.replace("'", '"'))
            else:
                stack_list = stack_str

            # Clean and normalize
            return [tech.strip().upper() for tech in stack_list if tech.strip()]
        except:
            # Fallback: split by comma
            return [tech.strip().upper() for tech in str(stack_str).split(',') if tech.strip()]

    df['stack_cleaned'] = df['stack'].apply(parse_stack)
    df['stack_count'] = df['stack_cleaned'].apply(len)

    # Remove vacancies with no stack data
    initial_count = len(df)
    df = df[df['stack_count'] > 0].copy()
    removed = initial_count - len(df)

    if removed > 0:
        logger.warning(f"Removed {removed} vacancies with no stack data")

    logger.info(f"Cleaned {len(df)} vacancies with valid stack data")
    return df


def extract_all_technologies(df: pd.DataFrame) -> Counter:
    """Extract and count all technologies across all vacancies."""
    logger.info("Extracting technology frequencies...")

    all_techs = []
    for stack_list in df['stack_cleaned']:
        all_techs.extend(stack_list)

    tech_counter = Counter(all_techs)
    logger.info(f"Found {len(tech_counter)} unique technologies")

    return tech_counter


def visualize_top_technologies(tech_counter: Counter, top_n: int = 20) -> None:
    """Create bar chart of most demanded technologies."""
    logger.info(f"Creating top {top_n} technologies chart...")

    most_common = tech_counter.most_common(top_n)
    techs, counts = zip(*most_common)

    fig, ax = plt.subplots(figsize=(14, 8))
    bars = ax.barh(range(len(techs)), counts, color=sns.color_palette("viridis", len(techs)))

    ax.set_yticks(range(len(techs)))
    ax.set_yticklabels(techs)
    ax.invert_yaxis()
    ax.set_xlabel('Number of Vacancies', fontsize=12, fontweight='bold')
    ax.set_title(f'Top {top_n} Most Demanded Technologies', fontsize=14, fontweight='bold')
    ax.grid(axis='x', alpha=0.3)

    # Add value labels on bars
    for i, (bar, count) in enumerate(zip(bars, counts)):
        ax.text(count + 1, i, str(count), va='center', fontsize=10, fontweight='bold')

    plt.tight_layout()
    output_path = OUTPUT_DIR / 'top_technologies.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    logger.info(f"Saved chart to {output_path}")
    plt.close()


def visualize_technology_distribution(df: pd.DataFrame) -> None:
    """Create distribution chart of technologies per vacancy."""
    logger.info("Creating technology distribution chart...")

    fig, ax = plt.subplots(figsize=(12, 6))

    stack_counts = df['stack_count'].value_counts().sort_index()
    ax.bar(stack_counts.index, stack_counts.values, color='skyblue', edgecolor='black', alpha=0.7)

    ax.set_xlabel('Number of Technologies per Vacancy', fontsize=12, fontweight='bold')
    ax.set_ylabel('Number of Vacancies', fontsize=12, fontweight='bold')
    ax.set_title('Distribution of Technologies per Vacancy', fontsize=14, fontweight='bold')
    ax.grid(axis='y', alpha=0.3)

    # Add value labels
    for x, y in zip(stack_counts.index, stack_counts.values):
        ax.text(x, y + 0.5, str(y), ha='center', va='bottom', fontsize=10, fontweight='bold')

    plt.tight_layout()
    output_path = OUTPUT_DIR / 'tech_distribution.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    logger.info(f"Saved chart to {output_path}")
    plt.close()


def analyze_salary_by_stack(df: pd.DataFrame, tech_counter: Counter, top_n: int = 15) -> None:
    """Analyze average salary for top technologies."""
    logger.info("Analyzing salary by technology stack...")

    # Filter out vacancies without salary
    df_with_salary = df[df['salary'].notna()].copy()

    if len(df_with_salary) == 0:
        logger.warning("No salary data available, skipping salary analysis")
        return

    top_techs = [tech for tech, _ in tech_counter.most_common(top_n)]

    tech_salaries = {}
    for tech in top_techs:
        salaries = df_with_salary[df_with_salary['stack_cleaned'].apply(lambda x: tech in x)]['salary']
        if len(salaries) > 0:
            tech_salaries[tech] = salaries.mean()

    if not tech_salaries:
        logger.warning("Could not calculate salaries for any technology")
        return

    # Sort by salary
    sorted_salaries = sorted(tech_salaries.items(), key=lambda x: x[1], reverse=True)
    techs, salaries = zip(*sorted_salaries)

    fig, ax = plt.subplots(figsize=(14, 8))
    bars = ax.barh(range(len(techs)), salaries, color=sns.color_palette("coolwarm", len(techs)))

    ax.set_yticks(range(len(techs)))
    ax.set_yticklabels(techs)
    ax.invert_yaxis()
    ax.set_xlabel('Average Salary (UAH)', fontsize=12, fontweight='bold')
    ax.set_title('Average Salary by Technology', fontsize=14, fontweight='bold')
    ax.grid(axis='x', alpha=0.3)

    # Add value labels
    for i, (bar, salary) in enumerate(zip(bars, salaries)):
        ax.text(salary + 500, i, f'{salary:,.0f}', va='center', fontsize=10, fontweight='bold')

    plt.tight_layout()
    output_path = OUTPUT_DIR / 'salary_by_tech.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    logger.info(f"Saved chart to {output_path}")
    plt.close()


def create_technology_categories(tech_counter: Counter) -> dict:
    """Categorize technologies by type."""
    logger.info("Categorizing technologies...")

    categories = {
        'Languages': ['PYTHON', 'JAVASCRIPT', 'JAVA', 'C++', 'C#', 'GO', 'RUBY', 'PHP', 'TYPESCRIPT', 'KOTLIN', 'SWIFT', 'RUST'],
        'Web Frameworks': ['DJANGO', 'FLASK', 'FASTAPI', 'REACT', 'VUE', 'ANGULAR', 'EXPRESS', 'SPRING', 'LARAVEL', 'RAILS', 'NEXTJS', 'NUXT'],
        'Databases': ['POSTGRESQL', 'MYSQL', 'MONGODB', 'REDIS', 'ELASTICSEARCH', 'CASSANDRA', 'ORACLE', 'MSSQL', 'SQLITE', 'DYNAMODB'],
        'Cloud & DevOps': ['AWS', 'DOCKER', 'KUBERNETES', 'AZURE', 'GCP', 'TERRAFORM', 'JENKINS', 'GITLAB', 'GITHUB', 'CI/CD', 'ANSIBLE'],
        'Data & ML': ['PANDAS', 'NUMPY', 'TENSORFLOW', 'PYTORCH', 'SCIKIT-LEARN', 'KERAS', 'SPARK', 'HADOOP', 'AIRFLOW', 'KAFKA'],
        'Tools & Other': []
    }

    categorized = {cat: Counter() for cat in categories}
    uncategorized = set()

    for tech, count in tech_counter.items():
        found = False
        for category, keywords in categories.items():
            if category == 'Tools & Other':
                continue
            if any(keyword in tech or tech in keyword for keyword in keywords):
                categorized[category][tech] = count
                found = True
                break

        if not found:
            categorized['Tools & Other'][tech] = count
            uncategorized.add(tech)

    return categorized


def visualize_technology_categories(categorized: dict) -> None:
    """Create pie chart of technology categories."""
    logger.info("Creating technology categories chart...")

    category_totals = {cat: sum(counter.values()) for cat, counter in categorized.items() if sum(counter.values()) > 0}

    if not category_totals:
        logger.warning("No category data to visualize")
        return

    fig, ax = plt.subplots(figsize=(10, 10))

    colors = sns.color_palette("Set2", len(category_totals))
    wedges, texts, autotexts = ax.pie(
        category_totals.values(),
        labels=category_totals.keys(),
        autopct='%1.1f%%',
        colors=colors,
        startangle=90,
        textprops={'fontsize': 11, 'fontweight': 'bold'}
    )

    ax.set_title('Technology Distribution by Category', fontsize=14, fontweight='bold', pad=20)

    plt.tight_layout()
    output_path = OUTPUT_DIR / 'tech_categories.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    logger.info(f"Saved chart to {output_path}")
    plt.close()


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
        ""
    ]

    for i, (tech, count) in enumerate(tech_counter.most_common(30), 1):
        percentage = (count / len(df)) * 100
        report_lines.append(f"{i:2}. {tech:30} - {count:4} vacancies ({percentage:5.1f}%)")

    # Add salary analysis if available
    df_with_salary = df[df['salary'].notna()]
    if len(df_with_salary) > 0:
        report_lines.extend([
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
        ])

    report_lines.extend([
        "",
        "=" * 80,
        "REPORT END",
        "=" * 80
    ])

    report_text = "\n".join(report_lines)

    output_path = OUTPUT_DIR / 'statistics_report.txt'
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(report_text)

    logger.info(f"Saved statistics report to {output_path}")
    print("\n" + report_text)


def save_processed_data(df: pd.DataFrame, tech_counter: Counter) -> None:
    """Save processed data for future analysis."""
    logger.info("Saving processed data...")

    # Save cleaned dataframe
    df_output_path = OUTPUT_DIR / 'cleaned_data.csv'
    df.to_csv(df_output_path, index=False)
    logger.info(f"Saved cleaned data to {df_output_path}")

    # Save technology frequency as JSON
    tech_freq_path = OUTPUT_DIR / 'technology_frequencies.json'
    with open(tech_freq_path, 'w', encoding='utf-8') as f:
        json.dump(dict(tech_counter.most_common()), f, indent=2, ensure_ascii=False)
    logger.info(f"Saved technology frequencies to {tech_freq_path}")


def run_full_analysis() -> None:
    """Run complete analysis pipeline."""
    logger.info("Starting full analysis pipeline...")

    # Load data
    df = load_data()
    if df is None:
        return

    # Clean data
    df = clean_stack_data(df)
    if len(df) == 0:
        logger.error("No valid data after cleaning")
        return

    # Extract technologies
    tech_counter = extract_all_technologies(df)

    # Generate visualizations
    visualize_top_technologies(tech_counter, top_n=20)
    visualize_technology_distribution(df)
    analyze_salary_by_stack(df, tech_counter, top_n=15)

    # Categorize and visualize
    categorized = create_technology_categories(tech_counter)
    visualize_technology_categories(categorized)

    # Generate reports
    generate_statistics_report(df, tech_counter)
    save_processed_data(df, tech_counter)

    logger.info(f"Analysis complete! Results saved to {OUTPUT_DIR}/")
    print(f"\n✅ Analysis complete! Check the '{OUTPUT_DIR}' folder for results.")


if __name__ == "__main__":
    run_full_analysis()
