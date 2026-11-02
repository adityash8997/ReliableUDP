
from __future__ import annotations

import hashlib
import json
import socket
from pathlib import Path
from typing import Any, Dict

from .config import ProtocolConfig
from .reliability_interface import ReliabilityProtocol
from .packet import Packet, PacketType
from .udp_transport import (
    UDPSender,
    UDPReceiver,
    UDPTransportConfig,
)


class StopAndWaitProtocol(ReliabilityProtocol):

    def __init__(self, config: ProtocolConfig):
        self.config = config
        self.host = "127.0.0.1"
        self.port = 9000

        self.expected_seq = 0
        self.send_seq = 0

        self.transport = UDPSender(
            UDPTransportConfig(
                timeout_seconds=config.rto_ms / 1000
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
            "duplicate_packets": 0,
        }

    # ---------------- SENDER ----------------

    def send_packet(self, packet: Any) -> None:
        self.transport.send_packet(
            packet,
            host=self.host,
            port=self.port,
        )
        self.metrics["packets_sent"] += 1

    def _send_and_wait(self, packet: Packet) -> None:
        for attempt in range(self.config.max_retransmissions + 1):

            if attempt > 0:
                self.metrics["retransmissions"] += 1

            self.send_packet(packet)

            try:
                while True:
                    response, _ = self.transport.receive_packet()

                    if response.type == PacketType.ERROR:
                        raise RuntimeError(
                            response.payload.decode(errors="replace")
                        )

                    if (
                        response.type == PacketType.ACK
                        and response.ack_num == packet.seq_num
                    ):
                        self.metrics["ack_received"] += 1
                        self.send_seq = packet.seq_num + 1
                        return

            except socket.timeout:
                self.metrics["timeouts"] += 1

        raise TimeoutError(
            f"No ACK received for packet {packet.seq_num}"
        )

    def send_file(
        self,
        filename: str,
        destination: str,
        **kwargs: Any
    ) -> Dict[str, Any]:

        source = Path(filename)

        if not source.is_file():
            raise FileNotFoundError(filename)

        file_hash = hashlib.sha256()

        with source.open("rb") as file:
            while True:
                chunk = file.read(65536)
                if not chunk:
                    break
                file_hash.update(chunk)

        metadata = {
            "filename": source.name,
            "size": source.stat().st_size,
            "sha256": file_hash.hexdigest(),
        }

        self.send_seq = 0

        start = Packet(
            type=PacketType.START,
            seq_num=0,
            payload=json.dumps(metadata).encode(),
        )

        self._send_and_wait(start)

        sequence = 1

        with source.open("rb") as file:
            while True:
                chunk = file.read(self.config.packet_size)

                if not chunk:
                    break

                data_packet = Packet(
                    type=PacketType.DATA,
                    seq_num=sequence,
                    payload=chunk,
                )

                self._send_and_wait(data_packet)
                sequence += 1

        finish = Packet(
            type=PacketType.FIN,
            seq_num=sequence,
        )

        self._send_and_wait(finish)

        self.transport.close()

        return {
            "protocol": "stop-and-wait",
            "filename": source.name,
            "file_size": metadata["size"],
            "sha256": metadata["sha256"],
            "metrics": self.get_metrics(),
        }

    # ---------------- RECEIVER ----------------

    def receive_file(
        self,
        filename: str,
        destination: str | None = None,
        **kwargs: Any
    ) -> Dict[str, Any]:

        output = Path(destination if destination else filename)
        output.parent.mkdir(parents=True, exist_ok=True)

        receiver = UDPReceiver(
            UDPTransportConfig(
                host=self.host,
                port=self.port,
                timeout_seconds=self.config.rto_ms / 1000,
            )
        )

        expected = 0
        sender_address = None
        metadata = None
        output_file = None
        received_hash = hashlib.sha256()
        received_size = 0

        try:
            while True:
                try:
                    packet, address = receiver.receive_packet()

                except socket.timeout:
                    continue

                self.metrics["packets_received"] += 1

                if packet.type == PacketType.START:

                    if packet.seq_num == expected:
                        metadata = json.loads(
                            packet.payload.decode()
                        )

                        output_file = output.open("wb")
                        sender_address = address
                        expected += 1

                    elif packet.seq_num < expected:
                        self.metrics["duplicate_packets"] += 1

                    else:
                        continue

                    ack = Packet(
                        type=PacketType.ACK,
                        ack_num=packet.seq_num,
                    )

                    receiver.send_packet(ack, address)
                    self.metrics["ack_sent"] += 1
                    continue

                if sender_address != address or metadata is None:
                    continue

                if packet.seq_num < expected:
                    self.metrics["duplicate_packets"] += 1

                    ack = Packet(
                        type=PacketType.ACK,
                        ack_num=packet.seq_num,
                    )

                    receiver.send_packet(ack, address)
                    self.metrics["ack_sent"] += 1
                    continue

                if packet.seq_num != expected:
                    continue

                if packet.type == PacketType.DATA:

                    output_file.write(packet.payload)
                    received_hash.update(packet.payload)
                    received_size += len(packet.payload)

                    expected += 1

                elif packet.type == PacketType.FIN:

                    expected += 1
                    output_file.close()
                    output_file = None

                    integrity = (
                        received_hash.hexdigest()
                        == metadata["sha256"]
                        and received_size == metadata["size"]
                    )

                    ack = Packet(
                        type=PacketType.ACK,
                        ack_num=packet.seq_num,
                    )

                    receiver.send_packet(ack, address)
                    self.metrics["ack_sent"] += 1

                    if not integrity:
                        raise IOError("File integrity verification failed")

                    return {
                        "protocol": "stop-and-wait",
                        "received_file": str(output),
                        "received_size": received_size,
                        "received_hash": received_hash.hexdigest(),
                        "integrity_pass": True,
                        "metrics": self.get_metrics(),
                    }

                else:
                    continue

                ack = Packet(
                    type=PacketType.ACK,
                    ack_num=packet.seq_num,
                )

                receiver.send_packet(ack, address)
                self.metrics["ack_sent"] += 1

        finally:
            if output_file is not None:
                output_file.close()

            receiver.close()

    # ---------------- PROTOCOL HELPERS ----------------

    def handle_packet(self, packet: Any) -> None:
        if packet.seq_num == self.expected_seq:
            self.expected_seq += 1
            self.metrics["packets_received"] += 1
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
    """Go-Back-N implementation pending."""

    def __init__(self, config: ProtocolConfig):
        self.config = config
        self.metrics = {"protocol": "go-back-n"}

    def send_file(self, filename, destination, **kwargs):
        raise NotImplementedError("Go-Back-N pending.")

    def receive_file(self, filename, **kwargs):
        raise NotImplementedError("Go-Back-N pending.")

    def send_packet(self, packet):
        raise NotImplementedError("Go-Back-N pending.")

    def handle_packet(self, packet):
        raise NotImplementedError("Go-Back-N pending.")

    def handle_ack(self, packet):
        raise NotImplementedError("Go-Back-N pending.")

    def handle_timeout(self):
        raise NotImplementedError("Go-Back-N pending.")

    def get_metrics(self):
        return dict(self.metrics)


class SelectiveRepeatProtocol(ReliabilityProtocol):
    """Selective Repeat implementation owned by teammate."""

    def __init__(self, config: ProtocolConfig):
        self.config = config
        self.metrics = {"protocol": "selective-repeat"}

    def send_file(self, filename, destination, **kwargs):
        raise NotImplementedError("Selective Repeat pending.")

    def receive_file(self, filename, **kwargs):
        raise NotImplementedError("Selective Repeat pending.")

    def send_packet(self, packet):
        raise NotImplementedError("Selective Repeat pending.")

    def handle_packet(self, packet):
        raise NotImplementedError("Selective Repeat pending.")

    def handle_ack(self, packet):
        raise NotImplementedError("Selective Repeat pending.")

    def handle_timeout(self):
        raise NotImplementedError("Selective Repeat pending.")

    def get_metrics(self):
        return dict(self.metrics)


def build_protocol(
    protocol_name: str,
    config: ProtocolConfig
) -> ReliabilityProtocol:

    normalized = protocol_name.lower().strip()

    if normalized == "stop-and-wait":
        return StopAndWaitProtocol(config)

    if normalized == "go-back-n":
        return GoBackNProtocol(config)

    if normalized == "selective-repeat":
        return SelectiveRepeatProtocol(config)

    raise ValueError(f"Unsupported protocol: {protocol_name}")
