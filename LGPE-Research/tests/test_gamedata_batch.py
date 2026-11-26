import csv
import json
import shutil
import struct
import sys
import tempfile
import unittest
from pathlib import Path

from lgpe_research.batch import run_gamedata_batch
from lgpe_research.core import NCA, VERSION


class GameDataBatchTests(unittest.TestCase):
    def test_zukan_sort_sample_decodes_u16_rows_to_mirrored_json(self):
        source_rel = "bin/app/zukan_data/bin/zukan_sort_zenkoku.bin"
        data = struct.pack("<4H", 1, 311, 767, 0xffff)
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            root = tmp_path / "game"
            project = tmp_path / "project"
            source = root / VERSION / NCA / "1" / Path(source_rel)
            source.parent.mkdir(parents=True)
            source.write_bytes(data)

            catalog = project / "manifests" / "files.csv"
            catalog.parent.mkdir(parents=True)
            with catalog.open("w", encoding="utf-8-sig", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=[
                    "partition", "relative_path", "suffix", "kind", "bytes",
                    "signature", "header_hex", "sha256",
                ])
                writer.writeheader()
                writer.writerow({
                    "partition": "romfs", "relative_path": source_rel,
                    "suffix": ".bin", "kind": "binary-unknown",
                    "bytes": len(data), "signature": "unidentified",
                    "header_hex": data[:16].hex(), "sha256": "",
                })

            summary = run_gamedata_batch(
                root=root, project=project, execute=True,
                only_sources={source_rel},
            )

            output = project / "decoded" / VERSION / "romfs" / Path(source_rel).with_suffix(".json")
            decoded = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(decoded["entries"][1]["value_u16le"], 311)
            self.assertEqual(bytes.fromhex(decoded["raw_hex"]), data)
            self.assertEqual(summary["pknx_record_groups"]["zukan_sort"]["decoded"], 1)
            self.assertEqual(summary["decoded_outputs"], 1)
            rows = [
                json.loads(line)
                for line in (project / "manifests" / "gamedata.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            record = next(row for row in rows if row.get("source") == source_rel)
            self.assertEqual(record["status"], "DECODED")
            self.assertEqual(record["output"], str(output.relative_to(project)))

    def test_unlabeled_personal_monsname_decodes_with_pokedat_provenance(self):
        source_rel = "bin/pokelib/personal/monsname.dat"
        checkout = Path(__file__).resolve().parents[1] / "tools/src/pokedat"
        sys.path.insert(0, str(checkout))
        try:
            from text_file import TextFile
            from text_config import TextConfig

            data = bytes(TextFile.from_lines(["A", "B"], [0, 0], TextConfig("LGPE")).data)
        finally:
            sys.path.remove(str(checkout))

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            root = tmp_path / "game"
            project = tmp_path / "project"
            source = root / VERSION / NCA / "1" / Path(source_rel)
            source.parent.mkdir(parents=True)
            source.write_bytes(data)
            pokedat = project / "tools/src/pokedat"
            pokedat.mkdir(parents=True)
            shutil.copy2(checkout / "text_file.py", pokedat / "text_file.py")
            shutil.copy2(checkout / "text_config.py", pokedat / "text_config.py")

            catalog = project / "manifests/files.csv"
            catalog.parent.mkdir(parents=True)
            with catalog.open("w", encoding="utf-8-sig", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=[
                    "partition", "relative_path", "suffix", "kind", "bytes",
                    "signature", "header_hex", "sha256",
                ])
                writer.writeheader()
                writer.writerow({
                    "partition": "romfs", "relative_path": source_rel,
                    "suffix": ".dat", "kind": "data-unknown",
                    "bytes": len(data), "signature": "unidentified",
                    "header_hex": data[:16].hex(), "sha256": "",
                })

            summary = run_gamedata_batch(
                root=root, project=project, execute=True,
                only_sources={source_rel},
            )

            output = project / "decoded" / VERSION / "romfs" / Path(source_rel).with_suffix(".json")
            self.assertTrue(output.is_file())
            decoded = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(decoded["format"], "LGPE-unlabeled-message")
            self.assertEqual(decoded["entries"], [
                {"index": 0, "text": "A"}, {"index": 1, "text": "B"},
            ])
            self.assertEqual(bytes.fromhex(decoded["raw_hex"]), data)
            self.assertEqual(summary["pknx_record_groups"]["unlabeled_monsname"]["decoded"], 1)
            self.assertEqual(summary["decoded_outputs"], 1)
            rows = [
                json.loads(line)
                for line in (project / "manifests/gamedata.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            record = next(row for row in rows if row.get("source") == source_rel)
            self.assertEqual(record["status"], "DECODED")
            self.assertEqual(record["tool_versions"]["pokedat"], "bd423b2cad9aa852fddb796bbba3c5e7b381289b")

    def test_grammar_dat_decodes_to_a_mirrored_json_with_receipt(self):
        source_rel = "bin/message/grammar/English.dat"
        data = bytearray(24)
        data[:2] = bytes((2, 3))
        struct.pack_into("<HH", data, 2, 12, 20)
        data[6:12] = bytes.fromhex("010203040506")
        data[12:20] = "A\0B\0".encode("utf-16-le")
        data[20:24] = "x\0".encode("utf-16-le")
        data = bytes(data)
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            root = tmp_path / "game"
            project = tmp_path / "project"
            source = root / VERSION / NCA / "1" / Path(source_rel)
            source.parent.mkdir(parents=True)
            source.write_bytes(data)

            catalog = project / "manifests" / "files.csv"
            catalog.parent.mkdir(parents=True)
            with catalog.open("w", encoding="utf-8-sig", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=[
                    "partition", "relative_path", "suffix", "kind", "bytes",
                    "signature", "header_hex", "sha256",
                ])
                writer.writeheader()
                writer.writerow({
                    "partition": "romfs", "relative_path": source_rel,
                    "suffix": ".dat", "kind": "data-unknown",
                    "bytes": len(data), "signature": "unidentified",
                    "header_hex": data[:16].hex(), "sha256": "",
                })

            summary = run_gamedata_batch(
                root=root, project=project, execute=True,
                only_sources={source_rel},
            )

            output = project / "decoded" / VERSION / "romfs" / Path(source_rel).with_suffix(".json")
            self.assertTrue(output.is_file())
            decoded = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(bytes.fromhex(decoded["raw_hex"]), data)
            self.assertEqual(decoded["entries"][0]["utf16le_strings"], ["A", "B"])
            self.assertEqual(summary["decoded_outputs"], 1)
            self.assertEqual(summary["failed"], 0)
            rows = [
                json.loads(line)
                for line in (project / "manifests" / "gamedata.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            record = next(row for row in rows if row.get("source") == source_rel)
            self.assertEqual(record["status"], "DECODED")
            receipts = [
                json.loads(line)
                for line in (project / "manifests" / "outputs.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            receipt = next(row for row in receipts if row.get("relative_source") == source_rel)
            self.assertEqual(receipt["source_sha256"], record["source_sha256"])
            self.assertEqual(receipt["output_sha256"], record["output_sha256"])

    def test_battle_pocket_is_decoded_once_with_crosscheck_provenance(self):
        source_rel = "bin/pokelib/item/battle_pocket.dat"
        data = bytes((index * 7) & 0x1F for index in range(0x422))
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            root = tmp_path / "game"
            project = tmp_path / "project"
            source = root / VERSION / NCA / "1" / Path(source_rel)
            source.parent.mkdir(parents=True)
            source.write_bytes(data)

            catalog = project / "manifests" / "files.csv"
            catalog.parent.mkdir(parents=True)
            with catalog.open("w", encoding="utf-8-sig", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=[
                    "partition", "relative_path", "suffix", "kind", "bytes",
                    "signature", "header_hex", "sha256",
                ])
                writer.writeheader()
                writer.writerow({
                    "partition": "romfs", "relative_path": source_rel,
                    "suffix": ".dat", "kind": "data-unknown",
                    "bytes": len(data), "signature": "unidentified",
                    "header_hex": data[:16].hex(), "sha256": "",
                })

            summary = run_gamedata_batch(
                root=root, project=project, execute=True,
                only_sources={source_rel},
            )

            output = project / "decoded" / VERSION / "romfs" / Path(source_rel).with_suffix(".json")
            decoded = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(bytes.fromhex(decoded["raw_hex"]), data)
            self.assertEqual(summary["pknx_record_groups"]["battle_pocket"]["decoded"], 1)
            self.assertEqual(summary["pknx_record_groups"]["items"]["unknown"], 0)
            rows = [
                json.loads(line)
                for line in (project / "manifests" / "gamedata.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            matching = [row for row in rows if row.get("source") == source_rel]
            self.assertEqual(len(matching), 1)
            self.assertEqual(matching[0]["status"], "DECODED")
            self.assertEqual(matching[0]["tool_versions"]["pkNX"], "d191cd0e5c05f2af81d9a41c1f1d82e6621b351a")

    def test_field_pocket_source_is_decoded_to_a_mirrored_json_with_receipt(self):
        source_rel = "bin/pokelib/item/field_pocket.dat"
        data = bytes((index * 13) & 0xFF for index in range(0x422))
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            root = tmp_path / "game"
            project = tmp_path / "project"
            source = root / VERSION / NCA / "1" / Path(source_rel)
            source.parent.mkdir(parents=True)
            source.write_bytes(data)

            catalog = project / "manifests" / "files.csv"
            catalog.parent.mkdir(parents=True)
            with catalog.open("w", encoding="utf-8-sig", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=[
                    "partition", "relative_path", "suffix", "kind", "bytes",
                    "signature", "header_hex", "sha256",
                ])
                writer.writeheader()
                writer.writerow({
                    "partition": "romfs", "relative_path": source_rel,
                    "suffix": ".dat", "kind": "data-unknown",
                    "bytes": len(data), "signature": "unidentified",
                    "header_hex": data[:16].hex(), "sha256": "",
                })

            summary = run_gamedata_batch(
                root=root, project=project, execute=True,
                only_sources={source_rel},
            )

            output = project / "decoded" / VERSION / "romfs" / Path(source_rel).with_suffix(".json")
            self.assertTrue(output.is_file())
            decoded = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(bytes.fromhex(decoded["raw_hex"]), data)
            self.assertEqual(summary["pknx_record_groups"]["field_pocket"]["decoded"], 1)
            manifest_rows = [
                json.loads(line)
                for line in (project / "manifests" / "gamedata.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            row = next(row for row in manifest_rows if row.get("source") == source_rel)
            self.assertEqual(row["status"], "DECODED")
            self.assertEqual(row["output"], str(output.relative_to(project)))

    def test_item_hash_table_uses_exact_main_reader_and_preserves_source(self):
        source_rel = "bin/pokelib/item/item_hash_to_index.dat"
        data = (
            struct.pack("<I", 3)
            + struct.pack("<QQ", 0xAABBCCDDEEFF0011, 1)
            + struct.pack("<QQ", 0x1234567890ABCDEF, 7)
            + struct.pack("<QQ", 0x0102030405060708, 8)
        )
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            root = tmp_path / "game"
            project = tmp_path / "project"
            source = root / VERSION / NCA / "1" / Path(source_rel)
            source.parent.mkdir(parents=True)
            source.write_bytes(data)

            catalog = project / "manifests" / "files.csv"
            catalog.parent.mkdir(parents=True)
            with catalog.open("w", encoding="utf-8-sig", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=[
                    "partition", "relative_path", "suffix", "kind", "bytes",
                    "signature", "header_hex", "sha256",
                ])
                writer.writeheader()
                writer.writerow({
                    "partition": "romfs", "relative_path": source_rel,
                    "suffix": ".dat", "kind": "data-unknown",
                    "bytes": len(data), "signature": "unidentified",
                    "header_hex": data[:16].hex(), "sha256": "",
                })

            summary = run_gamedata_batch(
                root=root, project=project, execute=True,
                only_sources={source_rel},
            )

            self.assertEqual(summary["decoded_outputs"], 1)
            self.assertEqual(summary["failed"], 0)
            self.assertEqual(summary["pknx_record_groups"]["items"]["unknown"], 0)
            rows = [
                json.loads(line)
                for line in (project / "manifests" / "gamedata.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            row = next(row for row in rows if row.get("source") == source_rel)
            self.assertEqual(row["status"], "DECODED")
            self.assertEqual(row["count"], 3)
            output = project / "decoded" / VERSION / "romfs" / Path(source_rel).with_suffix(".json")
            self.assertTrue(output.is_file())
            decoded = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(bytes.fromhex(decoded["raw_hex"]), data)
            self.assertEqual(decoded["entries"][1]["loader_value_u16"], 7)
            receipt_rows = [
                json.loads(line)
                for line in (project / "manifests" / "outputs.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            receipt = next(item for item in receipt_rows if item.get("relative_source") == source_rel)
            self.assertEqual(receipt["source_sha256"], row["source_sha256"])
            self.assertEqual(receipt["output_sha256"], row["output_sha256"])


if __name__ == "__main__":
    unittest.main()
