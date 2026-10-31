from __future__ import annotations

import socket
import time
from dataclasses import dataclass
from typing import Optional

from .packet import Packet


@dataclass
class UDPTransportConfig:
    host: str = "127.0.0.1"
    port: int = 9000
    timeout_seconds: float = 1.0
    buffer_size: int = 65535

    def validate(self) -> None:
        if not self.host:
            raise ValueError("host cannot be empty")
        if not 0 <= self.port <= 65535:
            raise ValueError("port must be in range [0, 65535]")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if self.buffer_size <= 0:
            raise ValueError("buffer_size must be positive")


class UDPSender:
    """Simple UDP sender wrapper.

    This is intentionally a thin abstraction to support later protocol-level
    logic without hard-wiring the transfer code to socket details.
    """

    def __init__(self, config: UDPTransportConfig):
        self.config = config
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.settimeout(self.config.timeout_seconds)

    def send_packet(self, packet: Packet, host: Optional[str] = None, port: Optional[int] = None) -> None:
        target_host = host or self.config.host
        target_port = port or self.config.port
        self.socket.sendto(packet.serialize(), (target_host, target_port))
    def receive_packet(self) -> tuple[Packet, tuple[str, int]]:
        raw_data, addr = self.socket.recvfrom(self.config.buffer_size)
        return Packet.deserialize(raw_data), addr
    def close(self) -> None:
        self.socket.close()


class UDPReceiver:
    """Simple UDP receiver wrapper."""

    def __init__(self, config: UDPTransportConfig):
        self.config = config
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind((self.config.host, self.config.port))
        self.socket.settimeout(self.config.timeout_seconds)
    def send_packet(self, packet: Packet, address: tuple[str, int]) -> None:
        self.socket.sendto(packet.serialize(), address)
    def receive_packet(self, timeout_seconds: Optional[float] = None) -> tuple[Packet, tuple[str, int]]:
        socket_timeout = timeout_seconds if timeout_seconds is not None else self.config.timeout_seconds
        self.socket.settimeout(socket_timeout)
        raw_data, addr = self.socket.recvfrom(self.config.buffer_size)
        packet = Packet.deserialize(raw_data)
        return packet, addr

    def close(self) -> None:
        self.socket.close()
