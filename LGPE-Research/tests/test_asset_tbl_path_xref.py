import unittest

from lgpe_research.asset_tbl_xref import cross_reference_asset_paths


class AssetTablePathCrossReferenceTests(unittest.TestCase):
    def test_reports_exact_case_only_missing_and_invalid_path_matches(self):
        entries = [
            {"index": 0, "hash": "01", "label": "English/common/item.dat", "raw_label_hex": ""},
            {"index": 1, "hash": "02", "label": "French/common/item.dat", "raw_label_hex": ""},
            {"index": 2, "hash": "03", "label": "German/debug/item.dat", "raw_label_hex": ""},
            {"index": 3, "hash": "04", "label": "../../outside.dat", "raw_label_hex": ""},
        ]
        rows = cross_reference_asset_paths(entries, {
            "bin/message/English/common/item.dat",
            "bin/message/English/common/item.tbl",
            "bin/message/french/common/item.dat",
        })

        self.assertEqual(
            [row["path_status"] for row in rows],
            ["MATCH_EXACT", "MATCH_CASEFOLD", "NO_MATCH", "INVALID_LABEL_PATH"],
        )
        self.assertEqual(rows[0]["matched_source_paths"], ["bin/message/English/common/item.dat"])
        self.assertEqual(rows[1]["matched_source_paths"], ["bin/message/french/common/item.dat"])
        self.assertTrue(rows[0]["same_stem_tbl_present"])
        self.assertIsNone(rows[3]["relative_source_candidate"])

    def test_marks_casefold_collisions_as_ambiguous(self):
        rows = cross_reference_asset_paths(
            [{"index": 8, "hash": "08", "label": "English/common/item.dat"}],
            {
                "bin/message/English/common/item.dat",
                "bin/message/english/common/item.dat",
            },
        )
        self.assertEqual(rows[0]["path_status"], "AMBIGUOUS_CASEFOLD_MATCH")
        self.assertEqual(len(rows[0]["matched_source_paths"]), 2)


if __name__ == "__main__":
    unittest.main()
