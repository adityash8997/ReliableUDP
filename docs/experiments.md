# Experiments, Results, and Performance Evaluation

## Project overview and architecture

ReliableUDP transfers files using a custom packet format over UDP. The application sender and receiver wrap the file-transfer service and the selected reliability protocol. Stop-and-Wait currently implements START metadata, sequenced DATA packets, ACK/retransmission handling, FIN, and SHA-256 integrity checking. Packet checksums detect datagram corruption; the file-level SHA-256 confirms the reconstructed content.

The current execution/data path is:

1. `SenderApplication` / `ReceiverApplication` configure the selected protocol.
2. The file-transfer layer computes source metadata and verifies received content.
3. The reliability protocol sends and accepts START, DATA, FIN and ACK packets.
4. `Packet` serializes and checksums protocol datagrams; UDP wrappers send/receive them.
5. `MetricsCollector` receives per-transfer packet and timing events from the protocol.
6. `ExperimentRunner` prepares a source, runs sender and receiver, checks integrity, and records one result per repetition.
7. JSON stores a nested run record; CSV stores a flat analysis row with nested configuration JSON.
8. `scripts/analyze_results.py` validates result source and execution status, groups valid actual runs, and assigns experiment-family statuses. `scripts/plot_results.py` plots only families with at least two distinct actual parameter settings for a protocol.

The deterministic channel emulator is tested as a separate component; it is **not wired into the live UDP path**. Actual experiments reject nonzero impairment settings.

## Experiment methodology

Each configuration records the protocol, payload size, window size, configured RTO, channel parameters, seed, file size or input path, repetition count, and execution deadline. For generated test files, the seed deterministically generates source bytes. Repetition $i$ uses seed `base_seed + i` and has its own run ID. Protocol timing is measured with a monotonic clock, but results can vary with OS scheduling and host load.

For a scientifically meaningful sweep, vary one independent variable at a time and hold the other configuration fields fixed. Retain every run; do not aggregate away the raw repetitions. The current CLI supports a configuration JSON object/list or direct command-line options. The checked-in `experiments/configs/default.json` contains legacy multi-protocol and impairment configurations and is **not an actual-mode-ready configuration**.

### Actual versus synthetic provenance

- `result_source: actual` means a real protocol transfer ran and was recorded. Current actual execution is clean-channel Stop-and-Wait only.
- `result_source: synthetic` and `execution_status: demo_only` identify generated demonstration data. It is not protocol evidence.
- Results without schema version 1 and an explicit recognized source are `legacy_unverified`. They are excluded from actual analysis. Existing legacy results and PNGs are preserved and are not moved into the actual-results tree.

The runner never falls back from an actual execution failure to synthetic values. Unsupported actual protocols and channel impairments are rejected before execution.

## Metric definitions and units

Metrics are defined by `src/reliable_udp/metrics.py` and recorded by Stop-and-Wait. Values named in bytes count bytes; packet and event fields are counts; rates ending `_bps` are bits per second; RTT and RTO fields ending `_ms` are milliseconds.

| Metric | Definition / unit |
|---|---|
| Transfer duration | Monotonic completion time minus monotonic start time, seconds. Start is recorded immediately before the START datagram is sent. |
| Total transmitted bytes | Sum of serialized protocol-datagram lengths sent by **both endpoints** during the measured transfer, bytes. Includes retransmitted datagrams, DATA, ACK, and control packets; excludes IP/UDP headers. |
| Throughput | `total_transmitted_bytes * 8 / transfer_duration_seconds`, bits/s. It reflects all protocol datagrams sent in both directions. |
| Useful payload bytes | Unique DATA payload bytes accepted and written by the receiver, counted once, bytes. Retransmissions and duplicate DATA do not increase this count. |
| Goodput | `total_useful_payload_bytes * 8 / transfer_duration_seconds`, bits/s. |
| DATA / ACK / control packets | Separate transmit and receive packet counts. The sender's retransmitted DATA attempts add transmitted DATA packets; duplicate receiver packets are counted separately and excluded from accepted DATA count. |
| Retransmissions | Number of retry events after the first packet attempt; count. |
| Duplicate packets | Packets received with a sequence number already accepted; count. |
| Corrupted packets | Count of corruption events observed by the active protocol instrumentation. No channel corruption observations are available while the emulator is disconnected. |
| Packet loss rate | `null` unless a valid channel observation method supplies it. Do not infer it as `(sent - received) / sent`; ACKs, controls and retransmissions make that invalid. |
| RTT | ACK arrival minus first-send monotonic time for a packet that was not retransmitted, milliseconds. Retransmitted-packet RTT is omitted because the ACK cannot be attributed unambiguously. |
| RTO | Configured timeout is recorded in milliseconds when a timeout occurs. `rto_stats_ms` summarizes those timeout-associated values; it is distinct from the configured RTO in `configuration.protocol.rto_ms`. No timeout means no measured RTO samples. |
| Integrity | SHA-256 source and destination digests plus size comparison; `integrity_pass` is true, false, or null if unavailable. |

Zero-duration transfers return a null rate rather than dividing by zero. A completed empty-file transfer has zero useful payload and, if duration is positive, zero goodput.

## Running actual experiments

Commands below use the `scripts/run_experiment.py` argument names. A verified actual invocation used these settings (Python 3.14.2 on Windows):

```powershell
$env:PYTHONPATH='src'
python scripts/run_experiment.py --mode actual --output-dir experiments/results --file-size-bytes 256 --payload-size-bytes 128 --seed 20261105 --repetitions 1 --rto-ms 100 --max-execution-seconds 10
```

To use an existing source file, pass `--file path/to/source.bin` instead of `--file-size-bytes`. The `--protocol` option currently accepts the three names, but only `stop-and-wait` can run actual experiments. Stop-and-Wait requires `--window-size 1`. The runner accepts `--loss-rate`, `--duplication-rate`, `--corruption-rate`, `--reordering-rate`, `--delay-ms`, and `--jitter-ms` for configuration parsing, but actual mode rejects any nonzero value because those impairments are not applied by the live path.

Output is stored under a unique `experiments/results/actual/<experiment-id>/` directory. Each repetition is a separate `<run-id>.json`; the suite has one `<experiment-id>.csv`. Existing output paths are not overwritten.

## Synthetic demonstration mode

Synthetic generation is explicitly opt-in. The verified demonstration form is:

```powershell
python scripts/run_experiment.py --mode synthetic --output-dir "$env:TEMP\reliableudp-synthetic-demo" --protocol go-back-n --window-size 4 --file-size-bytes 1024 --seed 42 --repetitions 2
```

Synthetic records are saved under `experiments/results/synthetic/<experiment-id>/`, with `result_source: synthetic` and `execution_status: demo_only`. They are generated to exercise the result pipeline and **must not be interpreted as measured protocol performance**. Actual analysis excludes them by default.

The legacy synthetic sweep additionally requires `--demo-sweep`; it can generate values for protocols not implemented as actual transfers. It must not be used as evidence that those protocols ran.

## JSON and CSV formats

Schema version 1 JSON stores one run per object with:

- `experiment_id`, `run_id`, `result_source`, `protocol`, `execution_status`, timestamp, seed and repetition.
- Nested `configuration.protocol`, `configuration.channel`, `configuration.file`, and `configuration.run` objects.
- `environment` metadata, `metrics`, `integrity`, `error`, and `notes`.

CSV contains one row per run. `configuration_json` is an escaped JSON object; absent measurements serialize as blank cells. Common flat columns include `result_source`, `execution_status`, `transfer_duration_seconds`, packet counters, `total_useful_payload_bytes`, `total_transmitted_bytes`, `throughput_bps`, `goodput_bps`, `packet_loss_rate`, RTT/RTO means, hashes and integrity status. Empty cells mean unavailable, not zero.

A shortened extract from a verified actual record illustrates the nested JSON shape (values are from a real run; omitted fields are not omitted from stored output):

```json
{
	"schema_version": 1,
	"experiment_id": "33a58d72-e334-49ac-8a28-1f1b05bdffd6",
	"run_id": "adc6636e-92b8-467d-a98a-44655208a772",
	"result_source": "actual",
	"protocol": "stop-and-wait",
	"execution_status": "completed",
	"random_seed": 20261105,
	"configuration": {
		"protocol": {"name": "stop-and-wait", "window_size": 1, "payload_size_bytes": 128, "rto_ms": 100.0},
		"channel": {"loss_rate": 0.0, "duplication_rate": 0.0, "corruption_rate": 0.0, "reordering_rate": 0.0, "delay_ms": 0.0, "jitter_ms": 0.0, "seed": 20261105},
		"file": {"file_size_bytes": 256, "test_file": null},
		"run": {"repetition": 0, "repetitions": 1, "seed": 20261105, "max_execution_seconds": 10.0}
	},
	"metrics": {
		"transfer_duration_seconds": 0.0021631,
		"data_packets_transmitted": 2,
		"ack_packets_transmitted": 4,
		"total_useful_payload_bytes": 256,
		"goodput_bps": 946789.3301448823,
		"integrity_pass": true
	},
	"integrity": {"integrity_pass": true},
	"error": null
}
```

The matching CSV row uses the same IDs and flat metrics; its full schema includes `configuration_json`, the packet-category counters, and SHA-256 columns. CSV quoting doubles embedded quotation marks in that JSON field according to standard CSV escaping.

The checked-in root `summary.csv`, 31 flat JSON records, and `tests/tmp_results` examples are legacy schema without provenance and run IDs. They remain preserved and are classified `legacy_unverified`; they are not merged into actual aggregates.

## Performance evaluation and current results

Run the analysis and graph pipeline with:

```powershell
python scripts/analyze_results.py --results-dir experiments/results --output-dir experiments/analysis
python scripts/plot_results.py --results-dir experiments/results --output-dir experiments/analysis
```

Each invocation creates a unique analysis folder with `analysis.json`, `manifest.json`, and status reports. Aggregates preserve raw values and report run count, mean, median, minimum, maximum, and sample standard deviation; standard deviation is null for fewer than two observations. Graphs are emitted only when a protocol has at least two distinct valid actual parameter settings with other controls fixed. Points show means, `n` labels give valid run count, and standard-deviation bars appear only when at least two runs support them. The plotting code uses unconnected point markers to avoid implying measurements at missing parameter values.

| Experiment family | Current status | Objective and interpretation |
|---|---|---|
| Goodput vs packet-loss rate | **BLOCKED** | Requires actual loss-applied runs and the three implemented protocols for the requested comparison. Current live path rejects nonzero loss; only a clean Stop-and-Wait point exists. |
| Goodput vs window size | **INSUFFICIENT DATA** | Requires multiple actual window settings within a supported protocol. Current evidence has two Stop-and-Wait repetitions at window 1; GBN/SR are unavailable. |
| Retransmissions vs reordering probability | **BLOCKED** | Requires proof that reordering was applied on the live path. Configuration alone is not evidence; emulator is disconnected. |
| RTO sensitivity | **INSUFFICIENT DATA** | Requires multiple configured RTO values, with measured transfer outcomes. Current actual data contains one configured value. Configured RTO is distinct from timeout-derived RTO samples. |

With the current result inventory, two successful runs share one clean Stop-and-Wait setting. This provides a small descriptive repeatability sample but **no parameter trend or statistically meaningful protocol comparison**. No performance curve is scientifically supported, so the plotting pipeline produces a status report/manifest and no fabricated graph files. The generated [graph status report](../experiments/analysis/b5472fa4-2089-467a-b623-8d0e72610e13/graphs-ea632ddf-5049-4238-a158-3f0e72610e13/graph_status.md) documents the four unavailable families. The existing PNGs in `experiments/plots/` are legacy/demo artifacts and must not be cited as actual graphs.

## Current limitations

- Stop-and-Wait is the only implemented actual file-transfer protocol.
- Go-Back-N and Selective Repeat remain stubs; actual evaluation rejects them.
- The channel emulator does not participate in live UDP transfers; impaired actual experiments are blocked.
- No valid packet-loss rate is measured by the live path.
- Two actual clean-channel runs are available at the same configuration. Their variation is descriptive only; no parameter trend or statistical confidence can be claimed.
- RTO is configured and enforced as a socket timeout. Timeout-derived samples exist only when timeouts occur; there is no adaptive RTO estimator in the current path.
- Legacy result provenance cannot be established from their schema; they remain unverified and excluded.

## Reproducibility and timing

The generated source contents are deterministic for a given seed and file size; each repetition increments the seed. Configuration and software/platform metadata are stored per run. Transfer duration and RTT may vary because of operating-system scheduling, loopback behavior and machine load. Thus reproducibility applies to inputs and generated payload, not bit-identical wall-clock timings.

## Testing and verification

The final-sprint analysis and plot tests should be run with:

```powershell
python -m pytest -q
```

The final-sprint terminal checkout ran `python -m pytest -q` and reported **23 passed**. That terminal checkout exposed five test modules; the editor VFS lists additional pre-existing test modules, so the 23-pass result is not claimed as execution of test files absent from that checkout. Re-run in the submission checkout and report its observed output.