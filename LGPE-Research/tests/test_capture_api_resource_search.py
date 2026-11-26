import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from lgpe_research.capture_api_resource_search import (
    MAIN_SHA256,
    build_capture_api_resource_search,
)
import lgpe_research.cli as cli


def make_sample(project: Path, romfs: Path) -> None:
    (romfs / "bin/message/English/common").mkdir(parents=True)
    (romfs / "bin/battle/ai_script").mkdir(parents=True)
    archive = project / "decoded/1.0.2/romfs/bin/archive/script_amx.gfpak.contents"
    archive.mkdir(parents=True)
    (romfs / "bin/message/English/common/sample.dat").write_bytes(
        b"xxCaptureCallyy"
    )
    (romfs / "bin/battle/ai_script/sample.amx").write_bytes(
        "GetCaptureResult".encode("utf-16le")
    )
    (archive / "member-without-extension").write_bytes(
        b"xx" + "CaptureCall".encode("utf-16be") + b"yy"
    )
    (archive / "member.json").write_text(
        '{"text":"CaptureCall"}', encoding="utf-8"
    )


class CaptureApiResourceSearchTests(unittest.TestCase):
    def test_finds_ascii_and_utf16_literals_with_exact_offsets_and_hashes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            project = root / "project"
            romfs = root / "romfs"
            make_sample(project, romfs)

            report = build_capture_api_resource_search(
                project, romfs, main_sha256=MAIN_SHA256
            )

            self.assertEqual(report["schema"], "lgpe-research.capture-api-resource-string-search.v1")
            self.assertEqual(report["status"], "LITERAL_REFERENCE_CANDIDATE")
            self.assertEqual(report["search"]["files_scanned"], 3)
            source_files = report["search"]["source_files"]
            self.assertEqual(len(source_files), 3)
            self.assertTrue(all(len(row["source_sha256"]) == 64 for row in source_files))
            self.assertTrue(all(row["source_size"] > 0 for row in source_files))
            occurrences = [
                (row["relative_path"], hit["api_name"], hit["encoding"], hit["byte_offset"])
                for row in report["matches"]
                for hit in row["literal_occurrences"]
            ]
            self.assertEqual(occurrences, [
                ("bin/battle/ai_script/sample.amx", "GetCaptureResult", "utf-16le", 0),
                ("bin/message/English/common/sample.dat", "CaptureCall", "ascii", 2),
                ("member-without-extension", "CaptureCall", "utf-16be", 2),
            ])
            self.assertTrue(all(len(row["source_sha256"]) == 64 for row in report["matches"]))

    def test_rejects_a_different_main_build(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            make_sample(root / "project", root / "romfs")
            with self.assertRaisesRegex(ValueError, "expected LGPE Pikachu 1.0.2 main"):
                build_capture_api_resource_search(
                    root / "project", root / "romfs", main_sha256="0" * 64
                )

    def test_cli_writes_structured_report_from_local_project_layout(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            project = root / "project"
            game_root = root / "game"
            nca = game_root / "1.0.2/2b7730a9e56498bbafac2002d4908c6b_NCA"
            romfs = nca / "1"
            exefs = nca / "0"
            exefs.mkdir(parents=True)
            (exefs / "main").write_bytes(b"sample main; hash is patched below")
            make_sample(project, romfs)
            output = project / "manifests/capture-api-resource-search.json"

            with patch.object(cli, "PROJECT", project), patch.object(
                cli, "sha256", return_value=MAIN_SHA256
            ):
                result = cli.main([
                    "capture-api-resource-search",
                    "--root", str(game_root),
                    "--output", str(output),
                ])

            self.assertEqual(result, 0)
            encoded = output.read_bytes()
            self.assertNotIn(b"\r", encoded)
            report = json.loads(encoded.decode("utf-8"))
            self.assertEqual(report["build"]["main_sha256"], MAIN_SHA256)
            self.assertEqual(report["search"]["files_scanned"], 3)
            self.assertEqual(len(report["search"]["source_files"]), 3)
            self.assertEqual(report["status"], "LITERAL_REFERENCE_CANDIDATE")


if __name__ == "__main__":
    unittest.main()
