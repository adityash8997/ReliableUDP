from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class MetricsCollector:
    """Simple structured metrics collector for transfer experiments.

    This is intentionally foundational: later phases will extend it with more
    detailed protocol-specific counters. The purpose here is to provide a stable
    metrics interface for logging and experiment output.
    """

    total_bytes_sent: int = 0
    total_bytes_received: int = 0
    packets_sent: int = 0
    packets_received: int = 0
    retransmissions: int = 0
    ack_sent: int = 0
    ack_received: int = 0
    duplicate_packets: int = 0
    corrupted_packets: int = 0
    dropped_packets: int = 0
    timeouts: int = 0
    transfer_started_at: Optional[float] = None
    transfer_ended_at: Optional[float] = None
    metadata: Dict[str, object] = field(default_factory=dict)
    rtt_samples: List[float] = field(default_factory=list)
    estimated_rto_ms: List[float] = field(default_factory=list)

    def start_transfer(self) -> None:
        self.transfer_started_at = time.monotonic()

    def end_transfer(self) -> None:
        self.transfer_ended_at = time.monotonic()

    @property
    def transfer_duration_seconds(self) -> float:
        if self.transfer_started_at is None:
            return 0.0
        if self.transfer_ended_at is None:
            return time.monotonic() - self.transfer_started_at
        return self.transfer_ended_at - self.transfer_started_at

    def to_dict(self) -> Dict[str, object]:
        return {
            "total_bytes_sent": self.total_bytes_sent,
            "total_bytes_received": self.total_bytes_received,
            "packets_sent": self.packets_sent,
            "packets_received": self.packets_received,
            "retransmissions": self.retransmissions,
            "ack_sent": self.ack_sent,
            "ack_received": self.ack_received,
            "duplicate_packets": self.duplicate_packets,
            "corrupted_packets": self.corrupted_packets,
            "dropped_packets": self.dropped_packets,
            "timeouts": self.timeouts,
            "transfer_duration_seconds": self.transfer_duration_seconds,
            "rtt_samples": list(self.rtt_samples),
            "estimated_rto_ms": list(self.estimated_rto_ms),
            "metadata": dict(self.metadata),
        }
