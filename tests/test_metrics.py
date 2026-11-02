import unittest

from reliable_udp.metrics import MetricsCollector
from reliable_udp.packet import PacketType


class TestMetricsCollector(unittest.TestCase):
    def test_packet_categories_and_retransmission_events_are_separate(self):
        collector = MetricsCollector()
        collector.record_packet_sent(PacketType.DATA, 100)
        collector.record_packet_sent(PacketType.ACK, 18)
        collector.record_packet_sent(PacketType.START, 40)
        collector.record_packet_received(PacketType.DATA)
        collector.record_packet_received(PacketType.DATA, duplicate=True)
        collector.record_packet_received(PacketType.ACK)
        collector.record_retransmission()

        metrics = collector.to_dict()
        self.assertEqual(metrics["data_packets_transmitted"], 1)
        self.assertEqual(metrics["data_packets_received"], 1)
        self.assertEqual(metrics["ack_packets_transmitted"], 1)
        self.assertEqual(metrics["ack_packets_received"], 1)
        self.assertEqual(metrics["control_packets_transmitted"], 1)
        self.assertEqual(metrics["duplicate_packets"], 1)
        self.assertEqual(metrics["retransmissions"], 1)
        self.assertEqual(metrics["total_transmitted_bytes"], 158)

    def test_goodput_counts_useful_bytes_once_and_throughput_uses_wire_bytes(self):
        collector = MetricsCollector()
        collector.start_transfer("stop-and-wait", 100)
        collector.record_packet_sent(PacketType.DATA, 118)
        collector.record_packet_sent(PacketType.DATA, 118)
        collector.record_packet_sent(PacketType.ACK, 18)
        collector.record_useful_payload(100)
        collector.finish_transfer("completed", reconstructed_file_size_bytes=100)

        metrics = collector.to_dict()
        duration = metrics["transfer_duration_seconds"]
        self.assertGreater(duration, 0)
        self.assertAlmostEqual(metrics["throughput_bps"], 254 * 8 / duration)
        self.assertAlmostEqual(metrics["goodput_bps"], 100 * 8 / duration)
        self.assertEqual(metrics["total_useful_payload_bytes"], 100)

    def test_empty_file_and_unavailable_loss_are_not_divided_or_fabricated(self):
        collector = MetricsCollector()
        collector.start_transfer("stop-and-wait", 0)
        collector.finish_transfer("completed", reconstructed_file_size_bytes=0)

        metrics = collector.to_dict()
        self.assertEqual(metrics["goodput_bps"], 0)
        self.assertEqual(metrics["throughput_bps"], 0)
        self.assertIsNone(metrics["packet_loss_rate"])
        self.assertEqual(metrics["rtt_stats_ms"]["mean"], None)
        self.assertEqual(metrics["rto_stats_ms"]["mean"], None)

    def test_rtt_rto_timeout_and_integrity_fields_use_documented_units(self):
        collector = MetricsCollector()
        collector.start_transfer("stop-and-wait", 4)
        collector.record_rtt(0.012)
        collector.record_timeout(300.0)
        collector.finish_transfer(
            "completed",
            reconstructed_file_size_bytes=4,
            source_sha256="source",
            destination_sha256="destination",
            integrity_pass=False,
        )

        metrics = collector.to_dict()
        self.assertAlmostEqual(metrics["rtt_stats_ms"]["mean"], 12.0)
        self.assertEqual(metrics["rto_stats_ms"]["mean"], 300.0)
        self.assertEqual(metrics["timeouts"], 1)
        self.assertFalse(metrics["integrity_pass"])


if __name__ == "__main__":
    unittest.main()