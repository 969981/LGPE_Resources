import hashlib
import importlib.util
import struct
import tempfile
import unittest
from pathlib import Path


_SCRIPT = Path(__file__).resolve().parents[1] / "scripts/research/check_gfbcol_main_references.py"
_SPEC = importlib.util.spec_from_file_location("gfbcol_main_references", _SCRIPT)
probe = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(probe)


def nso_fixture(compressed=False):
    result = bytearray(0x100)
    result[:4] = b"NSO0"
    struct.pack_into("<I", result, 0xC, 0x3F if compressed else 0x38)
    for index, raw in enumerate((b"text", b"read", b"data")):
        payload = bytes([len(raw) << 4]) + raw if compressed else raw
        struct.pack_into("<III", result, 0x10 + 16 * index, len(result), index * 0x1000, len(raw))
        struct.pack_into("<I", result, 0x60 + index * 4, len(payload))
        result[0xA0 + index * 32:0xC0 + index * 32] = hashlib.sha256(raw).digest()
        result.extend(payload)
    return result


class GfbcolMainReferenceTests(unittest.TestCase):
    def test_validates_uncompressed_and_compressed_segment_hashes(self):
        for compressed in (False, True):
            with self.subTest(compressed=compressed):
                segments = probe.parse_nso_segments(bytes(nso_fixture(compressed)))
                self.assertEqual([s["data"] for s in segments], [b"text", b"read", b"data"])
                self.assertTrue(all(s["header_sha256_verified"] for s in segments))
                self.assertEqual([s["compressed"] for s in segments], [compressed] * 3)

    def test_rejects_truncation_bad_magic_and_corrupt_segment(self):
        fixture = nso_fixture()
        bad_magic = bytearray(fixture)
        bad_magic[:4] = b"bad!"
        corrupt = bytearray(fixture)
        corrupt[-1] ^= 1
        for data in (fixture[:12], fixture[:-1], bad_magic, corrupt):
            with self.subTest(data=data[:16]):
                with self.assertRaises(ValueError):
                    probe.parse_nso_segments(bytes(data))

    def test_rejects_missing_header_hash_and_oversized_allocation(self):
        missing_hash = nso_fixture()
        struct.pack_into("<I", missing_hash, 0xC, 0)
        with self.assertRaisesRegex(ValueError, "hash is not enabled"):
            probe.parse_nso_segments(bytes(missing_hash))
        oversized = nso_fixture(True)
        struct.pack_into("<I", oversized, 0x18, probe.MAX_BYTES + 1)
        with self.assertRaisesRegex(ValueError, "decompressed size"):
            probe.parse_nso_segments(bytes(oversized))

    def test_searches_utf16_at_both_parities_and_caps_samples(self):
        segments = [{"memory_offset": 0, "data": b"!" + "GFBCOL".encode("utf-16le")},
                    {"memory_offset": 0x100, "data": "gfbcol".encode("utf-16le")},
                    {"memory_offset": 0x200, "data": b"GFBCOL " * 40}]
        result = probe.scan_strings(segments, ("gfbcol", ".gfbcol"))
        self.assertEqual(result["gfbcol"]["utf-16le"]["count"], 2)
        self.assertEqual(result["gfbcol"]["utf-16le"]["address_samples"],
                         ["0x7100000001", "0x7100000100"])
        self.assertEqual(result["gfbcol"]["ascii"]["count"], 40)
        self.assertEqual(len(result["gfbcol"]["ascii"]["address_samples"]), 32)
        self.assertEqual(result[".gfbcol"]["ascii"]["count"], 0)

    def test_decodes_six_observed_instruction_sequences(self):
        observations = (
            (0x24F480, 0xF03218, 0x91086021, 0x97F6F075),
            (0x24F4D8, 0xF03221, 0x91088421, 0x97F6F05F),
            (0x24F528, 0xF0322B, 0x9108AC21, 0x97F6F04B),
            (0x24F578, 0xF03234, 0x9108D021, 0x97F6F037),
            (0x24F5C8, 0xF0323C, 0x9108F021, 0x97F6F023),
            (0x24F618, 0xF0324A, 0x91092821, 0x97F6F00F),
        )
        for start, target, add, branch in observations:
            with self.subTest(start=start):
                self.assertEqual(probe.decode_link_words((0x900065A1, add, 0x910023E0, branch), start),
                                 {"string_offset": target, "branch_target_offset": 0xB660})

    def test_decodes_signed_adrp_and_positive_branch(self):
        # ADRP x1, previous page; ADD x1,x1,#0x20; ADD x0,sp,#8; BL +0x10.
        self.assertEqual(probe.decode_link_words((0xF0FFFFE1, 0x91008021, 0x910023E0, 0x94000004), 0x2000),
                         {"string_offset": 0x1020, "branch_target_offset": 0x201C})

    def test_rejects_wrong_register_shift_and_branch_opcode(self):
        valid = [0x900065A1, 0x91086021, 0x910023E0, 0x97F6F075]
        for index, value in ((0, 0x900065A2), (1, 0x91486021), (1, 0x91086041),
                             (2, 0x910023E1), (3, 0x17F6F075)):
            mutated = valid.copy()
            mutated[index] = value
            with self.subTest(index=index, value=value):
                with self.assertRaises(ValueError):
                    probe.decode_link_words(tuple(mutated), 0x24F480)

    def test_main_guard_rejects_other_inputs_without_writing_them(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "main"
            original = bytes(nso_fixture())
            source.write_bytes(original)
            with self.assertRaisesRegex(ValueError, "exact Pikachu 1.0.2 main SHA-256 mismatch"):
                probe.inspect_main(source)
            self.assertEqual(source.read_bytes(), original)
            self.assertEqual(list(Path(directory).iterdir()), [source])


if __name__ == "__main__":
    unittest.main()
