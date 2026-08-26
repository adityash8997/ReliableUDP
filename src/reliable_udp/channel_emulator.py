from __future__ import annotations

import random
import time
from dataclasses import dataclass
from typing import Iterable, List, Tuple

from .packet import Packet, PacketValidationError


@dataclass
class ChannelEmulatorConfig:
    """Deterministic network impairment configuration."""

    loss_probability: float = 0.0
    duplication_probability: float = 0.0
    corruption_probability: float = 0.0
    reordering_probability: float = 0.0
    base_delay_ms: float = 0.0
    jitter_ms: float = 0.0
    seed: int | None = 42

    def validate(self) -> None:
        if not 0.0 <= self.loss_probability <= 1.0:
            raise ValueError("loss_probability must be in [0, 1]")
        if not 0.0 <= self.duplication_probability <= 1.0:
            raise ValueError("duplication_probability must be in [0, 1]")
        if not 0.0 <= self.corruption_probability <= 1.0:
            raise ValueError("corruption_probability must be in [0, 1]")
        if not 0.0 <= self.reordering_probability <= 1.0:
            raise ValueError("reordering_probability must be in [0, 1]")
        if self.base_delay_ms < 0:
            raise ValueError("base_delay_ms must not be negative")
        if self.jitter_ms < 0:
            raise ValueError("jitter_ms must not be negative")


class ChannelEmulator:
    """Standalone emulator for packet impairments.

    The emulator is deliberately separated from the protocol implementation so
    it can be tested independently with deterministic random seeds.
    """

    def __init__(self, config: ChannelEmulatorConfig):
        self.config = config
        self.config.validate()
        self.random = random.Random(self.config.seed)

    def _apply_corruption(self, packet: Packet) -> Packet:
        if self.random.random() >= self.config.corruption_probability:
            return packet

        # Corrupt one byte in the payload, or if payload is empty, one byte in the
        # packet header. This maintains the semantics for checksum tests.
        if packet.payload:
            raw = bytearray(packet.payload)
            idx = self.random.randrange(len(raw))
            raw[idx] = (raw[idx] + 1) % 256
            packet.payload = bytes(raw)
        else:
            packet.seq_num = (packet.seq_num + 1) % (2**32)
        return packet

    def _apply_duplication(self, packet: Packet) -> List[Packet]:
        if self.random.random() >= self.config.duplication_probability:
            return [packet]
        return [packet, Packet(**packet.__dict__)]

    def _delay_for_packet(self) -> float:
        delay_ms = self.config.base_delay_ms
        if self.config.jitter_ms > 0:
            delay_ms += self.random.uniform(0, self.config.jitter_ms)
        return delay_ms / 1000.0

    def process(self, packet: Packet) -> List[Packet]:
        """Create the sequence of packets after applying configured impairments.

        The actual semantics intentionally keep a small amount of logic in one place
        so the emulator can be tested directly and explained during viva.
        """
        candidates: List[Packet] = [packet]

        # duplication must be considered before loss because duplicated packets are
        # normal network events, though either could occur in sequence.
        if self.random.random() < self.config.duplication_probability:
            candidates = [packet, Packet(**packet.__dict__)]

        if self.random.random() < self.config.loss_probability:
            return []

        processed: List[Packet] = []
        for current in candidates:
            if self.random.random() < self.config.corruption_probability:
                current = self._apply_corruption(current)
            processed.append(current)

        if self.random.random() < self.config.reordering_probability and len(processed) > 1:
            processed.reverse()

        for item in processed:
            time.sleep(self._delay_for_packet())

        return processed

    def deliver_in_order(self, packets: Iterable[Packet]) -> List[Packet]:
        """A simple helper for deterministic per-packet scheduling tests."""
        items = list(packets)
        if self.random.random() < self.config.reordering_probability and len(items) > 1:
            items.reverse()
        return items
