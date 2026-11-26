import struct
import unittest

from lgpe_research.itemhash_crossref import (
    assert_message_document_matches,
    inspect_candidate_table,
)


class ItemHashCrossReferenceTests(unittest.TestCase):
    def test_message_redecode_guard_accepts_equal_documents(self):
        document = {"format": "LGPE-message", "lines": [{"index": 0, "id": "ITEMNAME_000"}]}
        self.assertIsNone(assert_message_document_matches(document, dict(document)))

    def test_message_redecode_guard_rejects_a_stale_decoded_reference(self):
        existing = {"format": "LGPE-message", "lines": [{"index": 0, "id": "ITEMNAME_000"}]}
        redecoded = {"format": "LGPE-message", "lines": [{"index": 0, "id": "ITEMNAME_001"}]}
        with self.assertRaisesRegex(ValueError, "differs from source DAT/TBL re-decode"):
            assert_message_document_matches(existing, redecoded)

    def test_preserves_opaque_rows_and_links_only_matching_message_indexes(self):
        table = (
            struct.pack("<I", 2)
            + struct.pack("<QII", 0xAABBCCDDEEFF0011, 1, 0)
            + struct.pack("<QII", 0x1234567890ABCDEF, 8, 0x55)
        )
        message_lines = [
            {"index": 1, "id": "ITEMNAME_001", "hash": "not-compared"},
            {"index": 8, "id": "ITEMNAME_008", "hash": "also-not-compared"},
            {"index": 9, "id": "ITEMNAME_009", "hash": "not-referenced"},
        ]

        result = inspect_candidate_table(table, message_lines)

        self.assertEqual(result.get("format_status"), "DECODED")
        self.assertEqual(result.get("field_semantics_status"), "UNKNOWN")
        self.assertEqual(result["candidate_record_count"], 2)
        self.assertEqual(result["message_index_match_count"], 2)
        self.assertEqual(result["unmatched_record_indexes"], [])
        self.assertEqual(result["unreferenced_message_indexes"], [9])
        self.assertEqual(result["entries"][0], {
            "record_index": 0,
            "file_offset": 4,
            "raw_hex": "1100ffeeddccbbaa0100000000000000",
            "key_u64_at_0": "aabbccddeeff0011",
            "value_u64_at_8": "0000000000000001",
            "loader_value_u16": 1,
            "matching_message_ids": ["ITEMNAME_001"],
        })
        self.assertEqual(result["entries"][1]["matching_message_ids"], ["ITEMNAME_008"])
        self.assertEqual(result["entries"][1]["loader_value_u16"], 8)
        self.assertEqual(result["entries"][1]["value_u64_at_8"], "0000005500000008")

    def test_rejects_count_stride_mismatch(self):
        with self.assertRaisesRegex(ValueError, "count/stride"):
            inspect_candidate_table(struct.pack("<I", 1) + bytes(15), [])

    def test_rejects_duplicate_message_line_indexes_as_ambiguous(self):
        table = struct.pack("<I", 1) + struct.pack("<QII", 7, 2, 0)
        result = inspect_candidate_table(table, [
            {"index": 2, "id": "ITEMNAME_002A"},
            {"index": 2, "id": "ITEMNAME_002B"},
        ])
        self.assertEqual(result["ambiguous_record_indexes"], [0])
        self.assertEqual(result["entries"][0]["matching_message_ids"], [
            "ITEMNAME_002A", "ITEMNAME_002B",
        ])


if __name__ == "__main__":
    unittest.main()
