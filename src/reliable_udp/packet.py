from __future__ import annotations

import struct
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from .checksum import calculate_checksum


class PacketType(Enum):
    DATA = 0x01
    ACK = 0x02
    START = 0x03
    FIN = 0x04
    ERROR = 0x05


class PacketValidationError(ValueError):
    """Raised when a packet is malformed or invalid."""


@dataclass
class Packet:
    """Custom wire-format packet for reliable UDP transport.

    Layout (deterministic network byte order):

    0   1   2   3   4   5   6   7   8   9  10  11 12 13 14 15
    +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
    | version | type | flags |  reserved (2 bytes) | seq num (4 bytes) |
    +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
    | ack num (4 bytes) | window (2 bytes) | payload_len (2 bytes) |
    +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
    | checksum (2 bytes) | payload ...                                 |
    +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+

    This layout is intentionally simple enough for every team member to explain
    during the viva. The actual protocol state machine remains student-owned.
    """

    version: int = 1
    type: PacketType = PacketType.DATA
    flags: int = 0
    seq_num: int = 0
    ack_num: int = 0
    window: int = 0
    payload: bytes = b""
    checksum: Optional[int] = None

    HEADER_STRUCT = struct.Struct("!BBBBIIHH")
    # format: version(1), type(1), flags(1), reserved(1), seq_num(4), ack_num(4), window(2), payload_len(2)
    # total header size is 16 bytes: 1+1+1+1+4+4+2+2 = 16

    @property
    def payload_len(self) -> int:
        return len(self.payload)

    @property
    def header_size(self) -> int:
        return self.HEADER_STRUCT.size

    def serialize(self) -> bytes:
        if not isinstance(self.type, PacketType):
            raise PacketValidationError("Packet type must be a PacketType enum")

        payload = self.payload if isinstance(self.payload, bytes) else bytes(self.payload)
        payload_length = len(payload)

        if payload_length > 65535:
            raise PacketValidationError("Payload length exceeds 65535 bytes")

        if self.version < 0 or self.version > 255:
            raise PacketValidationError("Version must fit in one byte")
        if self.flags < 0 or self.flags > 255:
            raise PacketValidationError("Flags must fit in one byte")
        if self.window < 0 or self.window > 65535:
            raise PacketValidationError("Window must fit in 16 bits")

        header = self.HEADER_STRUCT.pack(
            self.version,
            self.type.value,
            self.flags,
            0,
            self.seq_num,
            self.ack_num,
            self.window,
            payload_length,
        )

        # checksum is computed over the serialized header and payload values of
        # the packet, excluding the checksum field itself.
        checksum_input = header + payload
        checksum_value = calculate_checksum(checksum_input)
        full_packet = header + struct.pack("!H", checksum_value) + payload
        return full_packet

    @classmethod
    def deserialize(cls, raw: bytes) -> "Packet":
        if len(raw) < 18:
            raise PacketValidationError("Packet too short to contain a valid header")

        header = raw[:16]
        checksum_bytes = raw[16:18]
        payload = raw[18:]

        version, packet_type_id, flags, reserved, seq_num, ack_num, window, payload_length = struct.unpack(
            "!BBBBIIHH", header
        )

        if version != 1:
            raise PacketValidationError(f"Unsupported packet version: {version}")

        try:
            packet_type = PacketType(packet_type_id)
        except ValueError as exc:
            raise PacketValidationError(f"Unknown packet type: {packet_type_id}") from exc

        if payload_length != len(payload):
            raise PacketValidationError(
                f"Payload length mismatch: declared {payload_length}, actual {len(payload)}"
            )

        checksum_value = struct.unpack("!H", checksum_bytes)[0]
        combined = header + payload
        actual_checksum = calculate_checksum(combined)
        if actual_checksum != checksum_value:
            raise PacketValidationError("Checksum mismatch")

        return cls(
            version=version,
            type=packet_type,
            flags=flags,
            seq_num=seq_num,
            ack_num=ack_num,
            window=window,
            payload=payload,
            checksum=checksum_value,
        )

    def __len__(self) -> int:
        return self.header_size + 2 + len(self.payload)
