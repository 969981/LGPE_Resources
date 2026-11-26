import unittest

from lgpe_research.localized_sort_decode import (
    SCHEMA,
    decode_initial_to_sort,
    decode_sort_table,
)


class LocalizedSortDecodeTest(unittest.TestCase):
    def test_sort_table_reads_little_endian_u16_values_and_round_trips(self):
        data = bytes.fromhex("cc013f006701")

        result = decode_sort_table(data)

        self.assertEqual(result["schema"], SCHEMA)
        self.assertEqual(result["format"], "u16le-index-table")
        self.assertEqual(result["entry_count"], 3)
        self.assertEqual([row["value_u16le"] for row in result["entries"]], [460, 63, 359])
        self.assertEqual(bytes.fromhex(result["raw_hex"]), data)

    def test_sort_table_rejects_partial_element(self):
        with self.assertRaisesRegex(ValueError, "not divisible by 2"):
            decode_sort_table(b"\x01\x00\x02")

    def test_initial_to_sort_reads_pairs_without_naming_field_semantics(self):
        data = bytes.fromhex("ffff210022004e00")

        result = decode_initial_to_sort(data)

        self.assertEqual(result["format"], "u16le-pair-table")
        self.assertEqual(result["entry_count"], 2)
        self.assertEqual(
            result["entries"],
            [
                {"index": 0, "byte_offset": 0, "first_u16le": 65535, "second_u16le": 33},
                {"index": 1, "byte_offset": 4, "first_u16le": 34, "second_u16le": 78},
            ],
        )
        self.assertEqual(bytes.fromhex(result["raw_hex"]), data)

    def test_initial_to_sort_rejects_partial_record(self):
        with self.assertRaisesRegex(ValueError, "not divisible by 4"):
            decode_initial_to_sort(b"\x00\x00\x01\x00\x02")

    def test_empty_tables_are_not_reported_as_decoded(self):
        for decoder in (decode_sort_table, decode_initial_to_sort):
            with self.subTest(decoder=decoder.__name__):
                with self.assertRaisesRegex(ValueError, "empty"):
                    decoder(b"")


if __name__ == "__main__":
    unittest.main()
