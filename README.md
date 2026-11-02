# ReliableUDP

ReliableUDP is a Python Computer Networks project for reliable file transfer over UDP. It defines a custom packet/checksum format, UDP socket wrappers, a protocol interface, Stop-and-Wait file transfer with ACK/retransmission handling, and SHA-256 end-to-end file integrity verification.

## Current implementation

- **Actual transfer:** Stop-and-Wait on a clean local UDP path.
- **Metrics and experiments:** transfer-scoped metrics, bounded actual experiment runs, reproducible generated source files, repetitions and run IDs.
- **Results:** source-labelled nested JSON and flat CSV under unique `actual/` or `synthetic/` directories.
- **Analysis and graphs:** provenance-aware actual-result analysis. Graphs are generated only when there are at least two distinct valid parameter settings per protocol.
- **Not currently available:** actual Go-Back-N/Selective Repeat execution, live channel-emulator impairments, and adaptive RTO. These limitations block several experiment families.

See [docs/architecture.md](docs/architecture.md) for the architecture and [docs/experiments.md](docs/experiments.md) for verified commands, metrics, schemas, analysis status, and reproducibility details.

## Run an actual clean-channel experiment

From the repository root:

```powershell
$env:PYTHONPATH='src'
python scripts/run_experiment.py --mode actual --output-dir experiments/results --file-size-bytes 256 --payload-size-bytes 128 --seed 20261105 --repetitions 1 --rto-ms 100 --max-execution-seconds 10
```

Actual mode defaults to Stop-and-Wait. It rejects nonzero impairment settings and unsupported protocols instead of substituting synthetic results. See the experiment guide for input-file and synthetic-demo invocations.

## Analyze results and generate supported graphs

```powershell
python scripts/analyze_results.py --results-dir experiments/results --output-dir experiments/analysis
python scripts/plot_results.py --results-dir experiments/results --output-dir experiments/analysis
```

The scripts create unique output directories. Two clean-channel actual runs currently share one configuration, which is not enough to establish a performance trend; the scripts report the missing evidence rather than fabricate graphs. Existing root-level results and plots use legacy schemas and are not assumed to be actual.

## Tests

```powershell
python -m pytest -q
```

Use the output from the current checkout when reporting test results. The project requires Python 3.10 or later; Matplotlib is declared as the plotting dependency.

## Layout

- `src/reliable_udp/`: transfer, protocol, packet, transport, metrics, and experiment code.
- `scripts/`: experiment runner, analysis, and plotting entry points.
- `tests/`: unit, integration, metrics, experiment, analysis, and plotting tests.
- `experiments/results/`: preserved legacy results and source-separated new runs.
- `experiments/analysis/`: unique analysis manifests, status reports, and any supported graphs.
- `docs/`: architecture, packet, protocol, testing, viva, and experiment documentation.

## Scope and academic boundary

Go-Back-N and Selective Repeat classes remain protocol stubs. The standalone channel emulator has deterministic impairment tests but is not connected to the live sender/receiver path. Do not present synthetic or legacy-unverified records as actual protocol measurements.

## AI usage disclosure

See [AI-USE.md](AI-USE.md) for the repository's AI-use log.