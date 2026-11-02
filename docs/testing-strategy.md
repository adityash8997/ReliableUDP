# Testing Strategy

Run the project suite from the repository root:

```powershell
python -m pytest -q
```

Tests are organized around observable behavior:

- Packet serialization, checksum and malformed-input validation.
- UDP sender/receiver packet exchange.
- Standalone channel-emulator loss, duplication, corruption, reordering and deterministic seed behavior.
- Stop-and-Wait counters and state helpers.
- File transfer round-trip, SHA-256 integrity and overwrite protections.
- Metrics packet categorization, retransmission counting, throughput/goodput formulas, empty files, and missing observations.
- Experiment validation, real local Stop-and-Wait execution, repetitions, explicit synthetic provenance, failure/deadline handling, JSON/CSV schema and overwrite protection.
- Analysis provenance filtering, legacy/failed run exclusion, grouping and statistical summaries.
- Plot generation from supported actual settings and status-only output when actual evidence is insufficient.

The emulator tests establish its standalone behavior only. They do not prove that the live UDP transfer path applies those impairments; actual experiment mode rejects nonzero impairment configuration. GBN and SR do not have transfer tests that can pass as working protocols because their operations remain unimplemented.

Always report the exact output from the checkout being evaluated. Do not copy a test count from another workspace or infer that uncollected tests passed.