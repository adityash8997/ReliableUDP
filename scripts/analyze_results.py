from __future__ import annotations

import csv
import json
from pathlib import Path


def summarize(path: str | Path) -> dict:
    rows = []
    with Path(path).open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
    if not rows:
        raise ValueError(f"No rows found in {path}")

    summary = {
        "row_count": len(rows),
        "protocols": sorted({row["protocol"] for row in rows}),
        "mean_goodput_mbps": sum(float(row["goodput_mbps"]) for row in rows) / len(rows),
        "mean_completion_time_seconds": sum(float(row["completion_time_seconds"]) for row in rows) / len(rows),
        "mean_retransmissions": sum(float(row["retransmissions"]) for row in rows) / len(rows),
    }
    return summary


def main() -> None:
    csv_path = Path("experiments/results/summary.csv")
    summary = summarize(csv_path)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
