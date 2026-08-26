from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ProtocolConfig:
    """Configuration for the selected reliability protocol.

    This is intentionally generic enough to support Stop-and-Wait,
    Go-Back-N, and Selective Repeat, while leaving the actual core
    algorithm as student-owned implementation work.
    """

    protocol: str = "stop-and-wait"
    window_size: int = 1
    max_retransmissions: int = 20
    rto_ms: float = 500.0
    min_rto_ms: float = 50.0
    max_rto_ms: float = 5000.0
    packet_size: int = 1024
    ack_timeout_ms: int = 250

    def validate(self) -> None:
        if self.protocol not in {"stop-and-wait", "go-back-n", "selective-repeat"}:
            raise ValueError(f"Unsupported protocol: {self.protocol}")
        if self.window_size <= 0:
            raise ValueError("window_size must be positive")
        if self.packet_size <= 0:
            raise ValueError("packet_size must be positive")
        if self.rto_ms <= 0:
            raise ValueError("rto_ms must be positive")


@dataclass
class ChannelConfig:
    """Deterministic network impairment configuration."""

    loss_probability: float = 0.0
    duplication_probability: float = 0.0
    corruption_probability: float = 0.0
    reordering_probability: float = 0.0
    base_delay_ms: float = 0.0
    jitter_ms: float = 0.0
    seed: Optional[int] = 42

    def validate(self) -> None:
        for name, value in {
            "loss_probability": self.loss_probability,
            "duplication_probability": self.duplication_probability,
            "corruption_probability": self.corruption_probability,
            "reordering_probability": self.reordering_probability,
        }.items():
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be in range [0, 1]")
        if self.base_delay_ms < 0:
            raise ValueError("base_delay_ms must not be negative")
        if self.jitter_ms < 0:
            raise ValueError("jitter_ms must not be negative")


@dataclass
class TransferConfig:
    """Top-level transfer configuration."""

    protocol: ProtocolConfig = field(default_factory=ProtocolConfig)
    channel: ChannelConfig = field(default_factory=ChannelConfig)
    host: str = "127.0.0.1"
    port: int = 9000
    file_path: str = ""
    output_path: Optional[str] = None

    def validate(self) -> None:
        self.protocol.validate()
        self.channel.validate()
        if not 0 <= self.port <= 65535:
            raise ValueError("port must be in range [0, 65535]")
