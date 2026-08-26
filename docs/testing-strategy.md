# Testing Strategy

## Unit tests

Part 1 focuses on verifying the infrastructure that all future protocol implementations depend on.

- packet serialization and deserialization
- checksum correctness and corruption detection
- malformed packet rejection
- UDP sender/receiver basic exchange
- emulator loss, duplication, corruption, reorder, delay, and jitter behavior
- deterministic seed reproducibility

## Why this matters

Protocol correctness depends on a stable and verifiable network foundation. The emulator must be deterministic and testable independently of the reliability logic.
