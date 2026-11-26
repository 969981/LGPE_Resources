import csv
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from lgpe_research.asset_batch import run_asset_batch
from lgpe_research.assets_decode import validate_output, write_png_rgba


class AssetBatchCatalogTests(unittest.TestCase):
    def test_texture_dry_run_mirrors_one_to_one_and_marks_unknown_magic(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            game = base / "game"
            romfs = game / "1.0.2" / "2b7730a9e56498bbafac2002d4908c6b_NCA" / "1"
            project = base / "LGPE-Research"
            source = romfs / "bin" / "app" / "report" / "sample.bntx"
            unknown = romfs / "bin" / "app" / "report" / "unknown.bntx"
            source.parent.mkdir(parents=True)
            source.write_bytes(b"BNTX" + b"\0" * 16)
            unknown.write_bytes(b"NOPE" + b"\0" * 16)
            manifest = project / "manifests" / "files.csv"
            manifest.parent.mkdir(parents=True)
            fields = ["partition", "relative_path", "suffix", "kind", "bytes", "signature", "header_hex", "sha256"]
            with manifest.open("w", encoding="utf-8-sig", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=fields)
                writer.writeheader()
                writer.writerow({
                    "partition": "romfs", "relative_path": "bin/app/report/sample.bntx",
                    "suffix": ".bntx", "kind": "texture", "bytes": source.stat().st_size,
                    "signature": "BNTX", "header_hex": "42544e58", "sha256": "",
                })
                writer.writerow({
                    "partition": "romfs", "relative_path": "bin/app/report/unknown.bntx",
                    "suffix": ".bntx", "kind": "texture", "bytes": unknown.stat().st_size,
                    "signature": "unidentified", "header_hex": "4e4f5045", "sha256": "",
                })

            summary = run_asset_batch("texture", game, project, limit=20, execute=False)
            rows = [json.loads(line) for line in (project / "manifests" / "textures.jsonl").read_text().splitlines()]

            self.assertEqual(summary["catalogued"], 2)
            self.assertEqual(summary["compatible"], 1)
            self.assertEqual(summary["selected"], 1)
            self.assertEqual(summary["unknown"], 1)
            by_source = {row["source"]: row for row in rows}
            self.assertEqual(by_source["bin/app/report/sample.bntx"]["status"], "DRY_RUN")
            self.assertEqual(
                Path(by_source["bin/app/report/sample.bntx"]["output"]).as_posix(),
                "decoded/1.0.2/romfs/bin/app/report/sample.png",
            )
            self.assertEqual(by_source["bin/app/report/unknown.bntx"]["status"], "UNKNOWN")
            self.assertFalse((project / "decoded").exists())

    def test_existing_verified_output_preserves_conversion_provenance(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            game = base / "game"
            romfs = game / "1.0.2" / "2b7730a9e56498bbafac2002d4908c6b_NCA" / "1"
            project = base / "LGPE-Research"
            rel = "bin/app/report/sample.bntx"
            source = romfs / Path(rel)
            source.parent.mkdir(parents=True)
            source.write_bytes(b"BNTX" + b"\0" * 16)
            output = project / "decoded" / "1.0.2" / "romfs" / Path(rel).with_suffix(".png")
            output.parent.mkdir(parents=True)
            write_png_rgba(output, 1, 1, b"\x7f\x7f\x7f\xff")
            def digest(path):
                with path.open("rb") as stream:
                    return hashlib.file_digest(stream, "sha256").hexdigest()
            conversion = {
                "pixel_format": "R16_UNORM",
                "decoder": "BNTX-Extractor swizzle.deswizzle + R16_UNORM normalization",
                "source_format_code": 2561,
            }
            command = [{"command": ["decoder", "sample.bntx"], "returncode": 0}]
            prior = {
                "domain": "texture", "source": rel, "source_bytes": source.stat().st_size,
                "signature": "BNTX", "output": str(output.relative_to(project)),
                "source_sha256": digest(source), "output_sha256": digest(output),
                "output_bytes": output.stat().st_size, "status": "DECODED",
                "conversion": conversion, "tool_versions": {"BNTX-Extractor": "pinned"},
                "commands": command, "validation": validate_output(output),
            }
            manifest = project / "manifests" / "files.csv"
            manifest.parent.mkdir(parents=True)
            fields = ["partition", "relative_path", "suffix", "kind", "bytes", "signature", "header_hex", "sha256"]
            with manifest.open("w", encoding="utf-8-sig", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=fields)
                writer.writeheader()
                writer.writerow({
                    "partition": "romfs", "relative_path": rel, "suffix": ".bntx",
                    "kind": "texture", "bytes": source.stat().st_size,
                    "signature": "BNTX", "header_hex": "42544e58", "sha256": digest(source),
                })
            (project / "manifests" / "textures.jsonl").write_text(json.dumps(prior) + "\n", encoding="utf-8")

            summary = run_asset_batch("texture", game, project, execute=True)
            current = json.loads((project / "manifests" / "textures.jsonl").read_text(encoding="utf-8").splitlines()[0])
            self.assertEqual(summary["decoded"], 1)
            self.assertEqual(current["status"], "DECODED_EXISTING_VERIFIED")
            self.assertEqual(current["conversion"], conversion)
            self.assertEqual(current["tool_versions"], prior["tool_versions"])
            self.assertEqual(current["commands"], command)
            self.assertEqual(current["validation"], prior["validation"])


if __name__ == "__main__":
    unittest.main()
