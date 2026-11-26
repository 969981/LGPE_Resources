import hashlib
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

from lgpe_research.amx_catalog import HEADER
from lgpe_research.amx_decode import (
    GAME_MAIN_SHA256,
    _verify_exact_game_main,
    decode_amx,
    decode_compact_cells,
    validate_game_code,
)
from lgpe_research.core import NCA


def synthetic_amx(cells, *, name="sample.amx"):
    """Build a compact LGPE AMX fixture with an exact-build-accepted code stream."""
    encoded_cells = bytearray()
    for value in cells:
        for groups in range(1, 11):
            if -(1 << (groups * 7 - 1)) <= value < (1 << (groups * 7 - 1)):
                break
        else:
            raise ValueError("fixture value exceeds a 64-bit compact cell")
        packed = value & ((1 << (groups * 7)) - 1)
        parts = [((packed >> ((groups - i - 1) * 7)) & 0x7F) for i in range(groups)]
        for part in parts[:-1]:
            encoded_cells.append(part | 0x80)
        encoded_cells.append(parts[-1])
    body = bytes(encoded_cells)
    cod = 0x70
    dat = cod + len(cells) * 8
    hea = dat
    size = cod + len(body)
    fields = (
        size, 0xF1E1, 10, 10, 4, 12,
        cod, dat, hea, hea + 0x40, cod,
        0x3C, 0x3C, 0x48, 0x48, 0x6C, 0x6C, 0x6C,
    )
    data = bytearray(HEADER.pack(*fields) + b"\0" * (cod - HEADER.size) + body)
    struct.pack_into("<H", data, 0x6C, 0)
    return name, bytes(data)


class CompactCellTests(unittest.TestCase):
    def test_exact_game_validator_requires_matching_local_main_hash(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            nca = root / "1.0.2" / NCA
            (nca / "0").mkdir(parents=True)
            (nca / "1").mkdir()
            with self.assertRaisesRegex(FileNotFoundError, "requires ExeFS main"):
                _verify_exact_game_main(root)

            main = nca / "0" / "main"
            main.write_bytes(b"fixture")
            with patch("lgpe_research.amx_decode.sha256", return_value=GAME_MAIN_SHA256):
                self.assertEqual(_verify_exact_game_main(root), GAME_MAIN_SHA256)
            with patch("lgpe_research.amx_decode.sha256", return_value="0" * 64):
                with self.assertRaisesRegex(ValueError, "local main has"):
                    _verify_exact_game_main(root)

    def test_decodes_signed_big_endian_seven_bit_groups(self):
        # 63, -1, -64, 128, and -65 respectively.
        self.assertEqual(
            decode_compact_cells(bytes([0x3F, 0x7F, 0x40, 0x81, 0x00, 0xFF, 0x3F]), 8),
            [63, (1 << 64) - 1, (1 << 64) - 64, 128, (1 << 64) - 65],
        )

    def test_rejects_truncated_and_overwide_cells(self):
        with self.assertRaisesRegex(ValueError, "truncated"):
            decode_compact_cells(b"\x80", 8)
        with self.assertRaisesRegex(ValueError, "exceeds cell width"):
            decode_compact_cells(b"\x80" * 11 + b"\x00", 8)

    def test_exact_game_validator_records_boundaries_and_rejects_bad_opcode(self):
        fields = {"cod": 0, "dat": 24, "hea": 32, "stp": 96, "file_version": 10}
        good = validate_game_code([0xD2, 0xD2, 0xD2, 0], fields)
        self.assertEqual(good["status"], "PASS")
        self.assertEqual(good["instruction_count"], 3)
        self.assertEqual(good["instructions"][-1]["cell_offset"], 2)
        bad = validate_game_code([0], fields)
        self.assertEqual(bad["status"], "REJECT")
        self.assertIn("invalid opcode", bad["error"])

    def test_exact_game_validator_rejects_callback_dependent_opcode_without_callback(self):
        fields = {"cod": 0, "dat": 8, "hea": 16, "stp": 64, "file_version": 10}
        result = validate_game_code([0x9F, 0xD2], fields)
        self.assertEqual(result["status"], "REJECT")
        self.assertEqual(result["error_code"], "0x1c")

    def test_exact_game_validator_consumes_the_local_two_cell_opcode_table(self):
        fields = {"cod": 0, "dat": 24, "hea": 32, "stp": 96, "file_version": 10}
        result = validate_game_code([0x78, 0x55, 0xD2], fields)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["instructions"][0]["cells_consumed"], 2)
        self.assertEqual(result["instructions"][1]["cell_offset"], 2)


class AmxBatchTests(unittest.TestCase):
    def test_real_output_mirror_receipt_and_failed_stream_handling(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            root = base / "game"
            source_dir = root / "1.0.2" / NCA / "1" / "bin/battle/ai_script"
            source_dir.mkdir(parents=True)
            good_name, good_data = synthetic_amx([0xD2, 0xD2, 0xD2])
            bad_name, bad_data = synthetic_amx([0x00], name="rejected.amx")
            (source_dir / good_name).write_bytes(good_data)
            (source_dir / bad_name).write_bytes(bad_data)
            project = base / "project"

            with patch("lgpe_research.amx_decode._verify_exact_game_main", return_value=GAME_MAIN_SHA256):
                result = decode_amx(root, project, execute=True)

            self.assertEqual(result["scanned"], 2)
            self.assertEqual(result["decoded"], 1)
            self.assertEqual(result["failed"], 1)
            output = (
                project / "decoded/1.0.2/romfs/bin/battle/ai_script/sample.json"
            )
            self.assertTrue(output.is_file())
            record = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(record["code_cells_hex"], ["00000000000000d2"] * 3)
            self.assertEqual(record["source_sha256"], hashlib.sha256(good_data).hexdigest())
            self.assertEqual(record["game_verifier"]["status"], "PASS")
            self.assertFalse((output.parent / "rejected.json").exists())

            headers = [
                json.loads(line)
                for line in (project / "manifests/amx_headers.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            by_source = {row["source"].rsplit("/", 1)[-1]: row for row in headers}
            self.assertEqual(by_source[good_name]["status"], "DECODED")
            self.assertEqual(by_source[bad_name]["status"], "FAILED")
            self.assertIn("invalid opcode", by_source[bad_name]["error"])

            receipts = [
                json.loads(line)
                for line in (project / "manifests/outputs.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            self.assertEqual(len(receipts), 1)
            self.assertEqual(receipts[0]["output_sha256"], hashlib.sha256(output.read_bytes()).hexdigest())


if __name__ == "__main__":
    unittest.main()
