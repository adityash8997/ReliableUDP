from __future__ import annotations

import argparse

from .config import ChannelConfig, ProtocolConfig, TransferConfig
from .file_transfer import FileTransferService
from .reliability import build_protocol


class ReceiverApplication:
    """Application-facing receiver entry point."""

    def __init__(self, config: TransferConfig):
        self.config = config
        self.protocol = build_protocol(config.protocol.protocol, config.protocol)
        self.transfer = FileTransferService(self.protocol)

    def receive_file(self, output_path: str) -> dict:
        return self.transfer.receive_file(self.config.file_path, output_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Receive a file over UDP using the selected reliability protocol")
    parser.add_argument("--port", type=int, default=9000)
    parser.add_argument("--protocol", default="stop-and-wait", choices=["stop-and-wait", "go-back-n", "selective-repeat"])
    parser.add_argument("--output", default="received.bin")
    args = parser.parse_args()

    protocol_cfg = ProtocolConfig(protocol=args.protocol, window_size=1, rto_ms=500.0)
    transfer_cfg = TransferConfig(protocol=protocol_cfg, channel=ChannelConfig(), port=args.port, output_path=args.output)
    app = ReceiverApplication(transfer_cfg)
    result = app.receive_file(args.output)
    print(result)


if __name__ == "__main__":
    main()
