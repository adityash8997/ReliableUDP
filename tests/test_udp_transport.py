import socket
import threading
import time
import unittest

from reliable_udp.packet import Packet, PacketType
from reliable_udp.udp_transport import UDPReceiver, UDPSender, UDPTransportConfig


class TestUDPTransport(unittest.TestCase):
    def test_sender_receiver_basic_exchange(self):
        receiver_cfg = UDPTransportConfig(host="127.0.0.1", port=9911, timeout_seconds=1.0)
        sender_cfg = UDPTransportConfig(host="127.0.0.1", port=9911, timeout_seconds=1.0)

        receiver = UDPReceiver(receiver_cfg)
        sender = UDPSender(sender_cfg)

        packet = Packet(type=PacketType.DATA, seq_num=10, ack_num=0, payload=b"payload")

        def receive_thread():
            received_packet, _ = receiver.receive_packet(timeout_seconds=1.0)
            self.assertEqual(received_packet.payload, b"payload")

        thread = threading.Thread(target=receive_thread)
        thread.start()
        time.sleep(0.1)
        sender.send_packet(packet)
        thread.join(timeout=5)

        sender.close()
        receiver.close()


if __name__ == "__main__":
    unittest.main()
