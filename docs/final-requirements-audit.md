# Final Requirements Audit

This status reflects the current code and checked-in evidence, not intended future behavior.

| Requirement | Status | Evidence / limitation |
|---|---|---|
| Packet serialization and checksum validation | Implemented | `src/reliable_udp/packet.py`, `src/reliable_udp/checksum.py`, and packet tests. |
| UDP transport wrappers | Implemented | `src/reliable_udp/udp_transport.py`; transport tests cover packet exchange. |
| Stop-and-Wait transfer and ACK/retry path | Implemented | `src/reliable_udp/reliability.py`; live actual run is clean-channel localhost only. |
| Go-Back-N transfer | Not implemented | Protocol methods remain stubs; no actual experiment evidence. |
| Selective Repeat transfer | Not implemented | Protocol methods remain stubs; no actual experiment evidence. |
| SHA-256 integrity verification | Implemented | File metadata and received digest comparison; integration tests and actual run verify matching hashes. |
| Transfer-scoped metrics | Implemented, limited observations | Shared collector records packet classes, retransmissions, useful bytes, duration, RTT samples and integrity. Packet loss remains unavailable unless observed through a future live impairment integration. |
| Actual experiment runner | Implemented for clean Stop-and-Wait | Bounded local transfer, repetitions, unique IDs, actual source label and failure status; unsupported protocols/impairments reject. |
| Synthetic demonstration mode | Explicitly available | `result_source: synthetic`, `execution_status: demo_only`, separate source folder; excluded from actual analysis. |
| JSON/CSV result collection | Implemented | Versioned JSON and per-run CSV, unique output names, no silent overwrite. |
| Goodput vs loss-rate evaluation | Blocked | No actual nonzero loss runs; GBN/SR unavailable. Legacy records are unverified, not actual. |
| Goodput vs window-size evaluation | Insufficient data | Two actual Stop-and-Wait runs share window 1; no supported window sweep. |
| Retransmissions vs reordering evaluation | Blocked | The channel emulator is not on the live UDP path; no actual reordering evidence. |
| RTO sensitivity evaluation | Insufficient data | Only one configured RTO value in current actual evidence; no sensitivity curve. |
| Actual-data performance graphs | No graph currently justified | Two repeats at one clean configuration cannot support parameter trends. Existing PNGs are legacy/demo and are not represented as actual graphs. |
| Analysis and provenance validation | Implemented | Reusable script excludes synthetic, failed/incomplete, and legacy-unverified records from actual aggregates and reports family status. |
| Regression tests | Current command result required | Report only the output of the final-sprint test command in the active checkout. |

The legacy flat result files and old plots are preserved. Missing provenance is not repaired by assumption. For architecture, commands, formulas, schema, analysis statuses and limitations, see [experiments.md](experiments.md).