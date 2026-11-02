import csv
import json
import tempfile
import unittest
from pathlib import Path

from reliable_udp.experiment import ExperimentConfig, ExperimentRunner


class TestExperimentFramework(unittest.TestCase):
    def test_actual_runner_repeats_real_transfer_and_writes_json_csv(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "results"
            runner = ExperimentRunner(output_dir)
            config = ExperimentConfig(
                protocol="stop-and-wait",
                seed=123,
                file_size_bytes=257,
                payload_size_bytes=64,
                repetitions=3,
                rto_ms=100,
                max_execution_seconds=5,
            )

            results = runner.run_suite([config])

            self.assertEqual(len(results), 3)
            self.assertEqual({result.result_source for result in results}, {"actual"})
            self.assertEqual({result.execution_status for result in results}, {"completed"})
            self.assertEqual([result.random_seed for result in results], [123, 124, 125])
            self.assertEqual(len({result.run_id for result in results}), 3)
            self.assertEqual(len({result.experiment_id for result in results}), 1)

            for result in results:
                self.assertTrue(result.integrity["integrity_pass"])
                self.assertEqual(result.integrity["source_sha256"], result.integrity["destination_sha256"])
                self.assertEqual(result.metrics["source_file_size_bytes"], 257)
                self.assertEqual(result.metrics["reconstructed_file_size_bytes"], 257)
                self.assertEqual(result.metrics["total_useful_payload_bytes"], 257)
                self.assertGreater(result.metrics["data_packets_transmitted"], 0)
                self.assertEqual(result.metrics["data_packets_transmitted"], result.metrics["data_packets_received"])
                self.assertGreater(result.metrics["ack_packets_transmitted"], 0)
                self.assertGreater(result.metrics["ack_packets_received"], 0)
                self.assertIsNone(result.metrics["packet_loss_rate"])
                self.assertTrue((output_dir / "actual" / result.experiment_id / f"{result.run_id}.json").is_file())

            csv_path = output_dir / "actual" / results[0].experiment_id / f"{results[0].experiment_id}.csv"
            with csv_path.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(len(rows), 3)
            self.assertEqual({row["result_source"] for row in rows}, {"actual"})
            saved = json.loads((output_dir / "actual" / results[0].experiment_id / f"{results[0].run_id}.json").read_text())
            self.assertEqual(saved["integrity"]["source_sha256"], results[0].integrity["source_sha256"])
            self.assertEqual(saved["configuration"]["protocol"]["payload_size_bytes"], 64)

    def test_synthetic_mode_is_explicit_and_separated(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            runner = ExperimentRunner(temp_dir, mode="synthetic")
            config = ExperimentConfig(protocol="go-back-n", loss_rate=0.1, window_size=4, repetitions=2)

            results = runner.run_suite([config])

            self.assertEqual(len(results), 2)
            self.assertTrue(all(result.result_source == "synthetic" for result in results))
            self.assertTrue(all(result.execution_status == "demo_only" for result in results))
            self.assertTrue(all(result.integrity["integrity_pass"] is None for result in results))
            self.assertTrue(all((Path(temp_dir) / "synthetic" / result.experiment_id / f"{result.run_id}.json").exists() for result in results))
            self.assertFalse((Path(temp_dir) / "actual").exists())
            csv_path = Path(temp_dir) / "synthetic" / results[0].experiment_id / f"{results[0].experiment_id}.csv"
            with csv_path.open(newline="", encoding="utf-8") as handle:
                self.assertEqual({row["result_source"] for row in csv.DictReader(handle)}, {"synthetic"})
            with self.assertRaises(FileExistsError):
                runner._save_json(results[0])

    def test_actual_mode_rejects_unimplemented_protocol_without_fallback(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            runner = ExperimentRunner(temp_dir)
            with self.assertRaisesRegex(NotImplementedError, "only Stop-and-Wait is implemented"):
                runner.run_single(ExperimentConfig(protocol="go-back-n", window_size=4))
            self.assertEqual(list(Path(temp_dir).rglob("*.json")), [])

    def test_actual_mode_rejects_impairments_not_connected_to_udp(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            runner = ExperimentRunner(temp_dir)
            config = ExperimentConfig(loss_rate=0.01)
            with self.assertRaisesRegex(NotImplementedError, "not connected to the UDP path"):
                runner.run_single(config)

    def test_invalid_configuration_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            runner = ExperimentRunner(temp_dir)
            with self.assertRaises(ValueError):
                runner.run_single(ExperimentConfig(file_size_bytes=-1))
            with self.assertRaises(ValueError):
                runner.run_single(ExperimentConfig(payload_size_bytes=0))
            with self.assertRaises(ValueError):
                runner.run_single(ExperimentConfig(repetitions=0))
            with self.assertRaises(ValueError):
                runner.run_single(ExperimentConfig(window_size=2))

    def test_execution_timeout_is_saved_as_failed_actual_run(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            runner = ExperimentRunner(temp_dir)
            config = ExperimentConfig(
                file_size_bytes=16,
                max_execution_seconds=0.001,
                rto_ms=20,
            )

            result = runner.run_single(config)

            self.assertEqual(result.result_source, "actual")
            self.assertEqual(result.execution_status, "failed")
            self.assertIsNotNone(result.error)
            self.assertTrue((Path(temp_dir) / "actual" / result.experiment_id / f"{result.run_id}.json").is_file())

    def test_exports_refuse_to_overwrite(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            runner = ExperimentRunner(temp_dir, mode="synthetic")
            result = runner.run_single(ExperimentConfig(protocol="go-back-n", window_size=4))
            path = Path(temp_dir) / "manual.csv"
            runner.export_csv([result], path)
            with self.assertRaises(FileExistsError):
                runner.export_csv([result], path)


if __name__ == "__main__":
    unittest.main()