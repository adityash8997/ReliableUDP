from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

try:
    from analyze_results import write_analysis
except ModuleNotFoundError:
    from scripts.analyze_results import write_analysis


FAMILY_PLOTS = {
    "goodput_vs_loss_rate": {
        "x": "loss_rate",
        "metric": "goodput_bps",
        "title": "Goodput vs Configured Packet Loss Rate",
        "xlabel": "Configured packet loss probability",
        "ylabel": "Mean goodput (Mbps)",
        "scale": 1_000_000,
        "format": ".3g",
        "filename": "goodput_vs_loss_rate.png",
    },
    "goodput_vs_window_size": {
        "x": "window_size",
        "metric": "goodput_bps",
        "title": "Goodput vs Window Size",
        "xlabel": "Window size (packets)",
        "ylabel": "Mean goodput (Mbps)",
        "scale": 1_000_000,
        "format": "g",
        "filename": "goodput_vs_window_size.png",
    },
    "retransmissions_vs_reordering_probability": {
        "x": "reordering_rate",
        "metric": "retransmissions",
        "title": "Retransmissions vs Configured Reordering Probability",
        "xlabel": "Configured reordering probability",
        "ylabel": "Mean retransmission events (count)",
        "scale": 1,
        "format": ".3g",
        "filename": "retransmissions_vs_reordering_probability.png",
    },
}


def _supported_groups(family: dict[str, Any], metric_names: list[str]) -> dict[str, list[dict[str, Any]]]:
    by_stratum: dict[tuple[str, str], list[dict[str, Any]]] = {}
    controls_by_stratum: dict[tuple[str, str], dict[str, Any]] = {}
    for group in family.get("groups", []):
        if any(group.get("metrics", {}).get(name, {}).get("run_count", 0) > 0 for name in metric_names):
            controls = group.get("control_parameters", {})
            controls_key = json.dumps(controls, sort_keys=True, separators=(",", ":"))
            key = (group["protocol"], controls_key)
            controls_by_stratum[key] = controls
            by_stratum.setdefault(key, []).append(group)

    supported = {}
    for key, groups in by_stratum.items():
        if len({group["parameter_value"] for group in groups}) < 2:
            continue
        protocol, _ = key
        controls = controls_by_stratum[key]
        protocol_strata = [item for item in by_stratum if item[0] == protocol]
        if len(protocol_strata) == 1:
            label = protocol
        else:
            label = f"{protocol} (file={controls.get('file_size_bytes')} B, payload={controls.get('payload_size_bytes')} B)"
        supported[label] = sorted(groups, key=lambda group: group["parameter_value"])
    return supported


def _annotate_counts(ax: Any, x_values: list[float], y_values: list[float], counts: list[int]) -> None:
    for x_value, y_value, count in zip(x_values, y_values, counts):
        ax.annotate(f"n={count}", (x_value, y_value), xytext=(4, 5), textcoords="offset points", fontsize=8)


def _plot_single_family(
    family_name: str,
    family: dict[str, Any],
    spec: dict[str, Any],
    destination: Path,
) -> Optional[dict[str, Any]]:
    by_protocol = _supported_groups(family, [spec["metric"]])
    if not by_protocol:
        return None

    fig, ax = plt.subplots(figsize=(8, 5))
    for protocol, groups in sorted(by_protocol.items()):
        x_values = [group["parameter_value"] for group in groups]
        stats = [group["metrics"][spec["metric"]] for group in groups]
        values = [item["mean"] / spec["scale"] for item in stats]
        deviations = [
            item["standard_deviation"] / spec["scale"] if item["run_count"] >= 2 and item["standard_deviation"] is not None else 0
            for item in stats
        ]
        ax.errorbar(
            x_values,
            values,
            yerr=deviations if any(deviations) else None,
            fmt="o",
            linestyle="none",
            capsize=3,
            label=protocol,
        )
        _annotate_counts(ax, x_values, values, [item["run_count"] for item in stats])

    ax.set_title(spec["title"])
    ax.set_xlabel(spec["xlabel"])
    ax.set_ylabel(spec["ylabel"])
    ax.legend(title="Protocol")
    ax.grid(True, alpha=0.25)
    ax.ticklabel_format(axis="y", style="plain", useOffset=False)
    fig.tight_layout()
    path = destination / spec["filename"]
    fig.savefig(path, dpi=220, bbox_inches="tight")
    plt.close(fig)
    valid_runs = sum(
        group["metrics"][spec["metric"]]["run_count"]
        for groups in by_protocol.values()
        for group in groups
    )
    return {
        "filename": path.name,
        "experiment_family": family_name,
        "source_result_files": [],
        "result_source": "actual",
        "valid_runs": valid_runs,
        "analysis_status": family["status"],
        "generation_timestamp": datetime.now(timezone.utc).isoformat(),
        "statistic": "mean; standard deviation error bars only when at least two valid runs exist at a point",
        "points": sum(len(groups) for groups in by_protocol.values()),
    }


def _plot_rto_sensitivity(family: dict[str, Any], destination: Path) -> Optional[dict[str, Any]]:
    metrics = ["transfer_duration_seconds", "retransmissions", "timeouts", "goodput_bps"]
    by_protocol = _supported_groups(family, metrics)
    if not by_protocol:
        return None

    specs = [
        ("transfer_duration_seconds", "Mean completion duration (s)", 1),
        ("retransmissions", "Mean retransmission events (count)", 1),
        ("timeouts", "Mean timeout events (count)", 1),
        ("goodput_bps", "Mean goodput (Mbps)", 1_000_000),
    ]
    fig, axes = plt.subplots(2, 2, figsize=(10, 7))
    for ax, (metric, ylabel, scale) in zip(axes.flat, specs):
        for protocol, groups in sorted(by_protocol.items()):
            valid = [group for group in groups if group["metrics"][metric]["run_count"] > 0]
            x_values = [group["parameter_value"] for group in valid]
            stats = [group["metrics"][metric] for group in valid]
            y_values = [item["mean"] / scale for item in stats]
            deviations = [
                item["standard_deviation"] / scale if item["run_count"] >= 2 and item["standard_deviation"] is not None else 0
                for item in stats
            ]
            ax.errorbar(x_values, y_values, yerr=deviations if any(deviations) else None, fmt="o", linestyle="none", capsize=3, label=protocol)
            _annotate_counts(ax, x_values, y_values, [item["run_count"] for item in stats])
        ax.set_xlabel("Configured retransmission timeout (ms)")
        ax.set_ylabel(ylabel)
        ax.grid(True, alpha=0.25)
    axes[0, 0].legend(title="Protocol", fontsize=8)
    fig.suptitle("RTO Sensitivity (configured RTO; measurements are actual runs)")
    fig.tight_layout()
    path = destination / "rto_sensitivity.png"
    fig.savefig(path, dpi=220, bbox_inches="tight")
    plt.close(fig)
    valid_runs = sum(
        group["metrics"]["transfer_duration_seconds"]["run_count"]
        for groups in by_protocol.values()
        for group in groups
    )
    return {
        "filename": path.name,
        "experiment_family": "rto_sensitivity",
        "source_result_files": [],
        "result_source": "actual",
        "valid_runs": valid_runs,
        "analysis_status": family["status"],
        "generation_timestamp": datetime.now(timezone.utc).isoformat(),
        "statistic": "mean; standard deviation error bars only when at least two valid runs exist at a point",
        "points": sum(len(groups) for groups in by_protocol.values()),
    }


def generate_graphs(analysis: dict[str, Any], output_dir: str | Path) -> dict[str, Any]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=False)
    families = analysis.get("experiment_families", {})
    graphs: list[dict[str, Any]] = []
    for family_name, spec in FAMILY_PLOTS.items():
        family = families.get(family_name, {})
        graph = _plot_single_family(family_name, family, spec, output)
        if graph:
            graph["source_result_files"] = analysis.get("actual_source_files", [])
            graphs.append(graph)
    rto_family = families.get("rto_sensitivity", {})
    rto_graph = _plot_rto_sensitivity(rto_family, output)
    if rto_graph:
        rto_graph["source_result_files"] = analysis.get("actual_source_files", [])
        graphs.append(rto_graph)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "result_source": "actual",
        "analysis_source": analysis.get("analysis_source"),
        "graphs": graphs,
        "unavailable_families": {
            name: {
                "status": details.get("status"),
                "reason": details.get("reason"),
                "valid_run_count": details.get("valid_run_count", 0),
            }
            for name, details in families.items()
            if not any(graph["experiment_family"] == name for graph in graphs)
        },
    }
    (output / "graph_manifest.json").write_text(json.dumps(report, indent=2, allow_nan=False), encoding="utf-8")
    status_lines = ["# Graph generation status", "", "No graph is generated unless at least one protocol has two distinct actual parameter settings with the other recorded controls held fixed.", ""]
    if graphs:
        status_lines.extend(["Generated graphs:", ""])
        status_lines.extend(f"- {graph['filename']}: {graph['experiment_family']} ({graph['valid_runs']} valid runs)" for graph in graphs)
    else:
        status_lines.extend(["No performance graph was generated: the available actual dataset does not vary any required parameter.", ""])
    for name, details in report["unavailable_families"].items():
        status_lines.extend([f"## {name}: {details['status']}", "", details["reason"], ""])
    (output / "graph_status.md").write_text("\n".join(status_lines), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate performance graphs from valid actual ReliableUDP results only")
    parser.add_argument("--results-dir", nargs="+", default=["experiments/results"])
    parser.add_argument("--output-dir", default="experiments/analysis")
    args = parser.parse_args()
    analysis_path, manifest_path = write_analysis(args.results_dir, args.output_dir)
    analysis = json.loads(analysis_path.read_text(encoding="utf-8"))
    graph_dir = analysis_path.parent / f"graphs-{uuid4()}"
    report = generate_graphs(analysis, graph_dir)
    manifest_path.write_text(json.dumps({
        "analysis_file": analysis_path.name,
        "source_result_files": analysis.get("actual_source_files", []),
        "analysis_source": analysis.get("analysis_source"),
        "inventory": analysis.get("inventory"),
        "experiment_statuses": {name: details["status"] for name, details in analysis.get("experiment_families", {}).items()},
        "graph_directory": graph_dir.name,
        "graphs": report["graphs"],
    }, indent=2, allow_nan=False), encoding="utf-8")
    print(json.dumps({"analysis": str(analysis_path), "graph_directory": str(graph_dir), "graph_count": len(report["graphs"]), "manifest": str(manifest_path)}, indent=2))


if __name__ == "__main__":
    main()