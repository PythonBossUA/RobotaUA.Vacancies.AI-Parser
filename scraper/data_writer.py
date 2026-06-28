"""CSV writing and data cleaning utilities."""

import csv
from pathlib import Path


def write_csv(data: list[dict], path: Path) -> None:
    """Write data to CSV file with proper headers."""
    with open(path, "a", newline="", encoding="utf-8") as cf:
        is_file_empty = path.stat().st_size == 0
        writer = csv.DictWriter(cf, fieldnames=data[0].keys())

        if is_file_empty:
            writer.writeheader()

        writer.writerows(data)


def clean_data(raw_data: list[dict[str, str]]) -> None:
    """Clean and normalize scraped data in-place."""
    for element in raw_data:
        element["id"] = int(element["id"])
        element["description"] = element["description"].replace(" ", " ").strip(" \n\t")
        element["salary"] = (
            element["salary"]["amount"] or None
            if isinstance(element["salary"], dict)
            else None
        )
        element["company"] = (
            element["company"]["name"] if isinstance(element["company"], dict) else None
        )
        element["city"] = (
            element["city"]["name"] if isinstance(element["city"], dict) else None
        )
        element.pop("__typename", None)
