import json
import unittest
from pathlib import Path

from reliable_udp.experiment import ExperimentConfig, ExperimentRunner


class TestExperimentFramework(unittest.TestCase):
    def test_experiment_runner_writes_results(self):
        output_dir = Path("tests/tmp_results")
        output_dir.mkdir(exist_ok=True)
        runner = ExperimentRunner(output_dir)
        config = ExperimentConfig(
            protocol="go-back-n",
            loss_rate=0.05,
            window_size=8,
            seed=123,
            file_size_bytes=2048,
            repetitions=2,
        )
        result = runner.run_single(config)
        self.assertTrue((output_dir / f"{config.protocol}_{config.seed}_{config.loss_rate}_{config.window_size}.json").exists())
        self.assertGreater(result.goodput_mbps, 0)

    def test_experiment_csv_export(self):
        output_dir = Path("tests/tmp_results")
        runner = ExperimentRunner(output_dir)
        config = ExperimentConfig(protocol="selective-repeat", loss_rate=0.02, window_size=16, seed=456)
        result = runner.run_single(config)
        csv_path = output_dir / "summary.csv"
        runner.export_csv([result], csv_path)
        self.assertTrue(csv_path.exists())


if __name__ == "__main__":
    unittest.main()
