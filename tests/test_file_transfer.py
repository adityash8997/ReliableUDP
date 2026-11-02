import hashlib
import tempfile
import threading
import unittest
from pathlib import Path

from reliable_udp.config import ProtocolConfig
from reliable_udp.file_transfer import FileTransferService, verify_file_integrity
from reliable_udp.reliability import StopAndWaitProtocol


class TestFileTransferIntegration(unittest.TestCase):
    def test_verify_file_integrity_matches_hashes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "source.bin"
            received = Path(tmpdir) / "received.bin"
            payload = b"\x00\x01\x02\x03" * 64
            source.write_bytes(payload)
            received.write_bytes(payload)

            result = verify_file_integrity(source, received)
            self.assertTrue(result["integrity_pass"])
            self.assertEqual(result["source_hash"], result["received_hash"])

    def test_verify_file_integrity_detects_modified_output(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "source.bin"
            received = Path(tmpdir) / "received.bin"
            payload = b"networking" * 20
            source.write_bytes(payload)
            received.write_bytes(payload + b"\x00")

            result = verify_file_integrity(source, received)
            self.assertFalse(result["integrity_pass"])

    def test_file_transfer_round_trip_preserves_bytes_and_hash(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            src_path = Path(tmpdir) / "source.bin"
            dst_path = Path(tmpdir) / "destination.bin"
            payload = (b"\x00\x01\x02\x03\x04\x05" * 300) + b"tail"
            src_path.write_bytes(payload)

            expected_hash = hashlib.sha256(payload).hexdigest()
            receiver_result = {}

            def receive_file():
                receiver = StopAndWaitProtocol(ProtocolConfig(protocol="stop-and-wait", window_size=1, rto_ms=300, packet_size=32))
                receiver.host = "127.0.0.1"
                receiver.port = 9009
                receiver_result.update(receiver.receive_file(str(dst_path), overwrite=True))

            receive_thread = threading.Thread(target=receive_file, daemon=True)
            receive_thread.start()

            sender = StopAndWaitProtocol(ProtocolConfig(protocol="stop-and-wait", window_size=1, rto_ms=300, packet_size=32))
            sender.host = "127.0.0.1"
            sender.port = 9009
            send_result = sender.send_file(str(src_path), str(dst_path))

            receive_thread.join(timeout=10)

            self.assertEqual(send_result["sha256"], expected_hash)
            self.assertTrue(dst_path.exists())
            self.assertEqual(dst_path.read_bytes(), payload)
            self.assertTrue(receiver_result["integrity_pass"])
            self.assertEqual(receiver_result["expected_sha256"], expected_hash)
            self.assertEqual(receiver_result["received_sha256"], expected_hash)

    def test_receive_file_refuses_to_overwrite_without_explicit_permission(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "source.bin"
            destination = Path(tmpdir) / "destination.bin"
            source.write_bytes(b"payload")
            destination.write_bytes(b"existing")

            protocol = StopAndWaitProtocol(ProtocolConfig(protocol="stop-and-wait", window_size=1, rto_ms=300, packet_size=32))
            service = FileTransferService(protocol)

            with self.assertRaises(FileExistsError):
                service.receive_file(source, destination)


if __name__ == "__main__":
    unittest.main()
