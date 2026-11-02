from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional
from uuid import uuid4


def _read_json_record(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        return {"_source_file": str(path), "_provenance": "legacy_unverified", "_parse_error": "JSON root is not an object"}
    value["_source_file"] = str(path)
    if value.get("schema_version") == 1 and value.get("result_source") in {"actual", "synthetic"}:
        value["_provenance"] = value["result_source"]
    else:
        value["_provenance"] = "legacy_unverified"
    return value


def _read_csv_records(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        row["_source_file"] = str(path)
        if row.get("schema_version") == "1" and row.get("result_source") in {"actual", "synthetic"}:
            row["_provenance"] = row["result_source"]
        else:
            row["_provenance"] = "legacy_unverified"
    return rows


def load_records(results_dirs: str | Path | Iterable[str | Path]) -> list[dict[str, Any]]:
    """Load JSON runs and CSV-only legacy data without upgrading provenance."""
    if isinstance(results_dirs, (str, Path)):
        roots = [Path(results_dirs)]
    else:
        roots = [Path(item) for item in results_dirs]
    if not roots:
        raise ValueError("At least one results directory must be provided")
    for root in roots:
        if not root.exists():
            raise FileNotFoundError(f"Results directory does not exist: {root}")
    json_by_absolute_path: dict[Path, Path] = {}
    for root in roots:
        for path in root.rglob("*.json"):
            json_by_absolute_path.setdefault(path.absolute(), path)
    json_paths = sorted(json_by_absolute_path.values(), key=lambda path: str(path))
    records: list[dict[str, Any]] = []
    for path in json_paths:
        try:
            records.append(_read_json_record(path))
        except (OSError, json.JSONDecodeError) as exc:
            records.append({"_source_file": str(path), "_provenance": "legacy_unverified", "_parse_error": f"{type(exc).__name__}: {exc}"})

    # Current run CSVs duplicate each run's JSON. Only ingest CSV records with no
    # JSON run records in that experiment directory, which preserves CSV-only legacy sources.
    json_parents = {path.parent.absolute() for path in json_paths}
    csv_by_absolute_path: dict[Path, Path] = {}
    for root in roots:
        for path in root.rglob("*.csv"):
            csv_by_absolute_path.setdefault(path.absolute(), path)
    csv_paths = sorted(csv_by_absolute_path.values(), key=lambda path: str(path))
    for path in csv_paths:
        if path.parent.absolute() in json_parents:
            continue
        try:
            records.extend(_read_csv_records(path))
        except (OSError, csv.Error) as exc:
            records.append({"_source_file": str(path), "_provenance": "legacy_unverified", "_parse_error": f"{type(exc).__name__}: {exc}"})
    return records


def _configuration(record: dict[str, Any]) -> dict[str, Any]:
    value = record.get("configuration")
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            return {}
    return value if isinstance(value, dict) else {}


def _metric(record: dict[str, Any], name: str) -> Any:
    metrics = record.get("metrics")
    if isinstance(metrics, dict) and name in metrics:
        return metrics.get(name)
    return record.get(name)


def _provenance(record: dict[str, Any]) -> str:
    value = record.get("_provenance")
    if value in {"actual", "synthetic", "legacy_unverified"}:
        return value
    if record.get("schema_version") == 1 and record.get("result_source") in {"actual", "synthetic"}:
        return record["result_source"]
    return "legacy_unverified"


def _parameter(record: dict[str, Any], family: str) -> Optional[float]:
    config = _configuration(record)
    protocol_config = config.get("protocol")
    channel_config = config.get("channel")
    protocol_config = protocol_config if isinstance(protocol_config, dict) else {}
    channel_config = channel_config if isinstance(channel_config, dict) else {}
    if family == "loss_rate":
        value = channel_config.get("loss_rate", record.get("loss_rate"))
    elif family == "window_size":
        value = protocol_config.get("window_size", config.get("window_size", record.get("window_size")))
    elif family == "reordering_rate":
        value = channel_config.get("reordering_rate", record.get("reordering_rate"))
    elif family == "rto_ms":
        value = protocol_config.get("rto_ms", config.get("rto_ms", record.get("rto_ms")))
    else:
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def _protocol(record: dict[str, Any]) -> Optional[str]:
    config = _configuration(record)
    protocol = config.get("protocol")
    value = protocol.get("name") if isinstance(protocol, dict) else None
    return record.get("protocol") or value


def _impairments_applied(record: dict[str, Any]) -> bool:
    channel = _configuration(record).get("channel")
    return isinstance(channel, dict) and channel.get("impairments_applied") is True


def _control_parameters(record: dict[str, Any], family: str) -> dict[str, Any]:
    config = _configuration(record)
    protocol = config.get("protocol") if isinstance(config.get("protocol"), dict) else {}
    channel = config.get("channel") if isinstance(config.get("channel"), dict) else {}
    file_config = config.get("file") if isinstance(config.get("file"), dict) else {}
    controls: dict[str, Any] = {
        "file_size_bytes": file_config.get("file_size_bytes", record.get("file_size_bytes")),
        "test_file": file_config.get("test_file"),
        "payload_size_bytes": protocol.get("payload_size_bytes", record.get("payload_size_bytes")),
        "window_size": protocol.get("window_size", config.get("window_size", record.get("window_size"))),
        "rto_ms": protocol.get("rto_ms", config.get("rto_ms", record.get("rto_ms"))),
        "loss_rate": channel.get("loss_rate", record.get("loss_rate")),
        "duplication_rate": channel.get("duplication_rate", record.get("duplication_rate")),
        "corruption_rate": channel.get("corruption_rate", record.get("corruption_rate")),
        "reordering_rate": channel.get("reordering_rate", record.get("reordering_rate")),
        "delay_ms": channel.get("delay_ms", record.get("delay_ms")),
        "jitter_ms": channel.get("jitter_ms", record.get("jitter_ms")),
    }
    swept_control = {
        "loss_rate": "loss_rate",
        "window_size": "window_size",
        "reordering_rate": "reordering_rate",
        "rto_ms": "rto_ms",
    }.get(family)
    if swept_control:
        controls.pop(swept_control, None)
    return controls


def _controls_complete(controls: dict[str, Any], family: str) -> bool:
    required = {
        "file_size_bytes", "payload_size_bytes", "window_size", "rto_ms",
        "loss_rate", "duplication_rate", "corruption_rate", "reordering_rate",
        "delay_ms", "jitter_ms",
    }
    swept_control = {
        "loss_rate": "loss_rate",
        "window_size": "window_size",
        "reordering_rate": "reordering_rate",
        "rto_ms": "rto_ms",
    }.get(family)
    if swept_control:
        required.remove(swept_control)
    return all(controls.get(name) is not None for name in required)


def _is_successful_actual(record: dict[str, Any]) -> bool:
    if _provenance(record) != "actual":
        return False
    if record.get("execution_status") != "completed":
        return False
    integrity = record.get("integrity")
    if isinstance(integrity, dict):
        integrity_pass = integrity.get("integrity_pass")
    else:
        integrity_pass = _metric(record, "integrity_pass")
    if isinstance(integrity_pass, str):
        integrity_pass = integrity_pass.strip().lower() == "true"
    if integrity_pass is not True:
        return False
    return _protocol(record) is not None


def _stats(values: Iterable[float]) -> dict[str, Any]:
    sequence = list(values)
    return {
        "run_count": len(sequence),
        "mean": statistics.fmean(sequence) if sequence else None,
        "median": statistics.median(sequence) if sequence else None,
        "min": min(sequence) if sequence else None,
        "max": max(sequence) if sequence else None,
        "standard_deviation": statistics.stdev(sequence) if len(sequence) >= 2 else None,
    }


def _group_actual(
    records: list[dict[str, Any]], parameter: str, metrics: list[str], *, require_applied_impairment: bool = False,
) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, float, str], list[dict[str, Any]]] = {}
    controls_by_key: dict[tuple[str, float, str], dict[str, Any]] = {}
    for record in records:
        if not _is_successful_actual(record):
            continue
        x_value = _parameter(record, parameter)
        protocol = _protocol(record)
        if x_value is None or protocol is None:
            continue
        if require_applied_impairment and not _impairments_applied(record):
            continue
        if parameter in {"loss_rate", "reordering_rate"} and x_value != 0 and not _impairments_applied(record):
            continue
        controls = _control_parameters(record, parameter)
        if not _controls_complete(controls, parameter):
            continue
        control_key = json.dumps(controls, sort_keys=True, separators=(",", ":"))
        key = (protocol, x_value, control_key)
        controls_by_key[key] = controls
        grouped.setdefault(key, []).append(record)

    output = []
    for (protocol, x_value, control_key), runs in sorted(grouped.items()):
        values: dict[str, Any] = {}
        for metric in metrics:
            raw = []
            for record in runs:
                value = _metric(record, metric)
                try:
                    numeric = float(value)
                except (TypeError, ValueError):
                    continue
                if math.isfinite(numeric):
                    raw.append(numeric)
            values[metric] = {**_stats(raw), "raw_values": raw}
        output.append({
            "protocol": protocol,
            "parameter": parameter,
            "parameter_value": x_value,
            "control_parameters": controls_by_key[(protocol, x_value, control_key)],
            "records": len(runs),
            "metrics": values,
        })
    return output


def _has_parameter_variation(groups: list[dict[str, Any]], metric: str) -> bool:
    values_by_stratum: dict[tuple[str, str], set[float]] = {}
    for group in groups:
        if group["metrics"].get(metric, {}).get("run_count", 0) <= 0:
            continue
        key = (group["protocol"], json.dumps(group["control_parameters"], sort_keys=True, separators=(",", ":")))
        values_by_stratum.setdefault(key, set()).add(group["parameter_value"])
    return any(len(values) >= 2 for values in values_by_stratum.values())


def analyze_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    actual = [record for record in records if _provenance(record) == "actual"]
    synthetic = [record for record in records if _provenance(record) == "synthetic"]
    legacy = [record for record in records if _provenance(record) == "legacy_unverified"]
    successful = [record for record in actual if _is_successful_actual(record)]
    failed_actual = [record for record in actual if not _is_successful_actual(record)]

    groups = {
        "goodput_vs_loss_rate": _group_actual(successful, "loss_rate", ["goodput_bps"]),
        "goodput_vs_window_size": _group_actual(successful, "window_size", ["goodput_bps"]),
        "retransmissions_vs_reordering_probability": _group_actual(
            successful, "reordering_rate", ["retransmissions"], require_applied_impairment=True,
        ),
        "rto_sensitivity": _group_actual(successful, "rto_ms", ["transfer_duration_seconds", "retransmissions", "timeouts", "goodput_bps"]),
    }

    protocols = sorted({_protocol(record) for record in successful if _protocol(record)})
    loss_groups = groups["goodput_vs_loss_rate"]
    window_groups = groups["goodput_vs_window_size"]
    reorder_groups = groups["retransmissions_vs_reordering_probability"]
    rto_groups = groups["rto_sensitivity"]
    loss_varied = _has_parameter_variation(loss_groups, "goodput_bps")
    window_varied = _has_parameter_variation(window_groups, "goodput_bps")
    reorder_varied = _has_parameter_variation(reorder_groups, "retransmissions")
    rto_varied = _has_parameter_variation(rto_groups, "transfer_duration_seconds")
    actual_nonzero_loss = any(
        group["parameter_value"] != 0 and group["metrics"]["goodput_bps"]["run_count"] > 0
        for group in loss_groups
    )
    actual_nonzero_reordering = any(
        group["parameter_value"] != 0 and group["metrics"]["retransmissions"]["run_count"] > 0
        for group in reorder_groups
    )
    rto_values = {group["parameter_value"] for group in rto_groups}

    expected_protocols = {"stop-and-wait", "go-back-n", "selective-repeat"}
    missing_protocols = sorted(expected_protocols - set(protocols))

    families = {
        "goodput_vs_loss_rate": {
            "status": "BLOCKED" if not actual_nonzero_loss else ("PARTIALLY_AVAILABLE" if missing_protocols else ("COMPLETE" if loss_varied else "INSUFFICIENT_DATA")),
            "reason": (
                "No actual nonzero loss-rate measurements exist; live actual execution rejects impaired channels."
                if not actual_nonzero_loss else
                "Actual loss-rate data exists, but protocol implementations are missing: " + ", ".join(missing_protocols)
                if missing_protocols else
                "Actual measurements do not vary loss rate with other configuration controls fixed."
                if not loss_varied else
                "All expected protocols and multiple controlled loss settings have actual data."
            ),
            "valid_run_count": len(successful),
            "missing_protocols": missing_protocols,
            "groups": groups["goodput_vs_loss_rate"],
        },
        "goodput_vs_window_size": {
            "status": "INSUFFICIENT_DATA" if not window_varied else ("PARTIALLY_AVAILABLE" if missing_protocols else "COMPLETE"),
            "reason": (
                "Actual evidence does not vary window size within an implemented protocol and fixed control settings."
                if not window_varied else
                "Window settings vary in actual data, but protocol implementations are missing: " + ", ".join(missing_protocols)
                if missing_protocols else
                "Multiple controlled window settings have actual data."
            ),
            "valid_run_count": len(successful),
            "window_parameter_varied_with_controls_fixed": window_varied,
            "groups": groups["goodput_vs_window_size"],
        },
        "retransmissions_vs_reordering_probability": {
            "status": "BLOCKED" if not actual_nonzero_reordering else ("PARTIALLY_AVAILABLE" if missing_protocols else ("COMPLETE" if reorder_varied else "INSUFFICIENT_DATA")),
            "reason": (
                "No successful actual records declare that reordering impairment was applied; configured probability alone is not evidence of applied reordering."
                if not actual_nonzero_reordering else
                "Actual reordering measurements exist, but protocol implementations are missing: " + ", ".join(missing_protocols)
                if missing_protocols else
                "Actual reordering data does not vary probability with other configuration controls fixed."
                if not reorder_varied else
                "Multiple controlled, applied reordering settings have actual data."
            ),
            "valid_run_count": sum(group["records"] for group in reorder_groups),
            "groups": reorder_groups,
        },
        "rto_sensitivity": {
            "status": "INSUFFICIENT_DATA" if not rto_varied else ("PARTIALLY_AVAILABLE" if missing_protocols else "COMPLETE"),
            "reason": (
                "Configured RTO does not vary across controlled actual runs, so sensitivity cannot be assessed. Configured RTO is not the same as a measured RTO; timeout-derived samples are only present when timeouts occur."
                if not rto_varied else
                "RTO values vary in actual data, but protocol implementations are missing: " + ", ".join(missing_protocols)
                if missing_protocols else
                "Multiple controlled configured RTO values have actual measurements."
            ),
            "valid_run_count": len(successful),
            "configured_rto_values_ms": sorted(value for value in rto_values if value is not None),
            "groups": rto_groups,
        },
    }

    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "analysis_source": "actual_only",
        "inventory": {
            "total_records": len(records),
            "actual_records": len(actual),
            "successful_actual_runs": len(successful),
            "failed_or_incomplete_actual_records": len(failed_actual),
            "synthetic_records_excluded": len(synthetic),
            "legacy_unverified_records_excluded": len(legacy),
            "successful_protocols": protocols,
        },
        "groups": groups,
        "experiment_families": families,
        "raw_actual_run_ids": [record.get("run_id") for record in successful],
        "source_files": sorted({record.get("_source_file") for record in records if record.get("_source_file")}),
        "actual_source_files": sorted({record.get("_source_file") for record in actual if record.get("_source_file")}),
    }


def analyze_results(results_dirs: str | Path | Iterable[str | Path]) -> dict[str, Any]:
    return analyze_records(load_records(results_dirs))


def write_analysis(results_dirs: str | Path | Iterable[str | Path], output_dir: str | Path) -> tuple[Path, Path]:
    results = analyze_results(results_dirs)
    output = Path(output_dir) / str(uuid4())
    output.mkdir(parents=True, exist_ok=False)
    analysis_path = output / "analysis.json"
    manifest_path = output / "manifest.json"
    analysis_path.write_text(json.dumps(results, indent=2, allow_nan=False), encoding="utf-8")
    manifest = {
        "analysis_file": analysis_path.name,
        "source_result_files": results["source_files"],
        "analysis_source": results["analysis_source"],
        "inventory": results["inventory"],
        "experiment_statuses": {name: details["status"] for name, details in results["experiment_families"].items()},
        "graphs": [],
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, allow_nan=False), encoding="utf-8")
    status_lines = ["# Actual-result analysis status", "", f"Valid successful actual runs: {results['inventory']['successful_actual_runs']}", ""]
    for name, details in results["experiment_families"].items():
        status_lines.extend([f"## {name}: {details['status']}", "", details["reason"], ""])
    (output / "status.md").write_text("\n".join(status_lines), encoding="utf-8")
    return analysis_path, manifest_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze ReliableUDP actual experiment results without treating unknown legacy provenance as actual")
    parser.add_argument("--results-dir", nargs="+", default=["experiments/results"])
    parser.add_argument("--output-dir", default="experiments/analysis")
    args = parser.parse_args()
    analysis_path, manifest_path = write_analysis(args.results_dir, args.output_dir)
    print(json.dumps({"analysis": str(analysis_path), "manifest": str(manifest_path)}, indent=2))


if __name__ == "__main__":
    main()