import struct
import unittest

from lgpe_research.sort_string_crossref import cross_reference_sort_table


def message_payload(prefix="MONSNAME"):
    return {
        "schema": "lgpe-gamedata-v1",
        "format": "LGPE-message",
        "lines": [
            {"index": 0, "id": f"{prefix}_000", "text": "Egg"},
            {"index": 1, "id": f"{prefix}_001", "text": "Zeta"},
            {"index": 2, "id": f"{prefix}_002", "text": "Alpha"},
        ],
    }


class SortStringCrossrefTests(unittest.TestCase):
    def test_cross_reference_is_lossless_and_records_exact_main_reader(self):
        raw = struct.pack("<2H", 2, 1)
        result = cross_reference_sort_table(
            raw,
            message_payload(),
            source="bin/app/sort_string/English/monsname_sort_table.dat",
            message_source="bin/message/English/common/monsname.dat",
            message_output="decoded/1.0.2/romfs/bin/message/English/common/monsname.json",
        )

        self.assertEqual(result["format_status"], "DECODED")
        self.assertEqual(result["candidate"]["representation"], "u16le-index-table")
        self.assertEqual(result["candidate"]["entry_count"], 2)
        self.assertTrue(result["candidate"]["little_endian_one_based_permutation"])
        self.assertFalse(result["candidate"]["big_endian_one_based_permutation"])
        self.assertEqual(result["candidate"]["resolved_message_line_count"], 2)
        self.assertEqual(result["candidate"]["adjacent_nfkd_casefold_ordered_pairs"], 1)
        self.assertEqual(
            [row["message_line_index"] for row in result["candidate"]["first_12_resolved_rows"]],
            [2, 1],
        )
        self.assertEqual(
            bytes.fromhex("".join(row["raw_hex"] for row in result["candidate"]["first_12_resolved_rows"])),
            raw,
        )
        self.assertEqual(result["code_evidence"]["direct_element_read"], "main+0x374a90")
        self.assertEqual(result["code_evidence"]["element_width_bytes"], 2)
        self.assertEqual(result["code_evidence"]["endianness"], "little")

    def test_rejects_non_permutation_candidate(self):
        with self.assertRaisesRegex(ValueError, "not a nonempty 1-based permutation"):
            cross_reference_sort_table(
                struct.pack("<2H", 1, 1),
                message_payload(),
                source="bin/app/sort_string/English/monsname_sort_table.dat",
                message_source="bin/message/English/common/monsname.dat",
                message_output="decoded/English/monsname.json",
            )

    def test_rejects_odd_byte_count(self):
        with self.assertRaisesRegex(ValueError, "odd byte length"):
            cross_reference_sort_table(
                b"\x01",
                message_payload(),
                source="bin/app/sort_string/English/monsname_sort_table.dat",
                message_source="bin/message/English/common/monsname.dat",
                message_output="decoded/English/monsname.json",
            )

    def test_rejects_missing_companion_message_index(self):
        with self.assertRaisesRegex(ValueError, "message indexes"):
            cross_reference_sort_table(
                struct.pack("<2H", 1, 2),
                {**message_payload(), "lines": [
                    {"index": 0, "id": "ITEMNAME_000", "text": "None"},
                    {"index": 1, "id": "ITEMNAME_001", "text": "A"},
                ]},
                source="bin/app/sort_string/English/monsname_sort_table.dat",
                message_source="bin/message/English/common/monsname.dat",
                message_output="decoded/English/monsname.json",
            )

    def test_reports_message_id_prefix_mismatch_without_promoting_candidate(self):
        payload = message_payload(prefix="ITEMNAME")
        result = cross_reference_sort_table(
            struct.pack("<2H", 1, 2),
            payload,
            source="bin/app/sort_string/English/monsname_sort_table.dat",
            message_source="bin/message/English/common/monsname.dat",
            message_output="decoded/English/monsname.json",
        )

        self.assertFalse(result["candidate"]["message_id_prefix_matches_family"])
        self.assertEqual(result["format_status"], "DECODED")


if __name__ == "__main__":
    unittest.main()
