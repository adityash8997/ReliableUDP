from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from .config import ProtocolConfig
from .reliability_interface import ReliabilityProtocol


class StopAndWaitProtocol(ReliabilityProtocol):
    """Student-owned core implementation placeholder.

    This class is intentionally skeletal. The actual sequence-number, ACK,
    timeout, and retransmission logic must be implemented later by the student.
    """

    def __init__(self, config: ProtocolConfig):
        self.config = config
        self.metrics = {"protocol": "stop-and-wait"}

    def send_file(self, filename: str, destination: str, **kwargs: Any) -> Dict[str, Any]:
        raise NotImplementedError("Stop-and-Wait core logic is intentionally left for student implementation.")

    def receive_file(self, filename: str, **kwargs: Any) -> Dict[str, Any]:
        raise NotImplementedError("Stop-and-Wait core logic is intentionally left for student implementation.")

    def send_packet(self, packet: Any) -> None:
        raise NotImplementedError("Stop-and-Wait core logic is intentionally left for student implementation.")

    def handle_packet(self, packet: Any) -> None:
        raise NotImplementedError("Stop-and-Wait core logic is intentionally left for student implementation.")

    def handle_ack(self, packet: Any) -> None:
        raise NotImplementedError("Stop-and-Wait core logic is intentionally left for student implementation.")

    def handle_timeout(self) -> None:
        raise NotImplementedError("Stop-and-Wait core logic is intentionally left for student implementation.")

    def get_metrics(self) -> Dict[str, Any]:
        return dict(self.metrics)


class GoBackNProtocol(ReliabilityProtocol):
    """Student-owned core implementation placeholder."""

    def __init__(self, config: ProtocolConfig):
        self.config = config
        self.metrics = {"protocol": "go-back-n"}

    def send_file(self, filename: str, destination: str, **kwargs: Any) -> Dict[str, Any]:
        raise NotImplementedError("Go-Back-N core logic is intentionally left for student implementation.")

    def receive_file(self, filename: str, **kwargs: Any) -> Dict[str, Any]:
        raise NotImplementedError("Go-Back-N core logic is intentionally left for student implementation.")

    def send_packet(self, packet: Any) -> None:
        raise NotImplementedError("Go-Back-N core logic is intentionally left for student implementation.")

    def handle_packet(self, packet: Any) -> None:
        raise NotImplementedError("Go-Back-N core logic is intentionally left for student implementation.")

    def handle_ack(self, packet: Any) -> None:
        raise NotImplementedError("Go-Back-N core logic is intentionally left for student implementation.")

    def handle_timeout(self) -> None:
        raise NotImplementedError("Go-Back-N core logic is intentionally left for student implementation.")

    def get_metrics(self) -> Dict[str, Any]:
        return dict(self.metrics)


class SelectiveRepeatProtocol(ReliabilityProtocol):
    """Student-owned core implementation placeholder."""

    def __init__(self, config: ProtocolConfig):
        self.config = config
        self.metrics = {"protocol": "selective-repeat"}

    def send_file(self, filename: str, destination: str, **kwargs: Any) -> Dict[str, Any]:
        raise NotImplementedError("Selective Repeat core logic is intentionally left for student implementation.")

    def receive_file(self, filename: str, **kwargs: Any) -> Dict[str, Any]:
        raise NotImplementedError("Selective Repeat core logic is intentionally left for student implementation.")

    def send_packet(self, packet: Any) -> None:
        raise NotImplementedError("Selective Repeat core logic is intentionally left for student implementation.")

    def handle_packet(self, packet: Any) -> None:
        raise NotImplementedError("Selective Repeat core logic is intentionally left for student implementation.")

    def handle_ack(self, packet: Any) -> None:
        raise NotImplementedError("Selective Repeat core logic is intentionally left for student implementation.")

    def handle_timeout(self) -> None:
        raise NotImplementedError("Selective Repeat core logic is intentionally left for student implementation.")

    def get_metrics(self) -> Dict[str, Any]:
        return dict(self.metrics)


def build_protocol(protocol_name: str, config: ProtocolConfig) -> ReliabilityProtocol:
    """Return the selected ARQ protocol stub.

    This function intentionally selects a protocol shell rather than a full
    implementation. The actual protocol state machine is student-owned and must
    be written later.
    """
    normalized = protocol_name.lower().strip()
    if normalized == "stop-and-wait":
        return StopAndWaitProtocol(config)
    if normalized == "go-back-n":
        return GoBackNProtocol(config)
    if normalized == "selective-repeat":
        return SelectiveRepeatProtocol(config)
    raise ValueError(f"Unsupported protocol: {protocol_name}")
