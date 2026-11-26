import contextlib
import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from lgpe_research.cli import main
from lgpe_research.core import PROJECT, source_dirs
from lgpe_research.nso_relocation_crossref import matching_relative_relocations


_MAIN = source_dirs(PROJECT.parent)["exefs"] / "main"
_POKELDN_PARSER = PROJECT / "tools/src/pokeldn/pokeldn/switch/nso.py"


class NsoRelocationCrossReferenceTests(unittest.TestCase):
    def test_matches_start_and_last_body_byte_but_excludes_end_address(self):
        relocations = [
            (0x153C800, 0x2F8A50),
            (0x153C808, 0x2F8E6B),
            (0x153C810, 0x2F8E6C),
            (0x153C818, 0x2F8A4F),
        ]

        matches = matching_relative_relocations(relocations, 0x2F8A50, 0x2F8E6C)

        self.assertEqual(
            matches,
            [
                {"slot": 0x153C800, "addend": 0x2F8A50},
                {"slot": 0x153C808, "addend": 0x2F8E6B},
            ],
        )

    def test_exact_target_uses_a_one_byte_half_open_range(self):
        matches = matching_relative_relocations(
            [(0x40, 0x1A61E0), (0x48, 0x1A61E1)], 0x1A61E0, 0x1A61E1
        )

        self.assertEqual(matches, [{"slot": 0x40, "addend": 0x1A61E0}])

    def test_rejects_empty_or_reversed_target_ranges(self):
        for start, end in ((0x100, 0x100), (0x101, 0x100), (-1, 1)):
            with self.subTest(start=start, end=end):
                with self.assertRaisesRegex(ValueError, "target range"):
                    matching_relative_relocations([], start, end)

    @unittest.skipUnless(
        _MAIN.is_file() and _POKELDN_PARSER.is_file(),
        "local LGPE 1.0.2 main or pinned PokeLDN source unavailable",
    )
    def test_cli_writes_exact_build_relocation_report_without_changing_main(self):
        before = hashlib.sha256(_MAIN.read_bytes()).hexdigest()
        with tempfile.TemporaryDirectory(dir=PROJECT / "manifests") as temp_dir:
            output = Path(temp_dir) / "nso-relocation-crossref.json"
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                result = main(
                    [
                        "nso-relocation-crossref",
                        "--root",
                        str(PROJECT.parent),
                        "--output",
                        str(output),
                    ]
                )

            report = json.loads(output.read_text(encoding="utf-8"))

        self.assertEqual(result, 0)
        self.assertEqual(report["status"], "STATIC_RELOCATION_CROSSREF_ONLY")
        self.assertEqual(report["main"]["sha256"], "1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8")
        self.assertEqual(report["relocations"]["relative_count"], 71687)
        dispatcher = next(row for row in report["queries"] if row["id"] == "spawn_dispatcher_body")
        self.assertEqual(dispatcher["range"]["end_exclusive"], "main+0x2f8e6c")
        self.assertEqual(dispatcher["match_count"], 0)
        api_targets = next(row for row in report["queries"] if row["id"] == "capture_api_table_targets")
        self.assertEqual(
            [(row["slot"], row["addend"]) for row in api_targets["matches"]],
            [
                ("main+0x153c870", "main+0x1a5e80"),
                ("main+0x153c880", "main+0x1a61e0"),
                ("main+0x153c890", "main+0x1a64c0"),
            ],
        )
        self.assertEqual(report["interpretation"]["runtime_dispatch"], "UNVERIFIED")
        self.assertEqual(hashlib.sha256(_MAIN.read_bytes()).hexdigest(), before)


if __name__ == "__main__":
    unittest.main()
