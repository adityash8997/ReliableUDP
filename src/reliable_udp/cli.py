from __future__ import annotations

import argparse

from .receiver import main as receive_main
from .sender import main as send_main


def main() -> None:
    parser = argparse.ArgumentParser(description="Reliable UDP transfer CLI")
    parser.add_argument("mode", choices=["sender", "receiver"])
    parser.add_argument("path", nargs="?")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9000)
    parser.add_argument("--protocol", default="stop-and-wait", choices=["stop-and-wait", "go-back-n", "selective-repeat"])
    parser.add_argument("--window", type=int, default=1)
    args = parser.parse_args()

    if args.mode == "sender":
        if args.path is None:
            parser.error("sender requires a file path")
        # The application entry point intentionally delegates to the protocol-layer
        # implementation as a thin wrapper. The protocol algorithm itself remains
        # student-owned in later phases.
        raise SystemExit("Sender execution is prepared but the actual core protocol logic is intentionally left as student-owned work.")

    if args.mode == "receiver":
        raise SystemExit("Receiver execution is prepared but the actual core protocol logic is intentionally left as student-owned work.")


if __name__ == "__main__":
    main()
