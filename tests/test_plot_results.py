import json
import tempfile
import unittest
from pathlib import Path

from scripts.analyze_results import analyze_records
from scripts.plot_results import generate_graphs


def _record(run_id: str, *, loss: float = 0.0, window: int = 1, rto: float = 100.0, goodput: float = 800.0) -> dict:
    return {
        "schema_version": 1,
        "run_id": run_id,
        "result_source": "actual",
        "protocol": "stop-and-wait",
        "execution_status": "completed",
        "configuration": {
            "protocol": {"name": "stop-and-wait", "window_size": window, "rto_ms": rto, "payload_size_bytes": 128},
            "channel": {
                "loss_rate": loss,
                "duplication_rate": 0.0,
                "corruption_rate": 0.0,
                "reordering_rate": 0.0,
                "delay_ms": 0.0,
                "jitter_ms": 0.0,
                "impairments_applied": loss > 0,
            },
            "file": {"file_size_bytes": 256, "test_file": None},
        },
        "metrics": {
            "goodput_bps": goodput,
            "transfer_duration_seconds": 1.0,
            "retransmissions": 0,
            "timeouts": 0,
        },
        "integrity": {"integrity_pass": True},
        "_provenance": "actual",
        "_source_file": f"{run_id}.json",
    }


class TestPlotResults(unittest.TestCase):
    def test_one_clean_run_creates_status_only_not_performance_curves(self):
        analysis = analyze_records([_record("only")])
        with tempfile.TemporaryDirectory() as temp_dir:
            report = generate_graphs(analysis, Path(temp_dir) / "graphs")
            output = Path(temp_dir) / "graphs"

            self.assertEqual(report["graphs"], [])
            self.assertEqual(list(output.glob("*.png")), [])
            manifest = json.loads((output / "graph_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["result_source"], "actual")
            self.assertEqual(len(manifest["unavailable_families"]), 4)
            self.assertTrue((output / "graph_status.md").is_file())

    def test_parameter_trend_graphs_use_only_actual_groups_and_manifest_counts(self):
        records = [
            _record("loss0", loss=0.0, window=1, rto=100, goodput=800),
            _record("loss1", loss=0.1, window=1, rto=100, goodput=600),
            _record("window2", loss=0.0, window=2, rto=100, goodput=900),
            _record("rto200", loss=0.0, window=1, rto=200, goodput=700),
        ]
        analysis = analyze_records(records)
        with tempfile.TemporaryDirectory() as temp_dir:
            report = generate_graphs(analysis, Path(temp_dir) / "graphs")
            graph_names = {item["filename"] for item in report["graphs"]}

            self.assertIn("goodput_vs_loss_rate.png", graph_names)
            self.assertIn("goodput_vs_window_size.png", graph_names)
            self.assertIn("rto_sensitivity.png", graph_names)
            self.assertNotIn("retransmissions_vs_reordering_probability.png", graph_names)
            self.assertTrue(all(item["result_source"] == "actual" for item in report["graphs"]))
            self.assertTrue(all(item["valid_runs"] >= 2 for item in report["graphs"]))
            self.assertTrue(all((Path(temp_dir) / "graphs" / name).is_file() for name in graph_names))


if __name__ == "__main__":
    unittest.main()