import json
import hashlib
import tempfile
import unittest
from pathlib import Path

from lgpe_research.cli import main
from lgpe_research.save_api_crossref import build_save_api_crossref_report


MAIN_SHA256 = "1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8"


def trace_run(main_sha256=MAIN_SHA256, read_only="true", source_unchanged="true"):
    return f"""
2026-10-30 INFO InspectSaveApiReferences.java> API_CODE_CALLS\t<EXTERNAL>::nn::fs::MountSaveData\tcount=1
2026-10-30 INFO InspectSaveApiReferences.java> API_CODE_CALLS\t<EXTERNAL>::nn::fs::IsSaveDataExisting\tcount=1
2026-10-30 INFO InspectSaveApiReferences.java> API_CODE_CALLS\t<EXTERNAL>::nn::fs::CommitSaveData\tcount=0
2026-10-30 INFO InspectSaveApiReferences.java> API_CODE_CALLS\t<EXTERNAL>::nn::fs::EnsureSaveData\tcount=0
2026-10-30 INFO InspectSaveApiReferences.java> FS_API_SYMBOL\t<EXTERNAL>::nn::fs::ReadFile
2026-10-30 INFO InspectSaveApiReferences.java> FS_API_CODE_CALLS\t<EXTERNAL>::nn::fs::ReadFile\tcount=1
2026-10-30 INFO InspectSaveApiReferences.java> FS_API_CODE_CALLS\t<EXTERNAL>::nn::fs::WriteFile\tcount=0
2026-10-30 INFO InspectSaveApiReferences.java> FS_API_CODE_CALLS\t<EXTERNAL>::nn::fs::SetFileSize\tcount=0
2026-10-30 INFO InspectSaveApiReferences.java> FS_OPERATION_CALLSITE\t7100024e6c\t<EXTERNAL>::nn::fs::MountSaveData\tcaller=7100024d70\tcaller_name=FUN_7100024d70
2026-10-30 INFO InspectSaveApiReferences.java> FS_OPERATION_OWNER_XREF_SUMMARY\tfunction=7100677620\tname=FUN_7100677620\tincoming_references=2
2026-10-30 INFO InspectSaveApiReferences.java> FS_OPERATION_PARENT_CALLSITE\t71006756d8\tchild=7100677620\tparent=71006755f0\tparent_name=FUN_71006755f0
2026-10-30 INFO InspectSaveApiReferences.java> INTERNAL_TARGET\tSAVE_WORKER\t7100024d70\tincoming_references=0
2026-10-30 INFO InspectSaveApiReferences.java> SUMMARY\tmain_sha256={main_sha256}\timage_base=0x7100000000\tsave_api_symbols=6\tsave_api_references=71\tsave_api_calls=50\tmount_calls=1\texisting_calls=1\tworker_incoming_references=0\tunique_api_caller_functions=37\tfilesystem_api_symbols=18\tfilesystem_api_code_calls=19\tfilesystem_operation_parents=2\tdecompile_failures=0\tsourceHashUnchanged={source_unchanged}\treadOnly={read_only}
""".strip()


class SaveApiCrossReferenceTests(unittest.TestCase):
    def test_report_preserves_exact_build_callsites_and_unknown_ownership(self):
        report = build_save_api_crossref_report(
            trace_run(),
            trace_script_sha256="a" * 64,
            trace_wrapper_sha256="b" * 64,
        )

        self.assertEqual(report["schema"], "lgpe-save-api-crossref-v1")
        self.assertEqual(report["status"], "STATIC_REFS_ONLY")
        self.assertEqual(report["main"]["sha256"], MAIN_SHA256)
        self.assertEqual(
            report["save_data_api_code_calls"]["<EXTERNAL>::nn::fs::MountSaveData"],
            1,
        )
        self.assertEqual(
            report["save_data_api_code_calls"]["<EXTERNAL>::nn::fs::CommitSaveData"],
            0,
        )
        self.assertEqual(
            report["filesystem_api_code_calls"]["<EXTERNAL>::nn::fs::WriteFile"],
            0,
        )
        self.assertEqual(
            report["filesystem_mutation_callsites"][0]["callsite"],
            "main+0x24e6c",
        )
        self.assertEqual(report["save_worker"]["incoming_references"], 0)
        self.assertEqual(
            report["filesystem_operation_owners"][0]["incoming_references"],
            2,
        )
        self.assertEqual(report["interpretation"]["primary_player_save_owner"], "UNKNOWN")
        self.assertEqual(report["interpretation"]["runtime_execution"], "UNVERIFIED")

    def test_report_uses_only_latest_appended_ghidra_run(self):
        old_run = trace_run().replace(
            "<EXTERNAL>::nn::fs::MountSaveData\tcount=1",
            "<EXTERNAL>::nn::fs::MountSaveData\tcount=99",
        )
        report = build_save_api_crossref_report(
            old_run + "\n" + trace_run(),
            trace_script_sha256="c" * 64,
            trace_wrapper_sha256="d" * 64,
        )
        self.assertEqual(
            report["save_data_api_code_calls"]["<EXTERNAL>::nn::fs::MountSaveData"],
            1,
        )

    def test_report_rejects_other_main_builds(self):
        with self.assertRaisesRegex(ValueError, "main SHA-256 mismatch"):
            build_save_api_crossref_report(
                trace_run(main_sha256="0" * 64),
                trace_script_sha256="e" * 64,
                trace_wrapper_sha256="f" * 64,
            )

    def test_report_rejects_non_read_only_or_modified_source_runs(self):
        for transcript in (
            trace_run(read_only="false"),
            trace_run(source_unchanged="false"),
        ):
            with self.subTest(transcript=transcript[-40:]):
                with self.assertRaisesRegex(ValueError, "read-only source integrity"):
                    build_save_api_crossref_report(
                        transcript,
                        trace_script_sha256="1" * 64,
                        trace_wrapper_sha256="2" * 64,
                    )

    def test_cli_writes_validated_json_manifest_from_real_trace_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            trace_path = Path(temp_dir) / "trace.log"
            output_path = Path(temp_dir) / "save-api-crossref.json"
            trace_path.write_text(trace_run(), encoding="utf-8")

            result = main([
                "save-api-crossref",
                "--trace-log", str(trace_path),
                "--output", str(output_path),
            ])

            self.assertEqual(result, 0)
            report = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(report["schema"], "lgpe-save-api-crossref-v1")
            self.assertEqual(report["save_worker"]["incoming_references"], 0)
            self.assertEqual(
                report["trace"]["log_sha256"],
                hashlib.sha256(trace_path.read_bytes()).hexdigest(),
            )


if __name__ == "__main__":
    unittest.main()
