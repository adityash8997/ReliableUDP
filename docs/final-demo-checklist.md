# Final Demo Checklist

1. Explain why UDP needs application-level reliability for file transfer.
2. Walk through sender/receiver, file transfer, protocol interface, packet/checksum and UDP layers using [architecture.md](architecture.md).
3. Run a clean-channel Stop-and-Wait experiment using the verified command in [experiments.md](experiments.md).
4. Show the run ID, source label, configuration, packet-category counts, duration, throughput/goodput, and integrity digests in JSON/CSV.
5. Point out that actual mode used a real local transfer and matching SHA-256 values.
6. Run analysis and plotting. Explain why the current one-run dataset yields status reports rather than performance curves.
7. Explain that legacy flat results and PNGs have no schema provenance and are not actual measurements.
8. Demonstrate synthetic mode only if needed, and point out `result_source: synthetic` and `execution_status: demo_only`.
9. State clearly that GBN/SR and live channel impairments are unavailable. Do not demonstrate synthetic values as a protocol run.
10. Explain clean-channel limitations and which new experiments would be required to support the requested comparisons.
11. Use the metric definitions and limitations in [experiments.md](experiments.md) for viva questions.