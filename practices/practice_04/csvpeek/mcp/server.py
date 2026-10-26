from __future__ import annotations

import csv
from pathlib import Path

from mcp.server import MCPServer

server = MCPServer("csv-inspector")

PROJECT_ROOT = Path(__file__).resolve().parents[1]


@server.tool()
def inspect_csv(path: str, sample_rows: int = 3) -> dict:
    """Inspect a CSV file from this repository.

    Returns its header, row count, missing-value counts,
    malformed rows, and a small sample.
    """
    if sample_rows < 0 or sample_rows > 10:
        raise ValueError("sample_rows must be between 0 and 10")

    requested = Path(path)
    if requested.is_absolute():
        raise ValueError("path must be relative to the project root")

    resolved = (PROJECT_ROOT / requested).resolve()

    if PROJECT_ROOT not in resolved.parents:
        raise ValueError("path must stay inside the project root")

    if resolved.suffix.lower() != ".csv":
        raise ValueError("only .csv files are supported")

    if not resolved.exists():
        raise FileNotFoundError(f"CSV file does not exist: {path}")

    if not resolved.is_file():
        raise ValueError(f"path is not a file: {path}")

    with resolved.open(newline="", encoding="utf-8") as file:
        reader = csv.reader(file)

        try:
            header = next(reader)
        except StopIteration as error:
            raise ValueError("CSV file is empty") from error

        if not header:
            raise ValueError("CSV header contains no columns")

        missing_values = {column: 0 for column in header}
        malformed_rows: list[int] = []
        sample: list[list[str]] = []
        row_count = 0

        for line_number, row in enumerate(reader, start=2):
            row_count += 1

            if len(sample) < sample_rows:
                sample.append(row)

            if len(row) != len(header):
                malformed_rows.append(line_number)
                continue

            for column, value in zip(header, row):
                if value == "":
                    missing_values[column] += 1

    return {
        "path": path,
        "columns": header,
        "row_count": row_count,
        "missing_values": missing_values,
        "malformed_rows": malformed_rows,
        "sample": sample,
    }


if __name__ == "__main__":
    server.run(transport="stdio")
