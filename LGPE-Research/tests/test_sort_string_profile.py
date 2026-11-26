from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from lgpe_research.sort_string_profile import profile_sort_string


class SortStringProfileTest(unittest.TestCase):
    def make_romfs(self, directory: str) -> Path:
        romfs = Path(directory)
        target = romfs / "bin/app/sort_string/English/item_sort_table.dat"
        target.parent.mkdir(parents=True)
        target.write_bytes(bytes.fromhex("020001000300"))
        return romfs

    def test_permutation_candidate_stays_unknown_and_keeps_source_hash(self):
        with TemporaryDirectory() as directory:
            romfs = self.make_romfs(directory)

            result = profile_sort_string(romfs)

        self.assertEqual(result["summary"]["scanned"], 1)
        self.assertEqual(result["summary"]["unknown"], 1)
        self.assertEqual(result["files"][0].get("source_version"), "1.0.2")
        self.assertEqual(
            result["files"][0].get("nca_folder"),
            "2b7730a9e56498bbafac2002d4908c6b_NCA",
        )
        self.assertEqual(result["files"][0]["format_status"], "UNKNOWN")
        self.assertEqual(result["files"][0]["candidate_representation"], "u16le hypothesis")
        self.assertTrue(result["files"][0]["sort_table_permutation_1_based"])
        self.assertEqual(result["files"][0]["u16le_candidate_count"], 3)
        self.assertEqual(
            result["files"][0]["sha256"],
            "9fb0b9481eb1fc19ca83464f92df790f0cd0236b60f33bdf1179a4278c3e967e",
        )

    def test_odd_length_source_has_no_u16_candidate(self):
        with TemporaryDirectory() as directory:
            romfs = self.make_romfs(directory)
            source = romfs / "bin/app/sort_string/English/item_sort_table.dat"
            source.write_bytes(b"\x01\x00\xff")

            result = profile_sort_string(romfs)

        row = result["files"][0]
        self.assertEqual(row["bytes"], 3)
        self.assertIsNone(row["candidate_representation"])
        self.assertIsNone(row["u16le_candidate_count"])
        self.assertIsNone(row["sort_table_permutation_1_based"])
        self.assertEqual(row["format_status"], "UNKNOWN")

    def test_empty_sort_table_is_not_a_valid_permutation(self):
        with TemporaryDirectory() as directory:
            romfs = self.make_romfs(directory)
            (romfs / "bin/app/sort_string/English/item_sort_table.dat").write_bytes(b"")

            result = profile_sort_string(romfs)

        self.assertFalse(result["files"][0]["sort_table_permutation_1_based"])

    def test_duplicate_values_fail_the_permutation_candidate_check(self):
        with TemporaryDirectory() as directory:
            romfs = self.make_romfs(directory)
            (romfs / "bin/app/sort_string/English/item_sort_table.dat").write_bytes(
                bytes.fromhex("010001000200")
            )

            result = profile_sort_string(romfs)

        self.assertFalse(result["files"][0]["sort_table_permutation_1_based"])

    def test_missing_sort_string_directory_is_reported(self):
        with TemporaryDirectory() as directory:
            with self.assertRaisesRegex(FileNotFoundError, "sort_string"):
                profile_sort_string(Path(directory))


if __name__ == "__main__":
    unittest.main()
