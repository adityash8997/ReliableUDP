from __future__ import annotations

import csv
import json
import math
import platform
import random
import queue
import tempfile
import threading
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional
from uuid import uuid4

from .config import ChannelConfig, ProtocolConfig, TransferConfig
from .file_transfer import compute_file_hash
from .metrics import MetricsCollector
from .receiver import ReceiverApplication
from .sender import SenderApplication


@dataclass
class ExperimentConfig:
    """Inputs for actual or explicitly synthetic experiment runs."""

    protocol: str = "stop-and-wait"
    loss_rate: float = 0.0
    duplication_rate: float = 0.0
    corruption_rate: float = 0.0
    reordering_rate: float = 0.0
    delay_ms: float = 0.0
    jitter_ms: float = 0.0
    window_size: int = 1
    rto_ms: float = 300.0
    seed: int = 42
    file_size_bytes: int = 1024
    payload_size_bytes: int = 1024
    repetitions: int = 1
    test_file: Optional[str] = None
    max_execution_seconds: float = 30.0
    notes: str = ""

    def as_protocol_config(self) -> ProtocolConfig:
        return ProtocolConfig(
            protocol=self.protocol,
            window_size=self.window_size,
            rto_ms=self.rto_ms,
            packet_size=self.payload_size_bytes,
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

    def validate(self, *, mode: str = "actual") -> None:
        if mode not in {"actual", "synthetic"}:
            raise ValueError("mode must be 'actual' or 'synthetic'")
        integer_values = {
            "window_size": self.window_size,
            "seed": self.seed,
            "file_size_bytes": self.file_size_bytes,
            "payload_size_bytes": self.payload_size_bytes,
            "repetitions": self.repetitions,
        }
        if any(not isinstance(value, int) or isinstance(value, bool) for value in integer_values.values()):
            raise ValueError("window_size, seed, file_size_bytes, payload_size_bytes, and repetitions must be integers")
        numeric_values = {
            "loss_rate": self.loss_rate,
            "duplication_rate": self.duplication_rate,
            "corruption_rate": self.corruption_rate,
            "reordering_rate": self.reordering_rate,
            "delay_ms": self.delay_ms,
            "jitter_ms": self.jitter_ms,
            "rto_ms": self.rto_ms,
            "max_execution_seconds": self.max_execution_seconds,
        }
        if any(not isinstance(value, (int, float)) or isinstance(value, bool) for value in numeric_values.values()):
            raise ValueError("Probability, delay, RTO, and timeout values must be numeric")
        if any(not math.isfinite(value) for value in numeric_values.values()):
            raise ValueError("Experiment numeric values must be finite")
        self.as_protocol_config().validate()
        self.as_channel_config().validate()
        if self.file_size_bytes < 0:
            raise ValueError("file_size_bytes must not be negative")
        if not 1 <= self.payload_size_bytes <= 65489:
            raise ValueError("payload_size_bytes must be in range [1, 65489]")
        if self.repetitions <= 0:
            raise ValueError("repetitions must be positive")
        if self.max_execution_seconds <= 0:
            raise ValueError("max_execution_seconds must be positive")
        if self.rto_ms <= 0:
            raise ValueError("rto_ms must be positive")
        if self.protocol == "stop-and-wait" and self.window_size != 1:
            raise ValueError("Stop-and-Wait requires window_size=1")
        if self.test_file is not None and not Path(self.test_file).is_file():
            raise FileNotFoundError(f"Test file does not exist: {self.test_file}")
        if mode == "actual":
            if self.protocol != "stop-and-wait":
                raise NotImplementedError(
                    f"Actual experiments for {self.protocol!r} are unavailable; only Stop-and-Wait is implemented."
                )
            impairments = {
                "loss_rate": self.loss_rate,
                "duplication_rate": self.duplication_rate,
                "corruption_rate": self.corruption_rate,
                "reordering_rate": self.reordering_rate,
                "delay_ms": self.delay_ms,
                "jitter_ms": self.jitter_ms,
            }
            enabled = [name for name, value in impairments.items() if value != 0]
            if enabled:
                raise NotImplementedError(
                    "Actual channel impairments are not connected to the UDP path: " + ", ".join(enabled)
                )


@dataclass
class ExperimentResult:
    """One immutable run record; absent measurements remain JSON null/CSV empty."""

    schema_version: int
    experiment_id: str
    run_id: str
    result_source: str
    protocol: str
    execution_status: str
    execution_timestamp: str
    random_seed: int
    repetition: int
    configuration: dict[str, Any]
    environment: dict[str, Any] = field(default_factory=dict)
    metrics: dict[str, Any] = field(default_factory=dict)
    integrity: dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def completion_time_seconds(self) -> Optional[float]:
        return self.metrics.get("transfer_duration_seconds")

    @property
    def goodput_mbps(self) -> Optional[float]:
        value = self.metrics.get("goodput_bps")
        return value / 1_000_000 if value is not None else None

    @property
    def retransmissions(self) -> Optional[int]:
        value = self.metrics.get("retransmissions")
        return int(value) if value is not None else None


class ExperimentRunner:
    """Run actual transfers by default; synthetic generation is explicit demo-only."""

    CSV_FIELDS = [
        "schema_version", "experiment_id", "run_id", "result_source", "protocol",
        "execution_status", "execution_timestamp", "random_seed", "repetition",
        "configuration_json", "transfer_id", "start_time", "completion_time",
        "transfer_duration_seconds", "source_file_size_bytes", "reconstructed_file_size_bytes",
        "data_packets_transmitted", "data_packets_received", "control_packets_transmitted",
        "control_packets_received", "ack_packets_transmitted", "ack_packets_received",
        "retransmissions", "duplicate_packets", "corrupted_packets", "timeouts",
        "total_useful_payload_bytes", "total_transmitted_bytes", "throughput_bps", "goodput_bps",
        "packet_loss_rate", "rtt_mean_ms", "rto_mean_ms", "source_sha256",
        "destination_sha256", "integrity_pass", "error", "notes",
    ]

    def __init__(self, results_dir: str | Path, *, mode: str = "actual"):
        if mode not in {"actual", "synthetic"}:
            raise ValueError("mode must be 'actual' or 'synthetic'")
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.mode = mode

    def _base_result(
        self, config: ExperimentConfig, experiment_id: str, repetition: int, seed: int,
        source: str, status: str, metrics: dict[str, Any], integrity: dict[str, Any],
        error: Optional[str] = None, configuration: Optional[dict[str, Any]] = None,
    ) -> ExperimentResult:
        config_values = asdict(config)
        if configuration:
            config_values.update(configuration)
        configuration_data = {
            "protocol": {
                "name": config.protocol,
                "window_size": config.window_size,
                "payload_size_bytes": config.payload_size_bytes,
                "rto_ms": config.rto_ms,
            },
            "channel": {
                "loss_rate": config.loss_rate,
                "duplication_rate": config.duplication_rate,
                "corruption_rate": config.corruption_rate,
                "reordering_rate": config.reordering_rate,
                "delay_ms": config.delay_ms,
                "jitter_ms": config.jitter_ms,
                "seed": seed,
            },
            "file": {
                "file_size_bytes": config_values["file_size_bytes"],
                "test_file": config.test_file,
            },
            "run": {
                "repetition": repetition,
                "repetitions": config.repetitions,
                "seed": seed,
                "max_execution_seconds": config.max_execution_seconds,
            },
            "notes": config.notes,
        }
        return ExperimentResult(
            schema_version=1,
            experiment_id=experiment_id,
            run_id=str(uuid4()),
            result_source=source,
            protocol=config.protocol,
            execution_status=status,
            execution_timestamp=datetime.now(timezone.utc).isoformat(),
            random_seed=seed,
            repetition=repetition,
            configuration=configuration_data,
            environment={
                "python_version": platform.python_version(),
                "python_implementation": platform.python_implementation(),
                "platform": platform.platform(),
                "timing_note": "Payload generation is deterministic by seed; wall-clock duration depends on OS scheduling and host load.",
            },
            metrics=metrics,
            integrity=integrity,
            error=error,
            notes=config.notes,
        )

    @staticmethod
    def _write_source(path: Path, size: int, seed: int) -> None:
        rng = random.Random(seed)
        remaining = size
        with path.open("wb") as handle:
            while remaining:
                chunk = rng.randbytes(min(65536, remaining))
                handle.write(chunk)
                remaining -= len(chunk)

    def _run_actual(self, config: ExperimentConfig, experiment_id: str, repetition: int, seed: int) -> ExperimentResult:
        collector = MetricsCollector()
        config_for_run = {"seed": seed}
        source_hash: Optional[str] = None
        source_size: Optional[int] = None
        started = time.monotonic()
        deadline = started + config.max_execution_seconds
        receiver_thread: Optional[threading.Thread] = None
        sender: Optional[SenderApplication] = None

        try:
            with tempfile.TemporaryDirectory(prefix="reliable-udp-") as temp_dir:
                temp_path = Path(temp_dir)
                if config.test_file:
                    source = Path(config.test_file)
                else:
                    source = temp_path / "source.bin"
                    self._write_source(source, config.file_size_bytes, seed)
                destination = temp_path / "received.bin"
                source_hash, source_size = compute_file_hash(source)
                config_for_run["file_size_bytes"] = source_size

                protocol_config = config.as_protocol_config()
                receiver = ReceiverApplication(
                    protocol_config,
                    host="127.0.0.1",
                    port=0,
                    metrics_collector=collector,
                )

                ready: queue.Queue[tuple[str, Any]] = queue.Queue(maxsize=1)
                receiver_result: dict[str, Any] = {}

                def notify_ready(port: int) -> None:
                    ready.put(("ready", port))

                def receive() -> None:
                    try:
                        receiver_result.update(receiver.receive_file(
                            str(destination),
                            overwrite=True,
                            metrics_collector=collector,
                            overall_timeout_seconds=config.max_execution_seconds,
                            ready_callback=notify_ready,
                        ))
                    except Exception as exc:
                        receiver_result["error"] = exc
                        try:
                            ready.put_nowait(("error", exc))
                        except queue.Full:
                            pass

                receiver_thread = threading.Thread(target=receive, name=f"udp-receiver-{repetition}", daemon=True)
                receiver_thread.start()
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError("Experiment execution deadline exceeded before receiver startup")
                try:
                    event, value = ready.get(timeout=remaining)
                except queue.Empty as exc:
                    raise TimeoutError("Timed out waiting for receiver socket startup") from exc
                if event == "error":
                    raise value
                transfer_config = TransferConfig(
                    protocol=protocol_config,
                    channel=config.as_channel_config(),
                    host="127.0.0.1",
                    port=int(value),
                )
                sender = SenderApplication(transfer_config, metrics_collector=collector)
                try:
                    sender.send_file(
                        str(source), str(destination), overwrite=True,
                        deadline_monotonic=deadline,
                    )
                finally:
                    sender.protocol.transport.close()
                    remaining = deadline - time.monotonic()
                    if receiver_thread.is_alive():
                        receiver_thread.join(max(0.0, remaining) + protocol_config.rto_ms / 1000 + 0.1)
                if receiver_thread.is_alive():
                    raise TimeoutError("Timed out waiting for receiver completion")
                if "error" in receiver_result:
                    raise receiver_result["error"]

                destination_hash, destination_size = compute_file_hash(destination)
                integrity_pass = source_hash == destination_hash and source_size == destination_size
                metrics = collector.to_dict()
                integrity = {
                    "source_sha256": source_hash,
                    "destination_sha256": destination_hash,
                    "source_size_bytes": source_size,
                    "destination_size_bytes": destination_size,
                    "integrity_pass": integrity_pass,
                }
                status = "completed" if integrity_pass and receiver_result.get("integrity_pass") else "integrity_failed"
                return self._base_result(
                    config, experiment_id, repetition, seed, "actual", status, metrics, integrity,
                    configuration=config_for_run,
                )
        except Exception as exc:
            if sender is not None:
                sender.protocol.transport.close()
            if receiver_thread is not None and receiver_thread.is_alive():
                receiver_thread.join(max(0.0, deadline - time.monotonic()) + config.rto_ms / 1000 + 0.1)
            collector.finish_transfer(
                "failed",
                reconstructed_file_size_bytes=collector.total_useful_payload_bytes,
                source_sha256=source_hash,
                destination_sha256=None,
                integrity_pass=None,
            )
            return self._base_result(
                config, experiment_id, repetition, seed, "actual", "failed", collector.to_dict(),
                {"source_sha256": source_hash, "destination_sha256": None, "integrity_pass": None},
                f"{type(exc).__name__}: {exc}",
            )

    def _run_synthetic(self, config: ExperimentConfig, experiment_id: str, repetition: int, seed: int) -> ExperimentResult:
        rng = random.Random(seed)
        duration = max(0.001, 1 + config.loss_rate * 10 + rng.random() * 0.01)
        useful_bytes = config.file_size_bytes
        metrics = {
            "transfer_id": str(uuid4()),
            "protocol": config.protocol,
            "transfer_duration_seconds": duration,
            "source_file_size_bytes": config.file_size_bytes,
            "reconstructed_file_size_bytes": None,
            "completion_status": "synthetic_demo",
            "data_packets_transmitted": None,
            "data_packets_received": None,
            "control_packets_transmitted": None,
            "control_packets_received": None,
            "ack_packets_transmitted": None,
            "ack_packets_received": None,
            "retransmissions": None,
            "duplicate_packets": None,
            "corrupted_packets": None,
            "timeouts": None,
            "total_useful_payload_bytes": useful_bytes,
            "total_transmitted_bytes": None,
            "throughput_bps": None,
            "goodput_bps": useful_bytes * 8 / duration,
            "packet_loss_rate": None,
            "rtt_stats_ms": {"count": 0, "min": None, "mean": None, "max": None},
            "rto_stats_ms": {"count": 0, "min": None, "mean": None, "max": None},
        }
        return self._base_result(
            config, experiment_id, repetition, seed, "synthetic", "demo_only", metrics,
            {"source_sha256": None, "destination_sha256": None, "integrity_pass": None},
        )

    def _run_one(self, config: ExperimentConfig, experiment_id: str, repetition: int, seed: int, mode: str) -> ExperimentResult:
        config.validate(mode=mode)
        if mode == "synthetic":
            return self._run_synthetic(config, experiment_id, repetition, seed)
        return self._run_actual(config, experiment_id, repetition, seed)

    def _result_dir(self, result: ExperimentResult) -> Path:
        return self.results_dir / result.result_source / result.experiment_id

    def _save_json(self, result: ExperimentResult) -> Path:
        directory = self._result_dir(result)
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{result.run_id}.json"
        with path.open("x", encoding="utf-8") as handle:
            json.dump(result.to_dict(), handle, indent=2, allow_nan=False)
        return path

    @classmethod
    def _csv_row(cls, result: ExperimentResult) -> dict[str, Any]:
        metrics = result.metrics
        rtt_stats = metrics.get("rtt_stats_ms") or {}
        rto_stats = metrics.get("rto_stats_ms") or {}
        row = {
            "schema_version": result.schema_version,
            "experiment_id": result.experiment_id,
            "run_id": result.run_id,
            "result_source": result.result_source,
            "protocol": result.protocol,
            "execution_status": result.execution_status,
            "execution_timestamp": result.execution_timestamp,
            "random_seed": result.random_seed,
            "repetition": result.repetition,
            "configuration_json": json.dumps(result.configuration, sort_keys=True),
            "error": result.error,
            "notes": result.notes,
        }
        for field_name in cls.CSV_FIELDS:
            if field_name in metrics:
                row[field_name] = metrics[field_name]
        row.update({
            "rtt_mean_ms": rtt_stats.get("mean"),
            "rto_mean_ms": rto_stats.get("mean"),
            "source_sha256": result.integrity.get("source_sha256"),
            "destination_sha256": result.integrity.get("destination_sha256"),
            "integrity_pass": result.integrity.get("integrity_pass"),
        })
        return row

    def export_csv(self, results: Iterable[ExperimentResult], csv_path: str | Path) -> Path:
        path = Path(csv_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("x", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=self.CSV_FIELDS, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(self._csv_row(item) for item in results)
        return path

    def run_suite(self, configs: Iterable[ExperimentConfig], *, mode: Optional[str] = None) -> list[ExperimentResult]:
        selected_mode = mode or self.mode
        if selected_mode not in {"actual", "synthetic"}:
            raise ValueError("mode must be 'actual' or 'synthetic'")
        configs = list(configs)
        if not configs:
            return []
        for config in configs:
            config.validate(mode=selected_mode)

        experiment_id = str(uuid4())
        results: list[ExperimentResult] = []
        for config in configs:
            for repetition in range(config.repetitions):
                seed = config.seed + repetition
                result = self._run_one(config, experiment_id, repetition, seed, selected_mode)
                self._save_json(result)
                results.append(result)
        source = selected_mode
        csv_path = self.results_dir / source / experiment_id / f"{experiment_id}.csv"
        self.export_csv(results, csv_path)
        return results

    def run_single(self, config: ExperimentConfig, *, mode: Optional[str] = None) -> ExperimentResult:
        return self.run_suite([config], mode=mode)[0]