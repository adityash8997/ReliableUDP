
from __future__ import annotations

import argparse
from pathlib import Path

from .config import ProtocolConfig
from .metrics import MetricsCollector
from .reliability import build_protocol


class ReceiverApplication:
    """Application-facing receiver entry point."""

    def __init__(self, protocol_config, host="0.0.0.0", port=9000, metrics_collector: MetricsCollector | None = None):
        self.protocol = build_protocol(
            protocol_config.protocol,
            protocol_config
        )
        if metrics_collector is not None and hasattr(self.protocol, "metrics_collector"):
            self.protocol.metrics_collector = metrics_collector

        self.protocol.host = host
        self.protocol.port = port

    def receive_file(self, output_path: str, *, overwrite: bool = False, **kwargs) -> dict:
        destination = Path(output_path)
        if destination.exists() and not overwrite:
            raise FileExistsError(f"Destination file already exists: {destination}. Pass overwrite=True to replace it.")
        return self.protocol.receive_file(output_path, destination=str(output_path), overwrite=overwrite, **kwargs)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Receive a file using UDP reliability protocol"
    )

    parser.add_argument(
        "output_path",
        help="Path where the received file will be saved"
    )

    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=9000)

    parser.add_argument(
        "--protocol",
        default="stop-and-wait",
        choices=[
            "stop-and-wait",
            "go-back-n",
            "selective-repeat"
        ]
    )

    parser.add_argument("--window", type=int, default=1)

    args = parser.parse_args()

    protocol_config = ProtocolConfig(
        protocol=args.protocol,
        window_size=args.window,
        rto_ms=500.0,
    )

    app = ReceiverApplication(
        protocol_config,
        host=args.host,
        port=args.port,
    )

    result = app.receive_file(args.output_path)
    print(result)


if __name__ == "__main__":
    main()
