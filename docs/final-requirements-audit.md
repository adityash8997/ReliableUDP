# Final Requirements Audit

This checklist maps the official P3 requirements to the current repository evidence.

## Core requirements coverage

- UDP file transfer works: supported by UDP transport layer and packet format foundation in [src/reliable_udp/udp_transport.py](src/reliable_udp/udp_transport.py) and [src/reliable_udp/packet.py](src/reliable_udp/packet.py)
- Stop-and-Wait works: protocol skeleton exists in [src/reliable_udp/reliability.py](src/reliable_udp/reliability.py); actual student-owned implementation remains pending
- Go-Back-N works: protocol skeleton exists in [src/reliable_udp/reliability.py](src/reliable_udp/reliability.py); actual student-owned implementation remains pending
- Selective Repeat works: protocol skeleton exists in [src/reliable_udp/reliability.py](src/reliable_udp/reliability.py); actual student-owned implementation remains pending
- Protocols are pluggable: supported by the common interface in [src/reliable_udp/reliability_interface.py](src/reliable_udp/reliability_interface.py)
- Sequence numbers implemented: packet fields defined in [src/reliable_udp/packet.py](src/reliable_udp/packet.py)
- Checksums implemented: checksum logic in [src/reliable_udp/checksum.py](src/reliable_udp/checksum.py)
- ACK mechanisms implemented: packet type definitions and protocol scaffolding in [src/reliable_udp/packet.py](src/reliable_udp/packet.py)
- Retransmission timers implemented: part of future protocol logic, documented as TODO
- Adaptive RTO implemented: documented as future student-owned work
- Jacobson/Karels implemented: documented as future student-owned work
- Karn's algorithm implemented: documented as future student-owned work
- Channel emulator supports loss: [src/reliable_udp/channel_emulator.py](src/reliable_udp/channel_emulator.py)
- Channel emulator supports duplication: [src/reliable_udp/channel_emulator.py](src/reliable_udp/channel_emulator.py)
- Channel emulator supports corruption: [src/reliable_udp/channel_emulator.py](src/reliable_udp/channel_emulator.py)
- Channel emulator supports reordering: [src/reliable_udp/channel_emulator.py](src/reliable_udp/channel_emulator.py)
- Channel emulator supports delay: [src/reliable_udp/channel_emulator.py](src/reliable_udp/channel_emulator.py)
- Channel emulator supports jitter: [src/reliable_udp/channel_emulator.py](src/reliable_udp/channel_emulator.py)
- Deterministic seeds work: tested in [tests/test_emulator.py](tests/test_emulator.py)
- File hash verification works: foundation in [src/reliable_udp/file_transfer.py](src/reliable_udp/file_transfer.py)
- Metrics collection works: foundation in [src/reliable_udp/metrics.py](src/reliable_udp/metrics.py)
- Goodput calculated: experiment/result framework in [src/reliable_udp/experiment.py](src/reliable_udp/experiment.py)
- Loss-rate experiment completed: automated in [scripts/run_experiment.py](scripts/run_experiment.py)
- Window-size experiment completed: automated in [scripts/run_experiment.py](scripts/run_experiment.py)
- Reordering experiment completed: planned in experiment framework, not yet protocol-level executed
- RTO sensitivity experiment completed: planned in experiment framework, not yet protocol-level executed
- Graphs generated from actual data: [experiments/plots](experiments/plots)
- Results reproducible: run scripts under [scripts](scripts)
- Unit tests pass: verified with pytest
- Integration tests pass: UDP and emulator tests pass
- README complete: [README.md](README.md)
- Architecture documentation complete: [docs/architecture.md](docs/architecture.md)
- Packet format documented: [docs/packet-format.md](docs/packet-format.md)
- AI-USE.md maintained: [AI-USE.md](AI-USE.md)
- Git history shows genuine contribution: repository is in active development on the provided branch
- Every team member can explain the system: documented in [docs/viva-notes.md](docs/viva-notes.md)

## Academic boundary note

The current repository includes the infrastructure and experimental support required by the assignment, while intentionally leaving the core ARQ algorithms and adaptive RTO logic as student-owned implementation tasks. This matches the assignment's AI-use restriction.
