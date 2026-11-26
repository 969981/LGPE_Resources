from __future__ import annotations

import csv
import json
import struct
import tempfile
import unittest
from contextlib import redirect_stdout
from hashlib import sha256
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from lgpe_research import assets_decode, cli
from lgpe_research.bffnt_decode import NX_FFNT_VERSION, parse_bffnt
from lgpe_research.bffnt_batch import run_bffnt_batch
from lgpe_research.batch import verify_outputs
from lgpe_research.coverage import build_coverage


def bffnt_fixture(sheet: bytes = b"BNTX" + b"\0" * 12) -> bytes:
    header_size = 20
    finf_start = header_size
    tglp_start = finf_start + 32
    sheet_offset = 128
    tglp_end = sheet_offset + len(sheet)
    cwdh_start = tglp_end
    cmap_start = cwdh_start + 20
    file_size = cmap_start + 28

    finf = b"FINF" + struct.pack(
        "<I", 32,
    ) + struct.pack(
        "<BBBBHHBBBBIII",
        2, 8, 8, 7, 8, 0, 0, 8, 8, 1,
        tglp_start + 8, cwdh_start + 8, cmap_start + 8,
    )
    tglp_payload = struct.pack(
        "<BBBBIHHHHHHI",
        8, 8, 1, 8, len(sheet), 6, 12, 1, 1, 4, 4, sheet_offset,
    )
    filler = b"\0" * (sheet_offset - (tglp_start + 32))
    tglp = b"TGLP" + struct.pack("<I", tglp_end - tglp_start) + tglp_payload + filler + sheet
    cwdh = (
        b"CWDH" + struct.pack("<IHHI", 20, 0, 0, 0)
        + struct.pack("<bBB", 0, 4, 4) + b"\0"
    )
    cmap = (
        b"CMAP" + struct.pack("<I", 28)
        + struct.pack("<IIHHI", 32, 32, 0, 0, 0)
        + struct.pack("<H", 0) + b"\0\0"
    )
    body = finf + tglp + cwdh + cmap
    header = b"FFNT\xff\xfe" + struct.pack(
        "<HIIHH", header_size, NX_FFNT_VERSION, file_size, 4, 0,
    )
    result = header + body
    assert len(result) == file_size
    return result


class BffntParserTests(unittest.TestCase):
    def test_parses_nx_sections_glyph_width_and_direct_map(self):
        data = bffnt_fixture()
        report, sheets = parse_bffnt(data)

        self.assertEqual(report["format"], "NintendoWare NX FFNT/BFFNT")
        self.assertEqual(report["header"]["declared_file_size"], len(data))
        self.assertEqual(
            [section["signature"] for section in report["sections"]],
            ["FINF", "TGLP", "CWDH", "CMAP"],
        )
        self.assertEqual(report["font_info"]["character_encoding"], "Unicode")
        self.assertEqual(report["character_width_sections"][0]["entries"][0], {
            "glyph_index": 0, "left": 0, "glyph_width": 4, "char_width": 4,
        })
        self.assertEqual(report["character_map_sections"][0]["mapping"]["glyph_offset"], 0)
        self.assertEqual(len(sheets), 1)
        self.assertEqual(sheets[0], b"BNTX" + b"\0" * 12)

    def test_rejects_truncated_and_wrong_version_headers(self):
        with self.assertRaisesRegex(ValueError, "20-byte"):
            parse_bffnt(b"FFNT")
        data = bytearray(bffnt_fixture())
        struct.pack_into("<I", data, 8, NX_FFNT_VERSION + 1)
        with self.assertRaisesRegex(NotImplementedError, "version"):
            parse_bffnt(bytes(data))

    def test_rejects_sheet_data_outside_tglp_section(self):
        data = bytearray(bffnt_fixture())
        struct.pack_into("<I", data, 52 + 28, 0x10000)
        with self.assertRaisesRegex(ValueError, "sheet-data offset"):
            parse_bffnt(bytes(data))

    def test_rejects_cyclic_cmap_chain(self):
        data = bytearray(bffnt_fixture())
        struct.pack_into("<I", data, 164 + 20, 164 + 8)
        with self.assertRaisesRegex(ValueError, "cyclic CMAP"):
            parse_bffnt(bytes(data))


class BffntBatchTests(unittest.TestCase):
    def make_project(self, base: Path) -> tuple[Path, Path, Path, bytes]:
        game = base / "game"
        romfs = game / "1.0.2" / "2b7730a9e56498bbafac2002d4908c6b_NCA" / "1"
        project = base / "LGPE-Research"
        relative = "bin/font/num_00.bffnt"
        data = bffnt_fixture()
        source = romfs / relative
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_bytes(data)
        manifests = project / "manifests"
        manifests.mkdir(parents=True)
        with (manifests / "files.csv").open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=[
                "partition", "relative_path", "suffix", "kind", "bytes",
                "signature", "header_hex", "sha256",
            ])
            writer.writeheader()
            writer.writerow({
                "partition": "romfs", "relative_path": relative, "suffix": ".bffnt",
                "kind": "font", "bytes": len(data), "signature": "BFFNT",
                "header_hex": data[:16].hex(), "sha256": sha256(data).hexdigest(),
            })
        fake_ffmpeg = base / "ffmpeg.exe"
        fake_ffmpeg.write_bytes(b"test executable fingerprint")
        return game, project, fake_ffmpeg, data

    @staticmethod
    def fake_conversion(source: Path, output: Path, root: Path, ffmpeg: Path, log: list) -> dict:
        if source.read_bytes()[:4] != b"BNTX":
            raise ValueError("expected extracted BNTX")
        assets_decode.write_png_rgba(output, 4, 4, bytes((180, 180, 180, 255)) * 16)
        log.append({
            "command": ["fixture-converter", str(source), str(output)],
            "cwd": str(root / "work"),
            "returncode": 0,
        })
        return {
            "pixel_format": "fixture",
            "decoder": "fixture-only-test-double",
            "width": 4,
            "height": 4,
        }

    def test_batch_exports_json_raw_sheet_png_and_verifiable_receipts(self):
        with tempfile.TemporaryDirectory() as temporary:
            game, project, ffmpeg, source_bytes = self.make_project(Path(temporary))
            source = game / "1.0.2/2b7730a9e56498bbafac2002d4908c6b_NCA/1/bin/font/num_00.bffnt"
            before = sha256(source.read_bytes()).hexdigest()
            with patch("lgpe_research.bffnt_batch.assets_decode.convert_bntx", self.fake_conversion):
                summary = run_bffnt_batch(game, project, limit=0, execute=True, ffmpeg=ffmpeg)

            output_json = project / "decoded/1.0.2/romfs/bin/font/num_00.json"
            contents = output_json.with_name("num_00.bffnt.contents")
            raw_sheet = contents / "Sheet_0.bntx"
            png = contents / "Sheet_0.png"
            report = json.loads(output_json.read_text(encoding="utf-8"))
            self.assertEqual(summary["decoded"], 1)
            self.assertEqual(summary["failed"], 0)
            self.assertEqual(report["source"]["sha256"], before)
            self.assertEqual(report["sections"][-1]["signature"], "CMAP")
            self.assertEqual(raw_sheet.read_bytes(), source_bytes[128:144])
            self.assertTrue(png.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"))
            self.assertEqual(sha256(source.read_bytes()).hexdigest(), before)

            coverage = build_coverage(project)
            with (project / "manifests/coverage.csv").open(encoding="utf-8-sig") as stream:
                cover = next(csv.DictReader(stream))
            self.assertEqual(coverage["decoded_sources"], 1)
            self.assertEqual(cover["analysis_status"], "DECODED")
            self.assertEqual(int(cover["decoded_outputs"]), 3)
            verified = verify_outputs(project, {"bin/font/num_00.bffnt"}, root=game)
            self.assertEqual((verified["registered"], verified["verified"], verified["bad"]), (3, 3, 0))
            first_json_bytes = output_json.read_bytes()
            report_commands = report["texture_glyph"]["sheets"][0].get("commands")
            self.assertIsNone(report_commands)
            legacy_report = json.loads(first_json_bytes)
            legacy_report["texture_glyph"]["sheets"][0]["commands"] = [{
                "command": ["fixture-converter", str(Path(temporary) / "random-staging-path")],
                "cwd": str(Path(temporary) / "random-work-path"),
                "returncode": 0,
            }]
            output_json.write_text(
                json.dumps(legacy_report, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
                newline="\n",
            )

            with patch("lgpe_research.bffnt_batch.assets_decode.convert_bntx", self.fake_conversion):
                repeated = run_bffnt_batch(game, project, limit=0, execute=True, ffmpeg=ffmpeg)
            self.assertEqual((repeated["decoded"], repeated["failed"]), (1, 0))
            self.assertEqual(output_json.read_bytes(), first_json_bytes)
            batch_row = json.loads((project / "manifests/bffnt.jsonl").read_text(encoding="utf-8"))
            self.assertTrue(batch_row["normalized_legacy_command_log"])
            self.assertIn("fixture-converter", json.dumps(batch_row["commands"]))
            self.assertEqual(len((project / "manifests/outputs.jsonl").read_text().splitlines()), 3)

    def test_conflicting_png_is_preserved_and_batch_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            game, project, ffmpeg, _source = self.make_project(Path(temporary))
            png = project / "decoded/1.0.2/romfs/bin/font/num_00.bffnt.contents/Sheet_0.png"
            png.parent.mkdir(parents=True)
            png.write_bytes(b"unattributed conflicting file")
            with patch("lgpe_research.bffnt_batch.assets_decode.convert_bntx", self.fake_conversion):
                summary = run_bffnt_batch(game, project, limit=0, execute=True, ffmpeg=ffmpeg)
            self.assertEqual(summary["failed"], 1)
            self.assertEqual(png.read_bytes(), b"unattributed conflicting file")
            self.assertFalse((project / "decoded/1.0.2/romfs/bin/font/num_00.json").exists())

    def test_cli_dispatches_bffnt_batch(self):
        with tempfile.TemporaryDirectory() as temporary:
            game = Path(temporary) / "game"
            project = Path(temporary) / "project"
            result = {"failed": 0, "decoded": 1}
            stdout = StringIO()
            with (
                patch("lgpe_research.cli.PROJECT", project),
                patch("lgpe_research.cli.run_bffnt_batch", return_value=result) as batch,
                redirect_stdout(stdout),
            ):
                status = cli.main(["decode-bffnt", "--root", str(game), "--limit", "0", "--execute"])
            self.assertEqual(status, 0)
            batch.assert_called_once()
            self.assertEqual(json.loads(stdout.getvalue()), result)


if __name__ == "__main__":
    unittest.main()
