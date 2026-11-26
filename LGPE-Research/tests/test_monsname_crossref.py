import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from lgpe_research.core import NCA, VERSION
from lgpe_research.monsname_crossref import build_personal_monsname_crossref, compare_text_lists


class MonsnameCrossReferenceTest(unittest.TestCase):
    def test_reports_exact_ordered_prefix(self):
        result = compare_text_lists(["egg", "bulbasaur"], ["egg", "bulbasaur", "venusaur"])

        self.assertEqual(result, {
            "source_entries": 2,
            "reference_entries": 3,
            "same_index_matches": 2,
            "mismatch_indices": [],
            "same_ordered_prefix": True,
            "reference_tail_entries": 1,
        })

    def test_reports_same_count_with_wrong_order_as_mismatch(self):
        result = compare_text_lists(["egg", "bulbasaur"], ["bulbasaur", "egg"])

        self.assertEqual(result, {
            "source_entries": 2,
            "reference_entries": 2,
            "same_index_matches": 0,
            "mismatch_indices": [0, 1],
            "same_ordered_prefix": False,
            "reference_tail_entries": 0,
        })

    def test_build_report_rehashes_sources_and_accepts_windows_manifest_paths(self):
        source_rel = "bin/pokelib/personal/monsname.dat"
        reference_rel = "bin/message/JPN/common/monsname.dat"
        source_bytes = b"personal-source"
        reference_bytes = b"localized-reference"
        source_json = {
            "entries": [{"index": 0, "text": "egg"}, {"index": 1, "text": "bulbasaur"}],
        }
        reference_json = {"lines": [
            {"index": 0, "text": "egg"},
            {"index": 1, "text": "bulbasaur"},
            {"index": 2, "text": "venusaur"},
        ]}
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = base / "game"
            project = base / "project"
            romfs = root / VERSION / NCA / "1"
            source_path = romfs / source_rel
            reference_path = romfs / reference_rel
            source_path.parent.mkdir(parents=True)
            reference_path.parent.mkdir(parents=True)
            source_path.write_bytes(source_bytes)
            reference_path.write_bytes(reference_bytes)
            source_output_rel = "decoded/1.0.2/romfs/bin/pokelib/personal/monsname.json"
            reference_output_rel = "decoded/1.0.2/romfs/bin/message/JPN/common/monsname.json"
            source_output = project / source_output_rel
            reference_output = project / reference_output_rel
            source_output.parent.mkdir(parents=True)
            reference_output.parent.mkdir(parents=True)
            source_payload = json.dumps(source_json).encode("utf-8")
            reference_payload = json.dumps(reference_json).encode("utf-8")
            source_output.write_bytes(source_payload)
            reference_output.write_bytes(reference_payload)
            rows = [
                {"source": source_rel, "status": "DECODED", "source_bytes": len(source_bytes),
                 "source_sha256": hashlib.sha256(source_bytes).hexdigest(),
                 "output": source_output_rel.replace("/", "\\"),
                 "output_sha256": hashlib.sha256(source_payload).hexdigest(),
                 "output_bytes": len(source_payload), "count": 2, "method": "pokedat",
                 "tool_versions": {"pokedat": "pinned"}},
                {"source": reference_rel, "status": "DECODED", "source_bytes": len(reference_bytes),
                 "source_sha256": hashlib.sha256(reference_bytes).hexdigest(),
                 "output": reference_output_rel.replace("/", "\\"),
                 "output_sha256": hashlib.sha256(reference_payload).hexdigest(),
                 "output_bytes": len(reference_payload), "count": 3},
            ]
            manifest = project / "manifests/gamedata.jsonl"
            manifest.parent.mkdir(parents=True)
            manifest.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")

            report = build_personal_monsname_crossref(project, root)
            self.assertTrue(report["comparison"]["same_ordered_prefix"])
            self.assertEqual(report["comparison"]["same_index_matches"], 2)
            self.assertEqual(report["primary"]["tool_versions"], {"pokedat": "pinned"})

            rows[0]["count"] = 99
            manifest.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "manifest count"):
                build_personal_monsname_crossref(project, root)


if __name__ == "__main__":
    unittest.main()
