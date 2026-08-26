import unittest

from reliable_udp.packet import Packet, PacketType, PacketValidationError
from reliable_udp.checksum import calculate_checksum


class TestPacket(unittest.TestCase):
    def test_packet_serialization_round_trip(self):
        packet = Packet(
            version=1,
            type=PacketType.DATA,
            seq_num=7,
            ack_num=3,
            window=4,
            payload=b"hello world",
        )
        raw = packet.serialize()
        restored = Packet.deserialize(raw)

        self.assertEqual(restored.type, PacketType.DATA)
        self.assertEqual(restored.seq_num, 7)
        self.assertEqual(restored.ack_num, 3)
        self.assertEqual(restored.window, 4)
        self.assertEqual(restored.payload, b"hello world")

    def test_checksum_detects_corruption(self):
        packet = Packet(
            version=1,
            type=PacketType.ACK,
            seq_num=1,
            ack_num=2,
            payload=b"abc",
        )
        raw = packet.serialize()
        corrupted = bytearray(raw)
        corrupted[-1] ^= 0xFF
        with self.assertRaises(PacketValidationError):
            Packet.deserialize(bytes(corrupted))

    def test_malformed_packet_rejected(self):
        with self.assertRaises(PacketValidationError):
            Packet.deserialize(b"\x00\x00")

    def test_unknown_packet_type_rejected(self):
        packet = Packet(type=PacketType.DATA, payload=b"data")
        raw = packet.serialize()
        mutated = bytearray(raw)
        mutated[1] = 0x99
        with self.assertRaises(PacketValidationError):
            Packet.deserialize(bytes(mutated))

    def test_checksum_function(self):
        payload = b"networking"
        self.assertIsInstance(calculate_checksum(payload), int)
        self.assertNotEqual(calculate_checksum(payload), 0)


if __name__ == "__main__":
    unittest.main()
