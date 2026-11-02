from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import RLock
from typing import Dict, List, Optional
from uuid import uuid4


@dataclass
class MetricsCollector:
    """Transfer metrics; byte counters are serialized protocol-datagram bytes unless named payload.

    Throughput is the bytes in serialized protocol datagrams sent by both
    endpoints, including ACK/control packets, times eight divided by elapsed
    seconds (excluding IP/UDP headers). Goodput is unique, accepted application
    payload bytes times eight divided by elapsed seconds.
    Packet loss is deliberately ``None``: the current transfer path has no
    trustworthy observation of all packets lost in the channel.
    """

    transfer_id: str = field(default_factory=lambda: str(uuid4()))
    protocol: Optional[str] = None
    source_file_size_bytes: Optional[int] = None
    reconstructed_file_size_bytes: Optional[int] = None
    completion_status: str = "not_started"
    start_time: Optional[str] = None
    completion_time: Optional[str] = None
    data_packets_transmitted: int = 0
    data_packets_received: int = 0
    control_packets_transmitted: int = 0
    control_packets_received: int = 0
    ack_packets_transmitted: int = 0
    ack_packets_received: int = 0
    retransmissions: int = 0
    duplicate_packets: int = 0
    corrupted_packets: int = 0
    timeouts: int = 0
    total_useful_payload_bytes: int = 0
    total_transmitted_bytes: int = 0
    packet_loss_rate: Optional[float] = None
    source_sha256: Optional[str] = None
    destination_sha256: Optional[str] = None
    integrity_pass: Optional[bool] = None
    metadata: Dict[str, object] = field(default_factory=dict)
    rtt_samples_ms: List[float] = field(default_factory=list)
    rto_samples_ms: List[float] = field(default_factory=list)
    _started_monotonic: Optional[float] = field(default=None, init=False, repr=False)
    _completed_monotonic: Optional[float] = field(default=None, init=False, repr=False)
    _lock: RLock = field(default_factory=RLock, init=False, repr=False)

    def start_transfer(self, protocol: str, source_file_size_bytes: int) -> None:
        with self._lock:
            if self._started_monotonic is not None:
                raise RuntimeError("Transfer metrics have already been started")
            self.protocol = protocol
            self.source_file_size_bytes = source_file_size_bytes
            self.completion_status = "in_progress"
            self.start_time = datetime.now(timezone.utc).isoformat()
            self._started_monotonic = time.monotonic()

    def finish_transfer(
        self,
        status: str,
        *,
        reconstructed_file_size_bytes: Optional[int] = None,
        source_sha256: Optional[str] = None,
        destination_sha256: Optional[str] = None,
        integrity_pass: Optional[bool] = None,
    ) -> None:
        with self._lock:
            self.completion_status = status
            self.reconstructed_file_size_bytes = reconstructed_file_size_bytes
            self.source_sha256 = source_sha256
            self.destination_sha256 = destination_sha256
            self.integrity_pass = integrity_pass
            self.completion_time = datetime.now(timezone.utc).isoformat()
            self._completed_monotonic = time.monotonic()

    @staticmethod
    def _packet_type_name(packet_type: object) -> str:
        return str(getattr(packet_type, "name", packet_type)).upper()

    def record_packet_sent(self, packet_type: object, wire_bytes: int) -> None:
        name = self._packet_type_name(packet_type)
        with self._lock:
            if name == "DATA":
                self.data_packets_transmitted += 1
            elif name == "ACK":
                self.ack_packets_transmitted += 1
            else:
                self.control_packets_transmitted += 1
            self.total_transmitted_bytes += wire_bytes

    def record_packet_received(self, packet_type: object, *, duplicate: bool = False) -> None:
        name = self._packet_type_name(packet_type)
        with self._lock:
            if duplicate:
                self.duplicate_packets += 1
                return
            if name == "DATA":
                self.data_packets_received += 1
            elif name == "ACK":
                self.ack_packets_received += 1
            else:
                self.control_packets_received += 1

    def record_retransmission(self) -> None:
        with self._lock:
            self.retransmissions += 1

    def record_rto(self, rto_ms: float) -> None:
        with self._lock:
            self.rto_samples_ms.append(rto_ms)

    def record_timeout(self, rto_ms: Optional[float] = None) -> None:
        with self._lock:
            self.timeouts += 1
            if rto_ms is not None:
                self.rto_samples_ms.append(rto_ms)

    def record_rtt(self, elapsed_seconds: float) -> None:
        with self._lock:
            self.rtt_samples_ms.append(elapsed_seconds * 1000.0)

    def record_corruption(self) -> None:
        with self._lock:
            self.corrupted_packets += 1

    def record_useful_payload(self, byte_count: int) -> None:
        with self._lock:
            self.total_useful_payload_bytes += byte_count

    @property
    def transfer_duration_seconds(self) -> float:
        if self._started_monotonic is None:
            return 0.0
        end = self._completed_monotonic if self._completed_monotonic is not None else time.monotonic()
        return max(0.0, end - self._started_monotonic)

    @staticmethod
    def _stats(values: List[float]) -> Dict[str, Optional[float]]:
        if not values:
            return {"count": 0, "min": None, "mean": None, "max": None}
        return {
            "count": len(values),
            "min": min(values),
            "mean": sum(values) / len(values),
            "max": max(values),
        }

    def to_dict(self) -> Dict[str, object]:
        duration = self.transfer_duration_seconds
        return {
            "transfer_id": self.transfer_id,
            "protocol": self.protocol,
            "start_time": self.start_time,
            "completion_time": self.completion_time,
            "transfer_duration_seconds": duration,
            "source_file_size_bytes": self.source_file_size_bytes,
            "reconstructed_file_size_bytes": self.reconstructed_file_size_bytes,
            "completion_status": self.completion_status,
            "data_packets_transmitted": self.data_packets_transmitted,
            "data_packets_received": self.data_packets_received,
            "control_packets_transmitted": self.control_packets_transmitted,
            "control_packets_received": self.control_packets_received,
            "ack_packets_transmitted": self.ack_packets_transmitted,
            "ack_packets_received": self.ack_packets_received,
            "retransmissions": self.retransmissions,
            "duplicate_packets": self.duplicate_packets,
            "corrupted_packets": self.corrupted_packets,
            "timeouts": self.timeouts,
            "total_useful_payload_bytes": self.total_useful_payload_bytes,
            "total_transmitted_bytes": self.total_transmitted_bytes,
            "throughput_bps": (self.total_transmitted_bytes * 8 / duration) if duration > 0 else None,
            "goodput_bps": (self.total_useful_payload_bytes * 8 / duration) if duration > 0 else None,
            "packet_loss_rate": self.packet_loss_rate,
            "rtt_samples_ms": list(self.rtt_samples_ms),
            "rtt_stats_ms": self._stats(self.rtt_samples_ms),
            "rto_samples_ms": list(self.rto_samples_ms),
            "rto_stats_ms": self._stats(self.rto_samples_ms),
            "source_sha256": self.source_sha256,
            "destination_sha256": self.destination_sha256,
            "integrity_pass": self.integrity_pass,
            "metadata": dict(self.metadata),
        }
