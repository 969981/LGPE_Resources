import hashlib
import json
from pathlib import Path
import struct
import tempfile
import unittest
import zlib

from lgpe_research.archive_reader import decode_payload, extract, fnv, lz4_block, read_gfpak, read_sarc, safe_path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT.parent / "1.0.2/2b7730a9e56498bbafac2002d4908c6b_NCA/1"


class ArchiveParserTests(unittest.TestCase):
    def test_game_freak_hash_basis(self):
        self.assertEqual(fnv(""), 0xCBF29CE484222645)
        self.assertEqual(fnv("bin/pokemon/pm0001_00/anm/"), 0xE7AA746DAA460564)

    def test_literal_and_overlapping_lz4(self):
        self.assertEqual(lz4_block(b"\x30abc", 3), b"abc")
        self.assertEqual(lz4_block(b"\x32abc\x03\x00\x00", 9), b"abcabcabc")
        self.assertEqual(lz4_block(b"\xf0\x01" + b"a" * 16, 16), b"a" * 16)

    def test_lz4_rejects_bad_ranges(self):
        for data, size in [(b"\x30a", 3), (b"\x00\x00\x00", 4), (b"\x00\x01\x00", 4), (b"\x10a", 0), (b"\xf0", 20)]:
            with self.subTest(data=data), self.assertRaises(ValueError):
                lz4_block(data, size)

    def test_compression_modes(self):
        value = b"example" * 20
        self.assertEqual(decode_payload(value, 0, len(value)), value)
        self.assertEqual(decode_payload(zlib.compress(value), 1, len(value)), value)
        with self.assertRaises(NotImplementedError):
            decode_payload(value, 3, len(value))
        with self.assertRaises(ValueError):
            decode_payload(value, 0, len(value) + 1)

    def test_unsafe_paths(self):
        for path in ["../x", "/x", "a/../b", "a//b", "a/./b", "C:/a", "a\\b", "a/NUL.txt", "a/b."]:
            with self.subTest(path=path), self.assertRaises(ValueError):
                safe_path(path)
        self.assertEqual(safe_path("anim/a.bflan"), "anim/a.bflan")

    def test_truncated_or_unknown_headers(self):
        for parser in (read_gfpak, read_sarc):
            with self.assertRaises((ValueError, NotImplementedError)):
                list(parser(b"bad"))
        unsupported = struct.pack("<8sIIII", b"GFLXPACK", 0x2000, 0, 0, 0)
        with self.assertRaises(NotImplementedError):
            list(read_gfpak(unsupported))

    @unittest.skipUnless((SOURCE / "bin/archive/pokemon/pm0001_00.gfpak").exists(), "private local dump unavailable")
    def test_local_gfpak_immutable_idempotent_and_conflict(self):
        source = SOURCE / "bin/archive/pokemon/pm0001_00.gfpak"
        before = hashlib.sha256(source.read_bytes()).hexdigest()
        corpus = ROOT / "tools/src/Switch-Toolbox/File_Format_Library/Resources/Hashes/Pkmn.txt"
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            dry = extract(source, SOURCE, output, corpus, False)
            self.assertFalse(Path(dry["output"]).exists())
            first = extract(source, SOURCE, output, corpus, True)
            second = extract(source, SOURCE, output, corpus, True)
            self.assertEqual(first, second)
            self.assertEqual(first["member_count"], 70)
            self.assertEqual(first["output_bytes"], 5504068)
            member = Path(first["output"]) / first["members"][0]["internal_path"]
            member.write_bytes(b"changed")
            with self.assertRaises(FileExistsError):
                extract(source, SOURCE, output, corpus, True)
        self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), before)

    @unittest.skipUnless((SOURCE / "bin/app/battle/bin/battle_command_00.arc").exists(), "private local dump unavailable")
    def test_local_sarc_names_hashes_and_ranges(self):
        source = SOURCE / "bin/app/battle/bin/battle_command_00.arc"
        data = source.read_bytes()
        entries = list(read_sarc(data))
        self.assertEqual(len(entries), 41)
        self.assertEqual(sum(len(payload) for _, payload in entries), 1472090)
        self.assertEqual(entries[0][0]["internal_path"], "anim/battle_button_grptxt_00_keep.bflan")
        self.assertTrue(any(payload.startswith(b"BNTX") for _, payload in entries))
        damaged = bytearray(data)
        damaged[32] ^= 1
        with self.assertRaises(ValueError):
            list(read_sarc(bytes(damaged)))

    @unittest.skipUnless((SOURCE / "bin/archive/field/area01.gfpak").exists(), "private local dump unavailable")
    def test_local_field_member_count_and_bounds(self):
        data = (SOURCE / "bin/archive/field/area01.gfpak").read_bytes()
        entries = list(read_gfpak(data))
        self.assertEqual(len(entries), 179)
        self.assertEqual(sum(len(payload) for _, payload in entries), 10892904)
        self.assertTrue(all(record["compression"] == 2 for record, _ in entries))
        damaged = bytearray(data)
        struct.pack_into("<Q", damaged, 24, len(data))
        with self.assertRaises(ValueError):
            list(read_gfpak(bytes(damaged)))


if __name__ == "__main__":
    unittest.main()
