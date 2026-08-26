from __future__ import annotations

import struct


def calculate_checksum(data: bytes) -> int:
    """Compute a simple 16-bit Internet-style checksum over raw bytes.

    This is intentionally simple and explicit so that students can explain the
    logic during the viva. It is suitable for detecting corruption in packet
    headers and payload bytes.
    """
    if not data:
        return 0

    if len(data) % 2:
        data += b"\x00"

    checksum = 0
    for i in range(0, len(data), 2):
        word = (data[i] << 8) | data[i + 1]
        checksum += word
        checksum = (checksum & 0xFFFF) + (checksum >> 16)

    checksum = (~checksum) & 0xFFFF
    return checksum


def verify_checksum(data: bytes, expected_checksum: int) -> bool:
    """Return True if the checksum matches the data payload."""
    return calculate_checksum(data) == expected_checksum


def checksum_packet_bytes(payload: bytes) -> bytes:
    """Return the 2-byte checksum field for the packet payload."""
    return struct.pack("!H", calculate_checksum(payload))
