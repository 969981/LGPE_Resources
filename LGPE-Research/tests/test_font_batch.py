from __future__ import annotations

import csv
import json
import os
import struct
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from hashlib import sha256
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from lgpe_research import cli, font_batch
from lgpe_research.batch import verify_outputs
from lgpe_research.font_batch import run_font_batch
from lgpe_research.coverage import build_coverage


KEY = 1231165446


def opentype_fixture() -> bytes:
    font = b"OTTO" + struct.pack(">HHHH", 1, 0, 0, 0)
    return font + struct.pack(">4sIII", b"name", 0, 28, 4) + b"FONT"


def bfotf_fixture() -> bytes:
    font = opentype_fixture()
    payload = b"".join(
        (int.from_bytes(font[offset:offset + 4], "big") ^ KEY).to_bytes(4, "big")
        for offset in range(0, len(font), 4)
    )
    return (0x1E1AF836).to_bytes(4, "little") + (len(font) ^ KEY).to_bytes(4, "big") + payload


class FontBatchTests(unittest.TestCase):
    def make_project(self, base: Path) -> tuple[Path, Path, dict[str, bytes]]:
        game = base / "game"
        romfs = game / "1.0.2" / "2b7730a9e56498bbafac2002d4908c6b_NCA" / "1"
        project = base / "LGPE-Research"
        inputs = {
            "bin/font/a_font.BFOTF": bfotf_fixture(),
            "bin/font/unknown.BFOTF": b"NOPE" + b"\0" * 28,
        }
        rows = []
        for relative, data in inputs.items():
            source = romfs / Path(relative)
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_bytes(data)
            rows.append({
                "partition": "romfs", "relative_path": relative, "suffix": ".bfotf",
                "kind": "unknown", "bytes": len(data), "signature": "unidentified",
                "header_hex": data[:16].hex(), "sha256": "",
            })
        manifest = project / "manifests" / "files.csv"
        manifest.parent.mkdir(parents=True)
        fields = ["partition", "relative_path", "suffix", "kind", "bytes", "signature", "header_hex", "sha256"]
        with manifest.open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
        return game, project, inputs

    def test_execute_mirrors_otf_outputs_and_records_unknown_magic(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            game, project, _inputs = self.make_project(base)
            source = game / "1.0.2" / "2b7730a9e56498bbafac2002d4908c6b_NCA" / "1" / "bin/font/a_font.BFOTF"
            before = sha256(source.read_bytes()).hexdigest()

            summary = run_font_batch(game, project, limit=0, execute=True)

            output = project / "decoded/1.0.2/romfs/bin/font/a_font.otf"
            self.assertEqual(output.read_bytes(), opentype_fixture())
            self.assertEqual(sha256(source.read_bytes()).hexdigest(), before)
            self.assertEqual(summary["catalogued"], 2)
            self.assertEqual(summary["decoded"], 1)
            self.assertEqual(summary["unknown"], 1)

            rows = [json.loads(line) for line in (project / "manifests/fonts.jsonl").read_text().splitlines()]
            by_source = {row["source"]: row for row in rows}
            row = by_source["bin/font/a_font.BFOTF"]
            self.assertEqual(row["status"], "DECODED")
            self.assertEqual(row["output"], "decoded/1.0.2/romfs/bin/font/a_font.otf")
            self.assertNotIn("\\", row["output"])
            self.assertEqual(row["source_sha256"], before)
            self.assertEqual(row["validation"]["signature"], "OTTO")
            self.assertEqual(by_source["bin/font/unknown.BFOTF"]["status"], "UNKNOWN")

            coverage = build_coverage(project)
            with (project / "manifests/coverage.csv").open(encoding="utf-8-sig") as stream:
                coverage_rows = {row["relative_path"]: row for row in csv.DictReader(stream)}
            self.assertEqual(coverage["decoded_sources"], 1)
            self.assertEqual(coverage_rows["bin/font/a_font.BFOTF"]["analysis_status"], "DECODED")
            self.assertEqual(coverage_rows["bin/font/unknown.BFOTF"]["analysis_status"], "UNKNOWN")

            receipt = json.loads((project / "manifests/outputs.jsonl").read_text().splitlines()[0])
            self.assertEqual(receipt["source_sha256"], before)
            self.assertEqual(receipt["relative_source"], "bin/font/a_font.BFOTF")
            self.assertEqual(receipt["output_file"], str(output))

            with patch("lgpe_research.font_batch.add_receipts") as add_receipts:
                repeated = run_font_batch(game, project, limit=0, execute=True)
            self.assertEqual(repeated["decoded"], 1)
            add_receipts.assert_not_called()

    def test_cli_decode_fonts_runs_the_batch_entrypoint(self):
        with tempfile.TemporaryDirectory() as temporary:
            game, project, _inputs = self.make_project(Path(temporary))
            stdout = StringIO()
            with patch("lgpe_research.cli.PROJECT", project), redirect_stdout(stdout):
                result = cli.main([
                    "decode-fonts", "--root", str(game), "--limit", "1", "--execute",
                ])
            self.assertEqual(result, 0)
            self.assertEqual(json.loads(stdout.getvalue())["decoded"], 1)
            self.assertTrue((project / "decoded/1.0.2/romfs/bin/font/a_font.otf").is_file())

    def test_retry_failed_dispatches_font_sources(self):
        with tempfile.TemporaryDirectory() as temporary:
            game, project, _inputs = self.make_project(Path(temporary))
            failures = project / "manifests/failures.jsonl"
            failures.write_text(json.dumps({
                "domain": "font", "source": "bin/font/a_font.BFOTF",
                "status": "FAILED", "error": "test retry",
            }) + "\n", encoding="utf-8")
            stdout = StringIO()
            with (
                patch("lgpe_research.cli.PROJECT", project),
                patch("lgpe_research.cli.run_font_batch", return_value={"failed": 0}) as run_font,
                patch("lgpe_research.cli.build_coverage", return_value={}),
                redirect_stdout(stdout),
            ):
                result = cli.main([
                    "retry-failed", "--root", str(game), "--domain", "font", "--execute",
                ])
            self.assertEqual(result, 0)
            run_font.assert_called_once()
            args, kwargs = run_font.call_args
            self.assertEqual(args[:4], (game, project, 0, True))
            self.assertEqual(kwargs["only_sources"], {"bin/font/a_font.BFOTF"})

    def test_exclusive_create_race_does_not_delete_competing_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            game, project, _inputs = self.make_project(Path(temporary))
            output = project / "decoded/1.0.2/romfs/bin/font/a_font.otf"
            real_open = Path.open

            def competing_open(path, mode="r", *args, **kwargs):
                if path == output and mode == "xb":
                    output.parent.mkdir(parents=True, exist_ok=True)
                    output.write_bytes(b"written by competing process")
                    raise FileExistsError(output)
                return real_open(path, mode, *args, **kwargs)

            with patch.object(Path, "open", competing_open):
                summary = run_font_batch(game, project, limit=0, execute=True)

            self.assertEqual(summary["failed"], 1)
            self.assertEqual(output.read_bytes(), b"written by competing process")

    def test_unsafe_catalog_path_is_recorded_as_failed(self):
        with tempfile.TemporaryDirectory() as temporary:
            game, project, _inputs = self.make_project(Path(temporary))
            catalog = project / "manifests/files.csv"
            with catalog.open(encoding="utf-8-sig", newline="") as stream:
                rows = list(csv.DictReader(stream))
            rows[0]["relative_path"] = "../escape.BFOTF"
            with catalog.open("w", encoding="utf-8-sig", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)

            summary = run_font_batch(
                game, project, limit=0, execute=True, only_sources={"../escape.BFOTF"},
            )

            self.assertEqual(summary["failed"], 1)
            rows = [
                json.loads(line)
                for line in (project / "manifests/fonts.jsonl").read_text().splitlines()
            ]
            invalid = next(row for row in rows if row["source"] == "../escape.BFOTF")
            self.assertEqual(invalid["status"], "FAILED")
            self.assertIn("unsafe relative source path", invalid["error"])

    def test_output_symlink_escape_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            game, project, _inputs = self.make_project(base)
            outside = base / "outside"
            outside.mkdir()
            output_parent = project / "decoded/1.0.2/romfs/bin/font"
            output_parent.parent.mkdir(parents=True)
            try:
                if os.name == "nt":
                    result = subprocess.run(
                        ["cmd.exe", "/c", "mklink", "/J", str(output_parent), str(outside)],
                        capture_output=True, text=True, check=False,
                    )
                    if result.returncode:
                        self.skipTest("directory junction creation is unavailable on this host")
                else:
                    output_parent.symlink_to(outside, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest("symlink creation is unavailable on this host")

            summary = run_font_batch(
                game, project, limit=0, execute=True,
                only_sources={"bin/font/a_font.BFOTF"},
            )

            self.assertEqual(summary["failed"], 1)
            self.assertFalse((outside / "a_font.otf").exists())

    def test_source_escape_isolated_to_its_catalog_row(self):
        with tempfile.TemporaryDirectory() as temporary:
            game, project, _inputs = self.make_project(Path(temporary))
            romfs = game / "1.0.2" / "2b7730a9e56498bbafac2002d4908c6b_NCA" / "1"
            real_ensure_inside = font_batch.ensure_inside

            def reject_one_source(path, parent):
                if parent == romfs and path.name == "a_font.BFOTF":
                    raise ValueError("path outside allowed directory: fixture escape")
                return real_ensure_inside(path, parent)

            with patch("lgpe_research.font_batch.ensure_inside", side_effect=reject_one_source):
                summary = run_font_batch(game, project, limit=0, execute=True)

            self.assertEqual(summary["failed"], 1)
            self.assertEqual(summary["unknown"], 1)
            rows = [
                json.loads(line)
                for line in (project / "manifests/fonts.jsonl").read_text().splitlines()
            ]
            statuses = {row["source"]: row["status"] for row in rows}
            self.assertEqual(statuses["bin/font/a_font.BFOTF"], "FAILED")
            self.assertEqual(statuses["bin/font/unknown.BFOTF"], "UNKNOWN")

    def test_receipt_is_registered_before_success_manifest(self):
        with tempfile.TemporaryDirectory() as temporary:
            game, project, _inputs = self.make_project(Path(temporary))
            with patch("lgpe_research.font_batch.add_receipts", side_effect=OSError("interrupted")):
                with self.assertRaisesRegex(OSError, "interrupted"):
                    run_font_batch(game, project, limit=1, execute=True)
            self.assertFalse((project / "manifests/fonts.jsonl").exists())

            recovered = run_font_batch(game, project, limit=1, execute=True)
            self.assertEqual(recovered["decoded"], 1)
            row = json.loads((project / "manifests/fonts.jsonl").read_text().splitlines()[0])
            self.assertEqual(row["status"], "DECODED_EXISTING_VERIFIED")
            self.assertTrue(row["recovered_receipt"])
            self.assertTrue((project / "manifests/outputs.jsonl").is_file())

    def test_legacy_success_row_repairs_missing_global_receipt(self):
        with tempfile.TemporaryDirectory() as temporary:
            game, project, _inputs = self.make_project(Path(temporary))
            first = run_font_batch(game, project, limit=1, execute=True)
            self.assertEqual(first["decoded"], 1)

            font_manifest = project / "manifests/fonts.jsonl"
            rows = [json.loads(line) for line in font_manifest.read_text().splitlines()]
            rows[0].pop("receipt_registered", None)
            font_manifest.write_text(
                "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8",
            )
            (project / "manifests/outputs.jsonl").unlink()

            recovered = run_font_batch(game, project, limit=1, execute=True)

            self.assertEqual(recovered["decoded"], 1)
            rows = [json.loads(line) for line in font_manifest.read_text().splitlines()]
            row = next(row for row in rows if row["source"] == "bin/font/a_font.BFOTF")
            self.assertEqual(row["status"], "DECODED_EXISTING_VERIFIED")
            self.assertTrue(row["receipt_registered"])
            self.assertTrue(row["recovered_receipt"])
            self.assertTrue((project / "manifests/outputs.jsonl").is_file())

    def test_receipt_from_another_project_root_is_rebuilt(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            game, project, _inputs = self.make_project(base)
            run_font_batch(game, project, limit=1, execute=True)

            font_manifest = project / "manifests/fonts.jsonl"
            font_rows = [json.loads(line) for line in font_manifest.read_text().splitlines()]
            font_rows[0].pop("receipt_registered", None)
            font_manifest.write_text(
                "".join(json.dumps(row) + "\n" for row in font_rows), encoding="utf-8",
            )
            outputs_manifest = project / "manifests/outputs.jsonl"
            receipts = [json.loads(line) for line in outputs_manifest.read_text().splitlines()]
            old_output = Path(receipts[0]["output_file"])
            other_project = base / "other-project"
            receipts[0]["output_file"] = str(
                other_project / old_output.relative_to(project)
            )
            outputs_manifest.write_text(
                "".join(json.dumps(row) + "\n" for row in receipts), encoding="utf-8",
            )

            repaired = run_font_batch(game, project, limit=1, execute=True)

            self.assertEqual(repaired["decoded"], 1)
            receipts = [json.loads(line) for line in outputs_manifest.read_text().splitlines()]
            font_receipts = [
                row for row in receipts
                if row.get("relative_source") == "bin/font/a_font.BFOTF"
            ]
            self.assertEqual(len(font_receipts), 1)
            self.assertEqual(Path(font_receipts[0]["output_file"]), project / "decoded/1.0.2/romfs/bin/font/a_font.otf")
            verified = verify_outputs(project, {"bin/font/a_font.BFOTF"}, root=game)
            self.assertEqual((verified["verified"], verified["bad"]), (1, 0))

    def test_valid_but_conflicting_existing_font_is_not_adopted(self):
        with tempfile.TemporaryDirectory() as temporary:
            game, project, _inputs = self.make_project(Path(temporary))
            output = project / "decoded/1.0.2/romfs/bin/font/a_font.otf"
            output.parent.mkdir(parents=True)
            conflicting = opentype_fixture()[:-4] + b"DIFF"
            output.write_bytes(conflicting)

            summary = run_font_batch(
                game, project, limit=0, execute=True,
                only_sources={"bin/font/a_font.BFOTF"},
            )

            self.assertEqual(summary["failed"], 1)
            self.assertEqual(output.read_bytes(), conflicting)
            row = json.loads((project / "manifests/fonts.jsonl").read_text().splitlines()[0])
            self.assertEqual(row["status"], "FAILED")

    def test_partial_write_failure_removes_only_the_created_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            game, project, _inputs = self.make_project(Path(temporary))
            output = project / "decoded/1.0.2/romfs/bin/font/a_font.otf"
            real_open = Path.open

            class FailingWriter:
                def __init__(self, stream):
                    self.stream = stream

                def __enter__(self):
                    self.stream.__enter__()
                    return self

                def __exit__(self, exc_type, exc, traceback):
                    return self.stream.__exit__(exc_type, exc, traceback)

                def fileno(self):
                    return self.stream.fileno()

                def write(self, data):
                    self.stream.write(data[:4])
                    raise OSError("simulated write failure")

                def flush(self):
                    return self.stream.flush()

            def failing_open(path, mode="r", *args, **kwargs):
                stream = real_open(path, mode, *args, **kwargs)
                if path == output and mode == "xb":
                    return FailingWriter(stream)
                return stream

            with patch.object(Path, "open", failing_open):
                summary = run_font_batch(
                    game, project, limit=0, execute=True,
                    only_sources={"bin/font/a_font.BFOTF"},
                )

            self.assertEqual(summary["failed"], 1)
            self.assertFalse(output.exists())

    def test_source_resolution_loop_isolated_for_selected_and_unselected_rows(self):
        with tempfile.TemporaryDirectory() as temporary:
            game, project, _inputs = self.make_project(Path(temporary))
            romfs = game / "1.0.2" / "2b7730a9e56498bbafac2002d4908c6b_NCA" / "1"
            real_ensure_inside = font_batch.ensure_inside

            def loop_one_source(path, parent):
                if parent == romfs and path.name == "a_font.BFOTF":
                    raise RuntimeError("symlink loop while resolving fixture")
                return real_ensure_inside(path, parent)

            with patch("lgpe_research.font_batch.ensure_inside", side_effect=loop_one_source):
                selected = run_font_batch(
                    game, project, limit=0, execute=True,
                    only_sources={"bin/font/a_font.BFOTF"},
                )
            self.assertEqual(selected["failed"], 1)
            self.assertEqual(selected["unknown"], 0)

            def loop_unselected_source(path, parent):
                if parent == romfs and path.name == "unknown.BFOTF":
                    raise RuntimeError("symlink loop while resolving fixture")
                return real_ensure_inside(path, parent)

            with patch("lgpe_research.font_batch.ensure_inside", side_effect=loop_unselected_source):
                unselected = run_font_batch(game, project, limit=1, execute=True)
            self.assertEqual(unselected["failed"], 0)
            self.assertEqual(unselected["decoded"], 1)
            rows = [json.loads(line) for line in (project / "manifests/fonts.jsonl").read_text().splitlines()]
            pending = next(row for row in rows if row["source"] == "bin/font/unknown.BFOTF")
            self.assertEqual(pending["status"], "PENDING")

    def test_output_resolution_loop_becomes_per_file_failure(self):
        with tempfile.TemporaryDirectory() as temporary:
            game, project, _inputs = self.make_project(Path(temporary))
            decoded = project / "decoded"
            real_ensure_inside = font_batch.ensure_inside

            def loop_output(path, parent):
                if parent == decoded:
                    raise RuntimeError("symlink loop while resolving output")
                return real_ensure_inside(path, parent)

            with patch("lgpe_research.font_batch.ensure_inside", side_effect=loop_output):
                summary = run_font_batch(
                    game, project, limit=0, execute=True,
                    only_sources={"bin/font/a_font.BFOTF"},
                )
            self.assertEqual(summary["failed"], 1)
            self.assertFalse((project / "decoded/1.0.2/romfs/bin/font/a_font.otf").exists())


if __name__ == "__main__":
    unittest.main()
