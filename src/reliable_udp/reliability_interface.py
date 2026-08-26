from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict


class ReliabilityProtocolError(RuntimeError):
    """Raised when a protocol-specific operation fails."""


class ReliabilityProtocol(ABC):
    """Common reliability protocol interface.

    This is intentionally a thin abstraction to allow switching among
    stop-and-wait, go-back-n, and selective-repeat without changing the
    application layer. The actual state-machine logic is left to the student
    in later phases.
    """

    @abstractmethod
    def send_file(self, filename: str, destination: str, **kwargs: Any) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def receive_file(self, filename: str, **kwargs: Any) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def send_packet(self, packet: Any) -> None:
        raise NotImplementedError

    @abstractmethod
    def handle_packet(self, packet: Any) -> None:
        raise NotImplementedError

    @abstractmethod
    def handle_ack(self, packet: Any) -> None:
        raise NotImplementedError

    @abstractmethod
    def handle_timeout(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_metrics(self) -> Dict[str, Any]:
        raise NotImplementedError
