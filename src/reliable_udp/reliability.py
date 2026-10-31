from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from .config import ProtocolConfig
from .reliability_interface import ReliabilityProtocol

from .packet import Packet
from .udp_transport import UDPSender, UDPTransportConfig

from .udp_transport import UDPReceiver
class StopAndWaitProtocol(ReliabilityProtocol):

    def __init__(self, config: ProtocolConfig):
        self.config = config
        self.expected_seq = 0
        self.send_seq = 0
        self.transport = UDPSender(
    UDPTransportConfig(
        host=getattr(self, "host", "127.0.0.1"),
        port=getattr(self, "port", 9000),
        timeout_seconds=self.config.rto_ms / 1000
    )
)
        self.metrics = {
            "protocol": "stop-and-wait",
            "packets_sent": 0,
            "packets_received": 0,
            "ack_sent": 0,
            "ack_received": 0,
            "retransmissions": 0,
            "timeouts": 0,
            "duplicate_packets": 0
        }

    def send_file(self, filename: str, destination: str, **kwargs: Any) -> Dict[str, Any]:
        raise NotImplementedError("Pending.")

    def receive_file(self, filename: str, **kwargs: Any) -> Dict[str, Any]:
        raise NotImplementedError("Pending.")
    def send_packet(self, packet: Any) -> None:
        self.transport.send_packet(
            packet,
            host=getattr(self, "host", "127.0.0.1"),
            port=getattr(self, "port", 9000)
        )
        self.metrics["packets_sent"] += 1

    def handle_packet(self, packet: Any) -> None:
        if packet.seq_num == self.expected_seq:
            self.expected_seq += 1
            self.metrics["packets_received"] += 1
            self.metrics["ack_sent"] += 1
        else:
            self.metrics["duplicate_packets"] += 1

    def handle_ack(self, packet: Any) -> None:
        if packet.ack_num == self.send_seq:
            self.send_seq += 1
            self.metrics["ack_received"] += 1

    def handle_timeout(self) -> None:
            self.metrics["timeouts"] += 1
            self.metrics["retransmissions"] += 1

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
