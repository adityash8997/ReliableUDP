# AI Usage Log

This file records how AI assistance was used during development and how the work was reviewed.

| Date | Tool | Purpose | Files / Area | AI Contribution | Student Review |
|---|---|---|---|---|---|
| 2026-08-26 | GitHub Copilot | Project assessment and Part 1 planning | repository overview | assessed repo state and recommended architecture boundaries | yes |
| 2026-08-26 | GitHub Copilot | Project scaffold generation | README, pyproject, docs, package structure | generated Python project skeleton and documentation structure | yes |
| 2026-08-26 | GitHub Copilot | Packet-layer design | packet and checksum modules | generated wire-format definitions, validation logic, and checksum helpers | yes |
| 2026-08-26 | GitHub Copilot | UDP and emulator support code | UDP transport and channel emulator | generated deterministic emulator and socket wrappers | yes |
| 2026-08-26 | GitHub Copilot | Test scaffolding | unit tests | generated tests for serialization, validation, and deterministic impairment behavior | yes |

## Important academic note

AI assistance was used to generate supporting infrastructure, tests, and documentation. The core ARQ protocol algorithms (Stop-and-Wait, Go-Back-N, Selective Repeat, adaptive RTO, Jacobson/Karels, and Karn's algorithm) are intentionally not implemented here and remain designated as student-owned core networking work.
