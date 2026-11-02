# Architecture

ReliableUDP separates application file operations from protocol state and UDP packet handling.

## Transfer path

1. `SenderApplication` and `ReceiverApplication` select and configure a reliability protocol.
2. `FileTransferService` adapts file paths to the protocol interface; file metadata and end-to-end SHA-256 support integrity checks.
3. `ReliabilityProtocol` defines the common file and packet operations. `StopAndWaitProtocol` implements actual clean-path transfer. Go-Back-N and Selective Repeat remain stubs.
4. `Packet` encodes START, DATA, ACK, FIN and ERROR packets and validates its checksum. UDP sender/receiver wrappers transmit those protocol datagrams.
5. `MetricsCollector` receives packet-category, retry, timing, useful-byte and integrity events for an individual transfer.

## Experiment and analysis path

`ExperimentRunner` validates the configuration, prepares or selects a source file, starts a receiver on an ephemeral localhost port, transfers through the application wrappers, waits within a deadline, verifies the destination hash and records one result per repetition. Results are marked `actual` or `synthetic`; the latter is explicit demo-only data and is kept in a separate directory.

The CSV/JSON result layer stores a nested run object and flat per-run CSV rows. `scripts/analyze_results.py` loads schema-v1 runs, classifies unknown old schemas as `legacy_unverified`, excludes synthetic/failed/incomplete runs from actual aggregates, and summarizes supported parameter groups. `scripts/plot_results.py` consumes those aggregates and draws only actual comparisons with at least two distinct settings.

## Channel model boundary

`ChannelEmulator` independently models loss, duplication, corruption, reordering and delay with deterministic seeds. It is not currently connected to the live UDP transport. Actual experiment mode therefore accepts only zero impairment parameters; a configured nonzero value is rejected rather than treated as applied.

## Measurement boundary

Stop-and-Wait increments metrics through the shared collector. Transmitted-byte totals include serialized protocol datagrams sent by both endpoints, including ACK/control traffic and retransmissions, but exclude IP/UDP headers. Useful payload counts only accepted DATA bytes once. Durations use monotonic clocks. See [experiments.md](experiments.md) for formulas, units and current evidence.