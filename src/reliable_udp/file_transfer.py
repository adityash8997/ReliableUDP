from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Dict, Optional


def compute_file_hash(path: str | Path, algorithm: str = "sha256") -> tuple[str, int]:
    """Return the file hash hex digest and file size in bytes."""
    file_path = Path(path)
    hasher = hashlib.new(algorithm)
    total_bytes = 0

    with file_path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            hasher.update(chunk)
            total_bytes += len(chunk)

    return hasher.hexdigest(), total_bytes


def verify_file_integrity(source_path: str | Path, received_path: str | Path) -> Dict[str, Any]:
    """Compare source and received files based on hash and size."""
    source_hash, source_size = compute_file_hash(source_path)
    received_hash, received_size = compute_file_hash(received_path)

    matches = source_hash == received_hash and source_size == received_size
    return {
        "source_size": source_size,
        "received_size": received_size,
        "source_hash": source_hash,
        "received_hash": received_hash,
        "integrity_pass": matches,
    }


class FileTransferService:
    """Application-facing service for file transfer operations.

    The actual ARQ logic remains student-owned in the protocol modules. This
    service only wires the protocol interface to the file system and integrity
    checks.
    """

    def __init__(self, protocol):
        self.protocol = protocol

    def send_file(self, source_path: str | Path, destination_path: str | Path) -> Dict[str, Any]:
        if self.protocol is None:
            raise ValueError("A protocol instance is required for transfer operations")
        return self.protocol.send_file(str(source_path), str(destination_path))

    def receive_file(self, source_path: str | Path, destination_path: str | Path) -> Dict[str, Any]:
        if self.protocol is None:
            raise ValueError("A protocol instance is required for transfer operations")
        return self.protocol.receive_file(str(source_path), str(destination_path))
