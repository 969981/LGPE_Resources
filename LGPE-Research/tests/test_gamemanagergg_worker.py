from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from lgpe_research import gamemanagergg_worker as worker
from lgpe_research.core import NCA


class GameManagerGGWorkerTests(unittest.TestCase):
    def test_cli_wrapper_reads_worker_receipt_without_touching_source(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            game_root = base / "game"
            nca = game_root / "1.0.2" / NCA
            (nca / "0").mkdir(parents=True)
            (nca / "1").mkdir()

            project = base / "LGPE-Research"
            worker_project = project / "scripts/gamemanagergg-worker/gamemanagergg-worker.csproj"
            worker_project.parent.mkdir(parents=True)
            worker_project.write_text("<Project />", encoding="utf-8")

            def fake_dotnet(command, **_kwargs):
                if "--list-runtimes" in command:
                    return subprocess.CompletedProcess(command, 0, stdout="Microsoft.NETCore.App 10.0.0", stderr="")
                output = Path(command[command.index("--") + 3])
                output.mkdir(parents=True)
                (output / "receipt.json").write_text(
                    json.dumps({
                        "sourceUnchanged": True,
                        "inputFileCount": 1963,
                        "outputCounts": {"personal": 980},
                        "roundTrip": {"personal": {"exact": 980, "mismatches": 0}},
                    }),
                    encoding="utf-8",
                )
                return subprocess.CompletedProcess(command, 0, stdout="{}", stderr="")

            with (
                patch.object(worker, "_pknx_revision", return_value=worker.PKNX_COMMIT),
                patch.object(worker, "_find_dotnet", return_value=("dotnet", False)),
                patch.object(worker.subprocess, "run", side_effect=fake_dotnet),
            ):
                result = worker.run_gamemanagergg_worker(game_root, project)

            self.assertEqual(result["status"], "CROSSCHECKED")
            self.assertEqual(result["inputFiles"], 1963)
            self.assertTrue(result["sourceUnchanged"])
            self.assertEqual(result["roundTrip"]["personal"]["mismatches"], 0)
            self.assertEqual(list((nca / "1").iterdir()), [])


if __name__ == "__main__":
    unittest.main()
