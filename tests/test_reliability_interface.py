import unittest

from reliable_udp.config import ProtocolConfig
from reliable_udp.reliability import build_protocol


class TestReliabilityInterface(unittest.TestCase):
    def test_protocol_selection(self):
        for name in ["stop-and-wait", "go-back-n", "selective-repeat"]:
            protocol = build_protocol(name, ProtocolConfig(protocol=name, window_size=4))
            self.assertIn("protocol", protocol.get_metrics())

    def test_invalid_protocol_rejected(self):
        with self.assertRaises(ValueError):
            build_protocol("not-a-protocol", ProtocolConfig(protocol="stop-and-wait"))


if __name__ == "__main__":
    unittest.main()
