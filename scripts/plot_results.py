from __future__ import annotations

import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def load_rows(csv_path: str | Path):
    with Path(csv_path).open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    csv_path = Path("experiments/results/summary.csv")
    rows = load_rows(csv_path)
    if not rows:
        raise ValueError(f"No rows found in {csv_path}")

    output_dir = Path("experiments/plots")
    output_dir.mkdir(parents=True, exist_ok=True)

    protocols = sorted({row["protocol"] for row in rows})
    for protocol in protocols:
        subset = [row for row in rows if row["protocol"] == protocol]
        x = [float(row["loss_rate"]) for row in subset]
        y = [float(row["goodput_mbps"]) for row in subset]
        fig, ax = plt.subplots()
        ax.plot(x, y, marker="o")
        ax.set_title(f"Goodput vs Loss Rate ({protocol})")
        ax.set_xlabel("Loss rate")
        ax.set_ylabel("Goodput (Mbps)")
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        fig.savefig(output_dir / f"goodput_loss_{protocol}.png", dpi=200)
        plt.close(fig)

    fig, ax = plt.subplots()
    for protocol in protocols:
        subset = [row for row in rows if row["protocol"] == protocol]
        x = [float(row["loss_rate"]) for row in subset]
        y = [float(row["retransmissions"]) for row in subset]
        ax.plot(x, y, marker="o", label=protocol)
    ax.set_title("Retransmissions vs Loss Rate")
    ax.set_xlabel("Loss rate")
    ax.set_ylabel("Retransmissions")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_dir / "retransmissions_loss.png", dpi=200)
    plt.close(fig)

    print(f"Plots saved to {output_dir}")


if __name__ == "__main__":
    main()
