
from __future__ import annotations

import hashlib
import json
import socket
import time
from pathlib import Path
from typing import Any, Dict

from .config import ProtocolConfig
from .metrics import MetricsCollector
from .reliability_interface import ReliabilityProtocol
from .packet import Packet, PacketType
from .udp_transport import (
    UDPSender,
    UDPReceiver,
    UDPTransportConfig,
)


class StopAndWaitProtocol(ReliabilityProtocol):

    def __init__(self, config: ProtocolConfig, metrics_collector: MetricsCollector | None = None):
        self.config = config
        self.metrics_collector = metrics_collector or MetricsCollector()
        self.host = "127.0.0.1"
        self.port = 9000

        self.expected_seq = 0
        self.send_seq = 0

        self.transport = UDPSender(
            UDPTransportConfig(
                timeout_seconds=config.rto_ms / 1000
            )
        )

    @property
    def metrics(self) -> Dict[str, Any]:
        """Backward-compatible summary derived from the shared collector."""
        values = self.metrics_collector.to_dict()
        return {
            "protocol": "stop-and-wait",
            "packets_sent": (
                values["data_packets_transmitted"]
                + values["control_packets_transmitted"]
                + values["ack_packets_transmitted"]
            ),
            "packets_received": (
                values["data_packets_received"]
                + values["control_packets_received"]
                + values["ack_packets_received"]
            ),
            "ack_sent": values["ack_packets_transmitted"],
            "ack_received": values["ack_packets_received"],
            "retransmissions": values["retransmissions"],
            "timeouts": values["timeouts"],
            "duplicate_packets": values["duplicate_packets"],
        }

    # ---------------- SENDER ----------------

    def send_packet(self, packet: Any) -> None:
        wire_bytes = len(packet.serialize())
        self.transport.send_packet(
            packet,
            host=self.host,
            port=self.port,
        )
        self.metrics_collector.record_packet_sent(packet.type, wire_bytes)

    def _send_and_wait(self, packet: Packet, deadline_monotonic: float | None = None) -> None:
        for attempt in range(self.config.max_retransmissions + 1):

            if deadline_monotonic is not None and time.monotonic() >= deadline_monotonic:
                raise TimeoutError("Transfer execution deadline exceeded")

            if attempt > 0:
                self.metrics_collector.record_retransmission()

            sent_at = time.monotonic()
            self.send_packet(packet)

            try:
                while True:
                    if deadline_monotonic is not None:
                        remaining = deadline_monotonic - time.monotonic()
                        if remaining <= 0:
                            raise TimeoutError("Transfer execution deadline exceeded")
                        self.transport.socket.settimeout(min(self.config.rto_ms / 1000, remaining))
                    response, _ = self.transport.receive_packet()
                    self.metrics_collector.record_packet_received(response.type)

                    if response.type == PacketType.ERROR:
                        raise RuntimeError(
                            response.payload.decode(errors="replace")
                        )

                    if (
                        response.type == PacketType.ACK
                        and response.ack_num == packet.seq_num
                    ):
                        if attempt == 0:
                            self.metrics_collector.record_rtt(time.monotonic() - sent_at)
                        self.send_seq = packet.seq_num + 1
                        return

            except socket.timeout:
                self.metrics_collector.record_timeout(self.config.rto_ms)

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

        deadline_monotonic = kwargs.get("deadline_monotonic")

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

        self.metrics_collector.start_transfer("stop-and-wait", metadata["size"])
        self.send_seq = 0

        start = Packet(
            type=PacketType.START,
            seq_num=0,
            payload=json.dumps(metadata).encode(),
        )

        self._send_and_wait(start, deadline_monotonic)

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

                self._send_and_wait(data_packet, deadline_monotonic)
                sequence += 1

        finish = Packet(
            type=PacketType.FIN,
            seq_num=sequence,
        )

        self._send_and_wait(finish, deadline_monotonic)

        self.transport.close()
        self.metrics_collector.finish_transfer("completed", reconstructed_file_size_bytes=metadata["size"], source_sha256=metadata["sha256"], destination_sha256=metadata["sha256"], integrity_pass=True)

        return {
            "protocol": "stop-and-wait",
            "filename": source.name,
            "file_size": metadata["size"],
            "sha256": metadata["sha256"],
            "integrity_expected": metadata["sha256"],
            "status": "transfer_complete",
            "metrics": self.get_metrics(),
            "transfer_metrics": self.metrics_collector.to_dict(),
        }

    # ---------------- RECEIVER ----------------

    def receive_file(
        self,
        filename: str,
        destination: str | None = None,
        **kwargs: Any
    ) -> Dict[str, Any]:

        overwrite = bool(kwargs.get("overwrite", False))
        metrics_collector = kwargs.get("metrics_collector", self.metrics_collector)
        receive_timeout_seconds = kwargs.get("receive_timeout_seconds")
        overall_timeout_seconds = kwargs.get("overall_timeout_seconds")
        ready_callback = kwargs.get("ready_callback")
        receiver_deadline = time.monotonic() + overall_timeout_seconds if overall_timeout_seconds else None
        target = Path(destination if destination else filename)
        if target.exists() and not overwrite:
            raise FileExistsError(f"Destination file already exists: {target}. Pass overwrite=True to replace it.")

        target.parent.mkdir(parents=True, exist_ok=True)

        receiver = UDPReceiver(
            UDPTransportConfig(
                host=self.host,
                port=self.port,
                timeout_seconds=self.config.rto_ms / 1000,
            )
        )
        if ready_callback is not None:
            ready_callback(receiver.socket.getsockname()[1])

        expected = 0
        sender_address = None
        metadata = None
        output_file = None
        received_hash = hashlib.sha256()
        received_size = 0

        try:
            while True:
                try:
                    socket_timeout = receive_timeout_seconds or self.config.rto_ms / 1000
                    if receiver_deadline is not None:
                        remaining = receiver_deadline - time.monotonic()
                        if remaining <= 0:
                            raise TimeoutError("Receiver execution deadline exceeded")
                        socket_timeout = min(socket_timeout, remaining)
                    packet, address = receiver.receive_packet(timeout_seconds=socket_timeout)

                except socket.timeout:
                    if receiver_deadline is not None and time.monotonic() >= receiver_deadline:
                        raise TimeoutError("Receiver execution deadline exceeded")
                    continue

                self.metrics_collector.record_packet_received(packet.type)

                if packet.type == PacketType.START:

                    if packet.seq_num == expected:
                        metadata = json.loads(
                            packet.payload.decode()
                        )

                        if target.exists() and not overwrite:
                            raise FileExistsError(f"Destination file already exists: {target}. Pass overwrite=True to replace it.")

                        output_file = target.open("wb")
                        sender_address = address
                        expected += 1

                    elif packet.seq_num < expected:
                        self.metrics_collector.record_packet_received(packet.type, duplicate=True)

                    else:
                        continue

                    ack = Packet(
                        type=PacketType.ACK,
                        ack_num=packet.seq_num,
                    )

                    receiver.send_packet(ack, address)
                    self.metrics_collector.record_packet_sent(ack.type, len(ack.serialize()))
                    continue

                if sender_address != address or metadata is None:
                    continue

                if packet.seq_num < expected:
                    self.metrics_collector.record_packet_received(packet.type, duplicate=True)

                    ack = Packet(
                        type=PacketType.ACK,
                        ack_num=packet.seq_num,
                    )

                    receiver.send_packet(ack, address)
                    self.metrics_collector.record_packet_sent(ack.type, len(ack.serialize()))
                    continue

                if packet.seq_num != expected:
                    continue

                if packet.type == PacketType.DATA:

                    output_file.write(packet.payload)
                    received_hash.update(packet.payload)
                    received_size += len(packet.payload)
                    self.metrics_collector.record_useful_payload(len(packet.payload))

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
                    self.metrics_collector.record_packet_sent(ack.type, len(ack.serialize()))

                    if not integrity:
                        self.metrics_collector.finish_transfer(
                            "integrity_failed",
                            reconstructed_file_size_bytes=received_size,
                            source_sha256=metadata.get("sha256"),
                            destination_sha256=received_hash.hexdigest(),
                            integrity_pass=False,
                        )
                        raise IOError("File integrity verification failed")

                    self.metrics_collector.finish_transfer(
                        "completed",
                        reconstructed_file_size_bytes=received_size,
                        source_sha256=metadata.get("sha256"),
                        destination_sha256=received_hash.hexdigest(),
                        integrity_pass=True,
                    )

                    return {
                        "protocol": "stop-and-wait",
                        "received_file": str(target),
                        "received_size": received_size,
                        "expected_sha256": metadata["sha256"],
                        "received_sha256": received_hash.hexdigest(),
                        "integrity_pass": True,
                        "status": "verified",
                        "metrics": self.get_metrics(),
                        "transfer_metrics": self.metrics_collector.to_dict(),
                    }

                else:
                    continue

                ack = Packet(
                    type=PacketType.ACK,
                    ack_num=packet.seq_num,
                )

                receiver.send_packet(ack, address)
                self.metrics_collector.record_packet_sent(ack.type, len(ack.serialize()))

        finally:
            if output_file is not None:
                output_file.close()

            receiver.close()

    # ---------------- PROTOCOL HELPERS ----------------

    def handle_packet(self, packet: Any) -> None:
        if packet.seq_num == self.expected_seq:
            self.expected_seq += 1
            self.metrics_collector.record_packet_received(packet.type)
        else:
            self.metrics_collector.record_packet_received(packet.type, duplicate=True)

    def handle_ack(self, packet: Any) -> None:
        if packet.ack_num == self.send_seq:
            self.send_seq += 1
            self.metrics_collector.record_packet_received(PacketType.ACK)

    def handle_timeout(self) -> None:
        self.metrics_collector.record_timeout(self.config.rto_ms)
        self.metrics_collector.record_retransmission()

    def get_metrics(self) -> Dict[str, Any]:
        return self.metrics


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
