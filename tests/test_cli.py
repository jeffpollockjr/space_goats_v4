import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.helpers import ROOT


class CLITests(unittest.TestCase):
    def run_cli(self, *args, cwd=ROOT):
        return subprocess.run([sys.executable, str(ROOT / "run_simulations.py"), *map(str, args)],
                              cwd=cwd, capture_output=True, text=True)

    def test_reports_and_replay_from_another_working_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "batch"
            result = self.run_cli("--players", 3, "--simulations", 4, "--observations", "--quiet",
                                  "--validate", "--output", output, cwd=Path(temp))
            self.assertEqual(result.returncode, 0, result.stderr)
            summary = json.loads((output / "summary.json").read_text())
            self.assertEqual(summary["simulations"], 4)
            self.assertEqual(sum(r["acquired"] for r in summary["card_statistics"]), 416)
            with (output / "card_observations.csv").open(encoding="utf-8-sig", newline="") as handle:
                self.assertEqual(len(list(csv.DictReader(handle))), 416)
            with (output / "game_results.csv").open(encoding="utf-8-sig", newline="") as handle:
                original = next(csv.DictReader(handle))
            replay = Path(temp) / "replay"
            result = self.run_cli("--players", 3, "--game-seed", original["game_seed"],
                                  "--start-player", original["starting_player"], "--output", replay, "--quiet")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual((output / "logs/game_0001.jsonl").read_bytes(),
                             (replay / "logs/game_0001.jsonl").read_bytes())

    def test_rotating_start_counts_differ_by_at_most_one(self):
        with tempfile.TemporaryDirectory() as temp:
            result = self.run_cli("--players", 5, "--simulations", 7, "--output", temp, "--quiet", "--log-games", 0)
            self.assertEqual(result.returncode, 0, result.stderr)
            summary = json.loads((Path(temp) / "summary.json").read_text())
            starts = [row["games_started"] for row in summary["player_statistics"]]
            self.assertEqual(sum(starts), 7)
            self.assertLessEqual(max(starts) - min(starts), 1)

    def test_help_and_argument_validation(self):
        result = self.run_cli("--help")
        self.assertEqual(result.returncode, 0)
        self.assertIn("--players", result.stdout)
        for args in (("--players", "6"), ("--players", "1"), ("--simulations", "0"),
                     ("--log-games", "-1"), ("--game-seed", "10"),
                     ("--players", "2", "--start-player", "3")):
            with self.subTest(args=args):
                self.assertEqual(self.run_cli(*args).returncode, 2)

    def test_bad_rules_and_deck_produce_readable_errors(self):
        with tempfile.TemporaryDirectory() as temp:
            bad_rules = Path(temp) / "bad.json"
            bad_rules.write_text('{"unknown": true}')
            result = self.run_cli("--rules", bad_rules, "--output", Path(temp) / "out")
            self.assertEqual(result.returncode, 2)
            self.assertIn("Unknown rule", result.stderr)
            result = self.run_cli("--deck", Path(temp) / "missing.csv")
            self.assertEqual(result.returncode, 2)
            self.assertIn("Error:", result.stderr)


if __name__ == "__main__":
    unittest.main()
