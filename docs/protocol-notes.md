# Protocol Notes

This project intentionally separates infrastructure from the actual reliability protocols.

## Student-owned core work

The following remain explicit TODOs for the later protocol implementation phases:

- Stop-and-Wait state machine and retransmission logic
- Go-Back-N sender window and cumulative ACK handling
- Selective Repeat buffers and per-packet ACK logic
- adaptive RTO logic
- Jacobson/Karels estimation
- Karn's algorithm

## Supported foundation

The infrastructure in this repository provides the following support code:

- packet definition
- checksum support
- deterministic channel model
- UDP wrappers
- metrics scaffold
- tests and documentation for the network foundation
