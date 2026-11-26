import csv
import json
import tempfile
import unittest
from pathlib import Path

from lgpe_research.bnk_batch import run_bnk_batch
from lgpe_research.core import NCA, VERSION, source_dirs


class BnkBatchTests(unittest.TestCase):
    def make_project(self, temp: Path, signature: str = "Wwise BKHD"):
        project = temp / "project"
        project.mkdir()
        root = temp / "game"
        source = source_dirs(root)["romfs"] / "bin" / "sound" / "test.bnk"
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_bytes(b"BKHD" + bytes(range(64)))
        catalog = project / "manifests" / "files.csv"
        catalog.parent.mkdir(parents=True)
        with catalog.open("w", newline="", encoding="utf-8-sig") as stream:
            writer = csv.DictWriter(
                stream,
                fieldnames=[
                    "partition", "relative_path", "suffix", "kind",
                    "bytes", "signature", "header_hex", "sha256",
                ],
            )
            writer.writeheader()
            writer.writerow({
                "partition": "romfs",
                "relative_path": "bin/sound/test.bnk",
                "suffix": ".bnk",
                "kind": "file",
                "bytes": source.stat().st_size,
                "signature": signature,
                "header_hex": source.read_bytes()[:16].hex(),
                "sha256": "",
            })
        return root, project, source

    def test_dry_run_preserves_one_to_one_xml_path(self):
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            root, project, source = self.make_project(temp)
            result = run_bnk_batch(root, project, limit=1, execute=False)
            row = json.loads((project / "manifests" / "bnk.jsonl").read_text(encoding="utf-8"))
            self.assertEqual(result["selected"], 1)
            self.assertEqual(row["status"], "DRY_RUN")
            self.assertEqual(
                row["output"],
                str(Path("decoded") / VERSION / "romfs" / "bin" / "sound" / "test.xml"),
            )
            self.assertEqual(source.read_bytes()[:4], b"BKHD")

    def test_actual_xml_decode_is_validated_and_receipted(self):
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            root, project, source = self.make_project(temp)
            tool = project / "tools" / "src" / "wwiser" / "wwiser.py"
            tool.parent.mkdir(parents=True)
            tool.write_text(
                "import pathlib, sys\nargs = sys.argv\nname = pathlib.Path(args[args.index('-dn') + 1])\nname.with_suffix('.xml').write_text('<root><Bank/></root>', encoding='utf-8')\n",
                encoding="utf-8",
            )
            before = source.read_bytes()
            result = run_bnk_batch(root, project, limit=1, execute=True)
            manifest_row = json.loads((project / "manifests" / "bnk.jsonl").read_text(encoding="utf-8"))
            output = project / manifest_row["output"]
            receipt = json.loads((project / "manifests" / "outputs.jsonl").read_text(encoding="utf-8"))
            self.assertEqual(result["decoded"], 1)
            self.assertEqual(manifest_row["status"], "DECODED")
            self.assertEqual(manifest_row["validation"]["root"], "root")
            self.assertTrue(output.is_file())
            self.assertEqual(source.read_bytes(), before)
            self.assertEqual(receipt["relative_source"], "bin/sound/test.bnk")
            self.assertEqual(Path(receipt["output_file"]), output)
            self.assertEqual(receipt["output_sha256"], manifest_row["output_sha256"])


    def test_full_run_uses_wwiser_config_and_preserves_mirror(self):
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            root, project, source = self.make_project(temp)
            tool = project / "tools" / "src" / "wwiser" / "wwiser.py"
            tool.parent.mkdir(parents=True)
            tool.write_text(
                "import pathlib, shlex, sys\n"
                "config = pathlib.Path(sys.argv[1])\n"
                "for line in config.read_text(encoding='utf-8').splitlines():\n"
                "    if line.startswith('#'): continue\n"
                "    args = shlex.split(line)\n"
                "    output = pathlib.Path(args[args.index('-dn') + 1]).with_suffix('.xml')\n"
                "    output.write_text('<root><Bank/></root>', encoding='utf-8')\n",
                encoding="utf-8",
            )
            result = run_bnk_batch(root, project, limit=0, execute=True)
            row = json.loads((project / "manifests" / "bnk.jsonl").read_text(encoding="utf-8"))
            self.assertEqual(result["selected"], 1)
            self.assertEqual(result["decoded"], 1)
            self.assertEqual(row["status"], "DECODED")
            self.assertEqual(row["output"], str(Path("decoded") / VERSION / "romfs" / "bin" / "sound" / "test.xml"))
            self.assertTrue((project / row["output"]).is_file())


if __name__ == "__main__":
    unittest.main()
