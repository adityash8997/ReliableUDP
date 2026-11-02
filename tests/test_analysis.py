import json
import tempfile
import unittest
from pathlib import Path

from scripts.analyze_results import analyze_records, analyze_results, load_records


def _actual_record(run_id: str, *, loss: float = 0.0, window: int = 1, rto: float = 100.0, goodput: float = 800.0, status: str = "completed", integrity: bool = True) -> dict:
    return {
        "schema_version": 1,
        "experiment_id": "experiment",
        "run_id": run_id,
        "result_source": "actual",
        "protocol": "stop-and-wait",
        "execution_status": status,
        "configuration": {
            "protocol": {"name": "stop-and-wait", "window_size": window, "rto_ms": rto, "payload_size_bytes": 128},
            "channel": {
                "loss_rate": loss,
                "duplication_rate": 0.0,
                "corruption_rate": 0.0,
                "reordering_rate": 0.0,
                "delay_ms": 0.0,
                "jitter_ms": 0.0,
            },
            "file": {"file_size_bytes": 256, "test_file": None},
        },
        "metrics": {
            "goodput_bps": goodput,
            "transfer_duration_seconds": 1.0,
            "retransmissions": 0,
            "timeouts": 0,
        },
        "integrity": {"integrity_pass": integrity},
    }


class TestAnalysis(unittest.TestCase):
    def test_load_records_classifies_current_and_legacy_sources(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "actual").mkdir()
            (root / "legacy").mkdir()
            (root / "csv-only").mkdir()
            (root / "actual" / "run.json").write_text(json.dumps(_actual_record("one")), encoding="utf-8")
            (root / "legacy" / "old.json").write_text(json.dumps({"protocol": "go-back-n", "goodput_mbps": 1}), encoding="utf-8")
            (root / "csv-only" / "summary.csv").write_text("protocol,goodput_mbps\ngo-back-n,1\n", encoding="utf-8")

            records = load_records(root)

            self.assertEqual(sum(row["_provenance"] == "actual" for row in records), 1)
            self.assertEqual(sum(row["_provenance"] == "legacy_unverified" for row in records), 2)

    def test_failed_synthetic_and_legacy_records_do_not_enter_actual_aggregates(self):
        actual = _actual_record("valid", goodput=800)
        failed = _actual_record("failed", status="failed", goodput=900)
        synthetic = dict(_actual_record("synthetic"), result_source="synthetic", _provenance="synthetic")
        legacy = {"protocol": "selective-repeat", "goodput_mbps": 5, "_provenance": "legacy_unverified"}

        analysis = analyze_records([actual, failed, synthetic, legacy])

        self.assertEqual(analysis["inventory"]["successful_actual_runs"], 1)
        self.assertEqual(analysis["inventory"]["failed_or_incomplete_actual_records"], 1)
        self.assertEqual(analysis["inventory"]["synthetic_records_excluded"], 1)
        self.assertEqual(analysis["inventory"]["legacy_unverified_records_excluded"], 1)
        loss_group = analysis["groups"]["goodput_vs_loss_rate"][0]
        self.assertEqual(loss_group["metrics"]["goodput_bps"]["run_count"], 1)
        self.assertEqual(loss_group["metrics"]["goodput_bps"]["mean"], 800)
        self.assertIsNone(loss_group["metrics"]["goodput_bps"]["standard_deviation"])

    def test_statistics_and_parameter_grouping(self):
        records = [_actual_record("a", window=1, goodput=100), _actual_record("b", window=1, goodput=300), _actual_record("c", window=2, goodput=500)]

        analysis = analyze_records(records)

        groups = analysis["groups"]["goodput_vs_window_size"]
        self.assertEqual([group["parameter_value"] for group in groups], [1.0, 2.0])
        first = groups[0]["metrics"]["goodput_bps"]
        self.assertEqual(first["run_count"], 2)
        self.assertEqual(first["mean"], 200)
        self.assertEqual(first["median"], 200)
        self.assertEqual(first["min"], 100)
        self.assertEqual(first["max"], 300)
        self.assertAlmostEqual(first["standard_deviation"], 141.4213562373095)
        self.assertEqual(first["raw_values"], [100.0, 300.0])

    def test_current_actual_inventory_statuses_are_honest(self):
        analysis = analyze_records([_actual_record("one")])
        families = analysis["experiment_families"]

        self.assertEqual(families["goodput_vs_loss_rate"]["status"], "BLOCKED")
        self.assertEqual(families["goodput_vs_window_size"]["status"], "INSUFFICIENT_DATA")
        self.assertEqual(families["retransmissions_vs_reordering_probability"]["status"], "BLOCKED")
        self.assertEqual(families["rto_sensitivity"]["status"], "INSUFFICIENT_DATA")

    def test_analyze_results_uses_current_actual_tree_without_legacy_promotion(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "actual" / "experiment").mkdir(parents=True)
            (root / "actual" / "experiment" / "run.json").write_text(json.dumps(_actual_record("run")), encoding="utf-8")

            analysis = analyze_results(root)

            self.assertEqual(analysis["analysis_source"], "actual_only")
            self.assertEqual(analysis["inventory"]["successful_actual_runs"], 1)

    def test_multiple_result_roots_combine_runs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            first = root / "run-a"
            second = root / "run-b"
            first.mkdir()
            second.mkdir()
            (first / "a.json").write_text(json.dumps(_actual_record("a")), encoding="utf-8")
            (second / "b.json").write_text(json.dumps(_actual_record("b")), encoding="utf-8")

            analysis = analyze_results([first, second])

            self.assertEqual(analysis["inventory"]["successful_actual_runs"], 2)
            self.assertEqual(len(analysis["raw_actual_run_ids"]), 2)


if __name__ == "__main__":
    unittest.main()