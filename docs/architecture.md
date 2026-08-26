# Architecture

This project follows a modular design to keep the application layer independent from the reliability protocol implementation.

## High-level structure

- Application layer: issues transfer requests and chooses a protocol
- File transfer layer: reads and writes file data
- Reliability interface: shared abstraction for supported protocols
- Packet layer: serialization, validation, and checksum logic
- UDP transport: sender and receiver socket wrappers
- Channel emulator: deterministic packet impairment model
- Metrics: counters and timing state for experiments

## Design principle

The core protocol algorithms are deliberately left as later student-owned implementations. This project supports the infrastructure required to host those algorithms cleanly and to test them reproducibly.

## Protocol boundary

The common reliability interface standardizes the operations that a protocol must support, but does not implement any ARQ logic itself. That logic remains intentionally specific to the later Stop-and-Wait, Go-Back-N, and Selective Repeat implementations.
