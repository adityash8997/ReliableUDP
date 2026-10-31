from __future__ import annotations

import argparse
from pathlib import Path

from .config import ChannelConfig, ProtocolConfig, TransferConfig
from .file_transfer import FileTransferService
from .reliability import build_protocol


class SenderApplication:
    """Application-facing sender entry point.

    This layer intentionally does not contain the retransmission logic. That is
    handled by the protocol-specific implementations that students complete.
    """

    def __init__(self, config: TransferConfig):
        self.config = config
        self.protocol = build_protocol(config.protocol.protocol, config.protocol)
        self.protocol.host = config.host
        self.protocol.port = config.port
        self.transfer = FileTransferService(self.protocol)

    def send_file(self, file_path: str, output_path: str | None = None) -> dict:
        output = output_path or self.config.output_path or str(Path(file_path).with_name(Path(file_path).name + ".received"))
        return self.transfer.send_file(file_path, output)


def main() -> None:
    parser = argparse.ArgumentParser(description="Send a file using the selected UDP reliability protocol")
    parser.add_argument("file_path", help="Path to the source file")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9000)
    parser.add_argument("--protocol", default="stop-and-wait", choices=["stop-and-wait", "go-back-n", "selective-repeat"])
    parser.add_argument("--window", type=int, default=1)
    parser.add_argument("--loss", type=float, default=0.0)
    parser.add_argument("--duplication", type=float, default=0.0)
    parser.add_argument("--corruption", type=float, default=0.0)
    parser.add_argument("--reordering", type=float, default=0.0)
    parser.add_argument("--delay-ms", type=float, default=0.0)
    parser.add_argument("--jitter-ms", type=float, default=0.0)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    protocol_cfg = ProtocolConfig(
        protocol=args.protocol,
        window_size=args.window,
        rto_ms=500.0,
    )
    channel_cfg = ChannelConfig(
        loss_probability=args.loss,
        duplication_probability=args.duplication,
        corruption_probability=args.corruption,
        reordering_probability=args.reordering,
        base_delay_ms=args.delay_ms,
        jitter_ms=args.jitter_ms,
        seed=args.seed,
    )
    transfer_cfg = TransferConfig(protocol=protocol_cfg, channel=channel_cfg, host=args.host, port=args.port)
    app = SenderApplication(transfer_cfg)
    result = app.send_file(args.file_path)
    print(result)


if __name__ == "__main__":
    main()
