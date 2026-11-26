import csv
import json
import tempfile
import unittest
from pathlib import Path

from lgpe_research.coverage import build_coverage


class CoverageTests(unittest.TestCase):
    def test_coverage_counts_scan_and_consumed_label_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            manifest = project / "manifests" / "files.csv"
            manifest.parent.mkdir()
            fields = ["partition", "relative_path", "suffix", "kind", "bytes", "signature", "header_hex", "sha256"]
            files = [
                ("romfs", "bin/message/English/common/a.dat", ".dat", "data-unknown"),
                ("romfs", "bin/message/English/common/a.tbl", ".tbl", "table-unknown"),
                ("romfs", "bin/sound/a.bnk", ".bnk", "audio-bank"),
                ("exefs", "main", "", "unknown"),
            ]
            with manifest.open("w", encoding="utf-8-sig", newline="") as stream:
                writer = csv.writer(stream)
                writer.writerow(fields)
                for partition, rel, suffix, kind in files:
                    writer.writerow([partition, rel, suffix, kind, 10, "unidentified", "", ""])
            (project / "manifests" / "gamedata.jsonl").write_text(
                json.dumps({
                    "domain": "gamedata", "source": files[0][1], "companion": files[1][1],
                    "status": "DECODED", "output_bytes": 42,
                }) + "\n",
                encoding="utf-8",
            )

            summary = build_coverage(project)
            self.assertEqual(summary["scanned"], 4)
            self.assertEqual(summary["decoded_sources"], 2)
            self.assertEqual(summary["decoded_outputs"], 1)
            self.assertEqual(summary["unknown_sources"], 2)
            with (project / "manifests" / "coverage.csv").open(encoding="utf-8-sig", newline="") as stream:
                rows = list(csv.DictReader(stream))
            by_path = {row["relative_path"]: row for row in rows}
            self.assertEqual(by_path[files[1][1]]["analysis_status"], "DECODED")
            self.assertIn("label/index", by_path[files[1][1]]["status_reason"])

    def test_coverage_counts_raw_and_parsed_outputs_for_container(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            manifest = project / "manifests" / "files.csv"
            manifest.parent.mkdir()
            fields = ["partition", "relative_path", "suffix", "kind", "bytes", "signature", "header_hex", "sha256"]
            with manifest.open("w", encoding="utf-8-sig", newline="") as stream:
                writer = csv.writer(stream)
                writer.writerow(fields)
                writer.writerow(["romfs", "bin/archive/waza_oboe.gfpak", ".gfpak", "archive", 100, "GFLXPACK", "", ""])
            archive = {"source": "bin/archive/waza_oboe.gfpak", "status": "DECODED", "member_count": 2}
            (project / "manifests" / "archives.jsonl").write_text(json.dumps(archive) + "\n", encoding="utf-8")
            learnset = {"source": "bin/archive/waza_oboe.gfpak", "status": "DECODED", "count": 980}
            (project / "manifests" / "learnsets.jsonl").write_text(json.dumps(learnset) + "\n", encoding="utf-8")
            outputs = [
                {"partition": "romfs", "relative_source": "bin/archive/waza_oboe.gfpak", "output_file": "raw/member1"},
                {"partition": "romfs", "relative_source": "bin/archive/waza_oboe.gfpak", "output_file": "raw/member2"},
                {"partition": "romfs", "relative_source": "bin/archive/waza_oboe.gfpak", "output_file": "json/member1.json"},
                {"partition": "romfs", "relative_source": "bin/archive/waza_oboe.gfpak", "output_file": "json/member2.json"},
            ]
            (project / "manifests" / "outputs.jsonl").write_text(
                "".join(json.dumps(row) + "\n" for row in outputs), encoding="utf-8",
            )
            summary = build_coverage(project)
            self.assertEqual(summary["decoded_sources"], 1)
            self.assertEqual(summary["decoded_outputs"], 4)


if __name__ == "__main__":
    unittest.main()
