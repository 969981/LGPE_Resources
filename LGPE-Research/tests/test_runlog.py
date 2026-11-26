import json
import tempfile
import unittest
from pathlib import Path

from lgpe_research.runlog import RunJournal


class RunJournalTests(unittest.TestCase):
    def test_records_start_checkpoint_and_completion_in_order(self):
        with tempfile.TemporaryDirectory() as directory:
            journal = RunJournal(Path(directory), "decode", {"root": Path("/game")})
            journal.checkpoint("sample", {"decoded": 2})
            journal.finish(0)
            path = Path(directory) / "manifests" / "runs.jsonl"
            rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
            self.assertEqual([row["status"] for row in rows], ["RUNNING", "CHECKPOINT", "COMPLETED"])
            self.assertEqual([row["sequence"] for row in rows], [0, 1, 2])
            self.assertEqual(Path(rows[0]["detail"]["arguments"]["root"]).name, "game")
            self.assertEqual(rows[1]["detail"]["result"]["decoded"], 2)
            self.assertEqual(len({row["run_id"] for row in rows}), 1)

    def test_failed_run_has_terminal_error_event(self):
        with tempfile.TemporaryDirectory() as directory:
            journal = RunJournal(Path(directory), "scan", {})
            journal.finish(1, "permission denied")
            path = Path(directory) / "manifests" / "runs.jsonl"
            rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(rows[-1]["status"], "FAILED")
            self.assertEqual(rows[-1]["detail"]["error"], "permission denied")


if __name__ == "__main__":
    unittest.main()
