from __future__ import annotations

import argparse
import json
from pathlib import Path

from reliable_udp.experiment import ExperimentConfig, ExperimentRunner


def build_base_configs() -> list[ExperimentConfig]:
    configs: list[ExperimentConfig] = []
    protocols = ["stop-and-wait", "go-back-n", "selective-repeat"]
    loss_rates = [0.0, 0.01, 0.02, 0.05, 0.10, 0.15, 0.20]
    windows = [1, 2, 4, 8, 16, 32]

    for protocol in protocols:
        for loss_rate in loss_rates:
            configs.append(
                ExperimentConfig(
                    protocol=protocol,
                    loss_rate=loss_rate,
                    duplication_rate=0.01,
                    corruption_rate=0.005,
                    reordering_rate=0.02,
                    delay_ms=50,
                    jitter_ms=20,
                    window_size=4 if protocol != "stop-and-wait" else 1,
                    rto_ms=500.0,
                    seed=42,
                    file_size_bytes=1024 * 1024,
                    repetitions=3,
                    notes="loss-rate sweep",
                )
            )

    for protocol in ["go-back-n", "selective-repeat"]:
        for window in windows:
            configs.append(
                ExperimentConfig(
                    protocol=protocol,
                    loss_rate=0.05,
                    duplication_rate=0.01,
                    corruption_rate=0.005,
                    reordering_rate=0.02,
                    delay_ms=50,
                    jitter_ms=20,
                    window_size=window,
                    rto_ms=500.0,
                    seed=42,
                    file_size_bytes=1024 * 1024,
                    repetitions=3,
                    notes="window-size sweep",
                )
            )

    return configs


def main() -> None:
    parser = argparse.ArgumentParser(description="Run deterministic experiment sweeps for the reliable UDP project")
    parser.add_argument("--output-dir", default="experiments/results")
    parser.add_argument("--config-file", default="experiments/configs/default.json")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    configs = build_base_configs()
    config_path = Path(args.config_file)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with config_path.open("w", encoding="utf-8") as handle:
        json.dump([cfg.__dict__ for cfg in configs], handle, indent=2)

    runner = ExperimentRunner(output_dir)
    results = runner.run_suite(configs)
    csv_path = output_dir / "summary.csv"
    runner.export_csv(results, csv_path)
    print(f"Saved {len(results)} experiment results to {output_dir}")


if __name__ == "__main__":
    main()
