"""Inspect a CSV file with ``python -m csvpeek PATH``."""

import argparse
import csv
from pathlib import Path


def summarize(path: Path) -> tuple[int, list[str], list[int]]:
    with path.open(encoding="utf-8", newline="") as file:
        reader = csv.reader(file, strict=True)
        columns = next(reader, None)
        if columns is None:
            raise ValueError("CSV file is empty")
        if not columns:
            raise ValueError("CSV header contains no columns")

        missing = [0] * len(columns)
        row_count = 0
        for record_number, row in enumerate(reader, start=2):
            if len(row) != len(columns):
                raise ValueError(
                    f"record {record_number}: expected {len(columns)} fields, "
                    f"got {len(row)}"
                )
            row_count += 1
            for index, value in enumerate(row):
                if value == "":
                    missing[index] += 1

    return row_count, columns, missing


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="csvpeek", description="Show CSV row counts, columns, and missing values."
    )
    parser.add_argument("path", type=Path, help="UTF-8 CSV file to inspect")
    args = parser.parse_args()
    try:
        row_count, columns, missing = summarize(args.path)
    except (OSError, UnicodeError, csv.Error, ValueError) as error:
        parser.error(f"{args.path}: {error}")

    print(f"Rows: {row_count}")
    print(f"Columns: {', '.join(columns)}")
    print("Missing values:")
    for column, count in zip(columns, missing):
        print(f"  {column}: {count}")


if __name__ == "__main__":
    main()
