import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from lgpe_research import cli


class GfbcolMainCrossrefCliTests(unittest.TestCase):
    def test_shared_json_writer_keeps_legacy_default_without_final_newline(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "legacy.json"
            cli.write_json(output, {"sample": 1})

            self.assertFalse(output.read_bytes().endswith(b"\n"))

    def test_command_writes_the_report_under_the_manifest_root(self):
        report = {
            "schema": "lgpe-gfbcol-main-token-crossref-v1",
            "analysis_status": "EXACT_LITERAL_VALUE_CROSS_REFERENCE",
            "schema_status": "UNKNOWN",
            "main": {
                "sha256": "1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8"
            },
            "gfbcol_probe": {"sources_read": 698},
            "summary": {
                "exact_main_tokens": 6,
                "tokens_matching_candidate_strings": 4,
                "matched_candidate_occurrences": 188,
            },
            "ghidra_owner_candidate_trace": {
                "summary": {"entry": "main+0x24f460", "call_sites": 6}
            },
        }
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp)
            output = project / "manifests" / "gfbcol-crossref.json"
            with patch.object(cli, "PROJECT", project), patch.object(
                cli, "build_gfbcol_main_crossref_report", create=True, return_value=report
            ):
                stdout = io.StringIO()
                with contextlib.redirect_stdout(stdout):
                    code = cli.main([
                        "crossref-gfbcol-main",
                        "--root",
                        str(project.parent),
                        "--output",
                        str(output),
                    ])

            self.assertEqual(code, 0)
            self.assertEqual(json.loads(output.read_text(encoding="utf-8")), report)
            raw = output.read_bytes()
            self.assertIn(b"\r\n", raw)
            self.assertNotIn(b"\n", raw.replace(b"\r\n", b""))
            self.assertIn('"tokens_matching_candidate_strings": 4', stdout.getvalue())
            self.assertIn('"owner_candidate": "main+0x24f460"', stdout.getvalue())

    def test_command_rejects_output_outside_manifest_root(self):
        report = {"schema": "lgpe-gfbcol-main-token-crossref-v1"}
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp)
            outside = Path(temp).parent / "escape-gfbcol-crossref.json"
            with patch.object(cli, "PROJECT", project), patch.object(
                cli, "build_gfbcol_main_crossref_report", create=True, return_value=report
            ):
                stdout = io.StringIO()
                with contextlib.redirect_stdout(stdout):
                    code = cli.main([
                        "crossref-gfbcol-main",
                        "--root",
                        str(project.parent),
                        "--output",
                        str(outside),
                    ])
            self.assertEqual(code, 1)
            self.assertFalse(outside.exists())


if __name__ == "__main__":
    unittest.main()
