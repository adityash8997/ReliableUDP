from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

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
    parser = argparse.ArgumentParser(description="Run actual UDP experiments or explicitly synthetic demo data")
    parser.add_argument("--output-dir", default="experiments/results")
    parser.add_argument("--mode", choices=["actual", "synthetic"], default="actual")
    parser.add_argument("--config-file", help="Optional JSON config object or list of config objects")
    parser.add_argument("--demo-sweep", action="store_true", help="Run the legacy synthetic sweep; requires --mode synthetic")
    parser.add_argument("--protocol", default="stop-and-wait")
    parser.add_argument("--file", dest="test_file")
    parser.add_argument("--file-size-bytes", type=int, default=1024)
    parser.add_argument("--payload-size-bytes", type=int, default=1024)
    parser.add_argument("--window-size", type=int, default=1)
    parser.add_argument("--loss-rate", type=float, default=0.0)
    parser.add_argument("--duplication-rate", type=float, default=0.0)
    parser.add_argument("--corruption-rate", type=float, default=0.0)
    parser.add_argument("--reordering-rate", type=float, default=0.0)
    parser.add_argument("--delay-ms", type=float, default=0.0)
    parser.add_argument("--jitter-ms", type=float, default=0.0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--repetitions", type=int, default=1)
    parser.add_argument("--rto-ms", type=float, default=300.0)
    parser.add_argument("--max-execution-seconds", type=float, default=30.0)
    args = parser.parse_args()

    if args.demo_sweep and args.mode != "synthetic":
        parser.error("--demo-sweep is synthetic-only; pass --mode synthetic explicitly")

    if args.demo_sweep:
        configs = build_base_configs()
    elif args.config_file:
        with Path(args.config_file).open("r", encoding="utf-8") as handle:
            loaded = json.load(handle)
        configs = [ExperimentConfig(**item) for item in (loaded if isinstance(loaded, list) else [loaded])]
    else:
        configs = [ExperimentConfig(
            protocol=args.protocol,
            test_file=args.test_file,
            file_size_bytes=args.file_size_bytes,
            payload_size_bytes=args.payload_size_bytes,
            window_size=args.window_size,
            loss_rate=args.loss_rate,
            duplication_rate=args.duplication_rate,
            corruption_rate=args.corruption_rate,
            reordering_rate=args.reordering_rate,
            delay_ms=args.delay_ms,
            jitter_ms=args.jitter_ms,
            seed=args.seed,
            repetitions=args.repetitions,
            rto_ms=args.rto_ms,
            max_execution_seconds=args.max_execution_seconds,
        )]

    runner = ExperimentRunner(args.output_dir, mode=args.mode)
    results = runner.run_suite(configs)
    for result in results:
        print(json.dumps(result.to_dict(), indent=2))
    if any(result.execution_status != "completed" for result in results) and args.mode == "actual":
        sys.exit(1)


if __name__ == "__main__":
    main()
