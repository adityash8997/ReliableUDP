import unittest

from reliable_udp.channel_emulator import ChannelEmulator, ChannelEmulatorConfig
from reliable_udp.packet import Packet, PacketType


class TestChannelEmulator(unittest.TestCase):
    def test_loss(self):
        config = ChannelEmulatorConfig(loss_probability=1.0, seed=7)
        emulator = ChannelEmulator(config)
        packet = Packet(type=PacketType.DATA, seq_num=1, payload=b"abc")
        self.assertEqual(emulator.process(packet), [])

    def test_duplication(self):
        config = ChannelEmulatorConfig(duplication_probability=1.0, seed=5)
        emulator = ChannelEmulator(config)
        packet = Packet(type=PacketType.DATA, seq_num=2, payload=b"abc")
        processed = emulator.process(packet)
        self.assertEqual(len(processed), 2)

    def test_corruption(self):
        config = ChannelEmulatorConfig(corruption_probability=1.0, seed=11)
        emulator = ChannelEmulator(config)
        packet = Packet(type=PacketType.DATA, seq_num=3, payload=b"abc")
        processed = emulator.process(packet)
        self.assertNotEqual(processed[0].payload, b"abc")
        self.assertIsInstance(processed[0], Packet)

    def test_reordering(self):
        config = ChannelEmulatorConfig(reordering_probability=1.0, seed=13)
        emulator = ChannelEmulator(config)
        packets = [Packet(type=PacketType.DATA, seq_num=i, payload=b"x") for i in range(3)]
        reordered = emulator.deliver_in_order(packets)
        self.assertEqual([p.seq_num for p in reordered], [2, 1, 0])

    def test_seed_reproducibility(self):
        config_a = ChannelEmulatorConfig(loss_probability=0.5, duplication_probability=0.3, seed=42)
        config_b = ChannelEmulatorConfig(loss_probability=0.5, duplication_probability=0.3, seed=42)
        e1 = ChannelEmulator(config_a)
        e2 = ChannelEmulator(config_b)
        packet = Packet(type=PacketType.DATA, seq_num=10, payload=b"payload")
        out1 = [e1.process(packet) for _ in range(10)]
        out2 = [e2.process(packet) for _ in range(10)]
        self.assertEqual(out1, out2)


if __name__ == "__main__":
    unittest.main()
