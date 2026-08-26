from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, List, Optional

from .config import ChannelConfig, ProtocolConfig


@dataclass
class ExperimentConfig:
    """Configuration for a single experiment run."""

    protocol: str
    loss_rate: float
    duplication_rate: float = 0.0
    corruption_rate: float = 0.0
    reordering_rate: float = 0.0
    delay_ms: float = 0.0
    jitter_ms: float = 0.0
    window_size: int = 1
    rto_ms: float = 500.0
    seed: int = 42
    file_size_bytes: int = 1024 * 1024
    repetitions: int = 3
    notes: str = ""

    def as_protocol_config(self) -> ProtocolConfig:
        return ProtocolConfig(
            protocol=self.protocol,
            window_size=self.window_size,
            rto_ms=self.rto_ms,
        )

    def as_channel_config(self) -> ChannelConfig:
        return ChannelConfig(
            loss_probability=self.loss_rate,
            duplication_probability=self.duplication_rate,
            corruption_probability=self.corruption_rate,
            reordering_probability=self.reordering_rate,
            base_delay_ms=self.delay_ms,
            jitter_ms=self.jitter_ms,
            seed=self.seed,
        )


@dataclass
class ExperimentResult:
    """Structured result stored as JSON/CSV."""

    timestamp: str
    protocol: str
    file_size_bytes: int
    payload_size_bytes: int
    window_size: int
    loss_rate: float
    duplication_rate: float
    corruption_rate: float
    reordering_rate: float
    delay_ms: float
    jitter_ms: float
    seed: int
    rto_ms: float
    repetitions: int
    completion_time_seconds: float
    goodput_mbps: float
    retransmissions: int
    packets_sent: int
    packets_received: int
    duplicate_packets: int
    corrupted_packets: int
    timeout_count: int
    integrity_pass: bool
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ExperimentRunner:
    """Experiment runner creating reproducible result files.

    The runner supports a real protocol callback when one is available. If no
    callback is supplied, it uses a deterministic synthetic baseline so the
    experiment pipeline can still be exercised without claiming that the core
    ARQ algorithms are implemented.
    """

    def __init__(self, results_dir: str | Path):
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)

    def _synthetic_result(self, config: ExperimentConfig) -> ExperimentResult:
        base = 1.0 / (1.0 + config.loss_rate * 20.0)
        window_factor = min(1.0, config.window_size / 16.0)
        completion_time = max(0.05, 1.0 + config.loss_rate * 10.0 + config.reordering_rate * 3.0 + config.delay_ms / 1000.0)
        goodput = max(0.01, (base * window_factor * 10.0) / completion_time)
        retransmissions = int(max(0, config.loss_rate * 100.0 + config.reordering_rate * 25.0))
        packets_sent = int(max(10, config.file_size_bytes / 512.0 + retransmissions))
        packets_received = packets_sent - retransmissions
        duplicate_packets = int(max(0, config.duplication_rate * 10.0))
        corrupted_packets = int(max(0, config.corruption_rate * 10.0))
        timeout_count = int(max(0, (config.loss_rate + config.reordering_rate) * 20.0))
        return ExperimentResult(
            timestamp=datetime.now(timezone.utc).isoformat(),
            protocol=config.protocol,
            file_size_bytes=config.file_size_bytes,
            payload_size_bytes=max(512, config.file_size_bytes),
            window_size=config.window_size,
            loss_rate=config.loss_rate,
            duplication_rate=config.duplication_rate,
            corruption_rate=config.corruption_rate,
            reordering_rate=config.reordering_rate,
            delay_ms=config.delay_ms,
            jitter_ms=config.jitter_ms,
            seed=config.seed,
            rto_ms=config.rto_ms,
            repetitions=config.repetitions,
            completion_time_seconds=completion_time,
            goodput_mbps=goodput,
            retransmissions=retransmissions,
            packets_sent=packets_sent,
            packets_received=packets_received,
            duplicate_packets=duplicate_packets,
            corrupted_packets=corrupted_packets,
            timeout_count=timeout_count,
            integrity_pass=True,
            notes=config.notes,
        )

    def run_single(self, config: ExperimentConfig, protocol_runner: Optional[Callable[[ExperimentConfig], ExperimentResult]] = None) -> ExperimentResult:
        result = (protocol_runner(config) if protocol_runner is not None else self._synthetic_result(config))
        result_path = self.results_dir / f"{config.protocol}_{config.seed}_{config.loss_rate}_{config.window_size}.json"
        with result_path.open("w", encoding="utf-8") as handle:
            json.dump(result.to_dict(), handle, indent=2)
        return result

    def run_suite(self, configs: Iterable[ExperimentConfig], protocol_runner: Optional[Callable[[ExperimentConfig], ExperimentResult]] = None) -> List[ExperimentResult]:
        results: List[ExperimentResult] = []
        for config in configs:
            results.append(self.run_single(config, protocol_runner=protocol_runner))
        return results

    def export_csv(self, results: Iterable[ExperimentResult], csv_path: str | Path) -> Path:
        path = Path(csv_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        fieldnames = [
            "timestamp",
            "protocol",
            "file_size_bytes",
            "payload_size_bytes",
            "window_size",
            "loss_rate",
            "duplication_rate",
            "corruption_rate",
            "reordering_rate",
            "delay_ms",
            "jitter_ms",
            "seed",
            "rto_ms",
            "repetitions",
            "completion_time_seconds",
            "goodput_mbps",
            "retransmissions",
            "packets_sent",
            "packets_received",
            "duplicate_packets",
            "corrupted_packets",
            "timeout_count",
            "integrity_pass",
            "notes",
        ]
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for item in results:
                writer.writerow(item.to_dict())
        return path
