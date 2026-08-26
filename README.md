# Reliable UDP Transfer Project

This repository is the foundation for a Computer Networks assignment focused on reliable file transfer over UDP.

## Project objective

The goal is to implement a custom reliability layer above UDP, compare multiple ARQ protocols, and model the network with a deterministic channel emulator. The current milestone covers the required foundation and infrastructure before the protocol algorithms themselves are implemented.

## Language

Python 3 is the selected implementation language for this project.

## Part 1 scope

This repository currently contains the network foundation only:

- project scaffolding
- configuration dataclasses
- packet definition and checksum validation
- UDP socket wrappers
- channel emulator infrastructure
- metrics foundation
- tests for core infrastructure
- documentation

This scope intentionally does not include the final ARQ algorithm implementations. Those remain as student-owned TODOs for later phases.

## Repository layout

```text
.
├── README.md
├── AI-USE.md
├── .gitignore
├── pyproject.toml
├── docs/
│   ├── architecture.md
│   ├── packet-format.md
│   ├── protocol-notes.md
│   ├── experiments.md
│   ├── testing-strategy.md
│   └── viva-notes.md
├── src/
│   └── reliable_udp/
│       ├── __init__.py
│       ├── checksum.py
│       ├── config.py
│       ├── packet.py
│       ├── metrics.py
│       ├── udp_transport.py
│       ├── channel_emulator.py
│       └── reliability_interface.py
└── tests/
    ├── test_packet.py
    ├── test_udp_transport.py
    └── test_emulator.py
```

## Installation

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# or .venv\Scripts\activate  # Windows
python -m pip install --upgrade pip
python -m pip install -e .
```

## Running tests

```bash
pytest -q
```

## Current academic boundary

The following are intentionally not implemented in this part:

- Stop-and-Wait ARQ
- Go-Back-N ARQ
- Selective Repeat ARQ
- adaptive RTO
- Jacobson/Karels estimation
- Karn's algorithm
- complete retransmission logic

The code includes interface stubs and TODO markers for these features so the later student-owned implementation remains explicit and reviewable.

## AI usage disclosure

This project keeps a transparent AI-use log in [AI-USE.md](AI-USE.md). The assignment allows AI to explain concepts, review code, generate tests, and scaffold support code, but not to silently replace the student's own protocol implementation.
