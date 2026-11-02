import unittest

from reliable_udp.config import ProtocolConfig
from reliable_udp.reliability import StopAndWaitProtocol
from reliable_udp.packet import Packet
from reliable_udp.packet import Packet, PacketType

class TestStopAndWait(unittest.TestCase):

    def setUp(self):
        config = ProtocolConfig(
            protocol="stop-and-wait",
            window_size=1,
            rto_ms=500
        )
        self.protocol = StopAndWaitProtocol(config)

    def test_initial_sequence_number(self):
        self.assertEqual(self.protocol.expected_seq, 0)

    def test_initial_metrics(self):
        metrics = self.protocol.get_metrics()
        self.assertEqual(metrics["protocol"], "stop-and-wait")

    def test_accepts_expected_packet(self):
        packet = Packet(seq_num=0)
        self.protocol.handle_packet(packet)

        self.assertEqual(self.protocol.expected_seq, 1)
        self.assertEqual(self.protocol.metrics["packets_received"], 1)

    def test_detects_duplicate_packet(self):
        packet = Packet(seq_num=0)
        self.protocol.handle_packet(packet)
        self.protocol.handle_packet(packet)

        self.assertEqual(self.protocol.expected_seq, 1)
        self.assertEqual(self.protocol.metrics["duplicate_packets"], 1)
    def test_accepts_correct_ack(self):
        packet = Packet(type=PacketType.ACK, ack_num=0)

        self.protocol.handle_ack(packet)

        self.assertEqual(self.protocol.send_seq, 1)
        self.assertEqual(self.protocol.metrics["ack_received"], 1)


    def test_ignores_wrong_ack(self):
        packet = Packet(type=PacketType.ACK, ack_num=5)

        self.protocol.handle_ack(packet)

        self.assertEqual(self.protocol.send_seq, 0)
        self.assertEqual(self.protocol.metrics["ack_received"], 0)
    def test_timeout_increments_metrics(self):
        self.protocol.handle_timeout()

        self.assertEqual(self.protocol.metrics["timeouts"], 1)
        self.assertEqual(self.protocol.metrics["retransmissions"], 1)
if __name__ == "__main__":
    unittest.main()