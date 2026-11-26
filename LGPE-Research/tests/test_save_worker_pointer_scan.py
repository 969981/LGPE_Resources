import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from lgpe_research.cli import main
from lgpe_research.save_worker_pointer_scan import build_save_worker_pointer_scan_report


MAIN_SHA256 = "1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8"


def trace_run(main_sha256=MAIN_SHA256, read_only="true", source_unchanged="true"):
    return f"""
2026-10-30 INFO ScanSaveWorkerPointers.java> TARGET\t7100024d70\tSAVE_WORKER\tfunction=FUN_7100024d70
2026-10-30 INFO ScanSaveWorkerPointers.java> TARGET_XREF_SUMMARY\tSAVE_WORKER\tcount=0
2026-10-30 INFO ScanSaveWorkerPointers.java> TARGET\t7100027200\tSAVE_ID_HELPER\tfunction=FUN_7100027200
2026-10-30 INFO ScanSaveWorkerPointers.java> TARGET_XREF_SUMMARY\tSAVE_ID_HELPER\tcount=2
2026-10-30 INFO ScanSaveWorkerPointers.java> TARGET\t7100027440\tQUEUE_HELPER\tfunction=FUN_7100027440
2026-10-30 INFO ScanSaveWorkerPointers.java> TARGET_XREF_SUMMARY\tQUEUE_HELPER\tcount=1
2026-10-30 INFO ScanSaveWorkerPointers.java> TARGET\t71000275f0\tSTATUS_HELPER\tfunction=FUN_71000275f0
2026-10-30 INFO ScanSaveWorkerPointers.java> TARGET_XREF_SUMMARY\tSTATUS_HELPER\tcount=1
2026-10-30 INFO ScanSaveWorkerPointers.java> POINTER_CANDIDATE\tIMAGE_OFFSET_DWORD\t.rela.plt\t7100ee83f3\tSAVE_ID_HELPER\t->\t7100027200
2026-10-30 INFO ScanSaveWorkerPointers.java> POINTER_CANDIDATE\tIMAGE_OFFSET_DWORD\t.hash\t7100eeadeb\tSAVE_ID_HELPER\t->\t7100027200
2026-10-30 INFO ScanSaveWorkerPointers.java> TARGET_SCAN_SUMMARY\tSAVE_WORKER\tabsolute_qword=0\timage_offset_dword=0
2026-10-30 INFO ScanSaveWorkerPointers.java> TARGET_SCAN_SUMMARY\tSAVE_ID_HELPER\tabsolute_qword=0\timage_offset_dword=2
2026-10-30 INFO ScanSaveWorkerPointers.java> TARGET_SCAN_SUMMARY\tQUEUE_HELPER\tabsolute_qword=0\timage_offset_dword=0
2026-10-30 INFO ScanSaveWorkerPointers.java> TARGET_SCAN_SUMMARY\tSTATUS_HELPER\tabsolute_qword=0\timage_offset_dword=0
2026-10-30 INFO ScanSaveWorkerPointers.java> QWORD_SCAN_SUMMARY\tmatches=0
2026-10-30 INFO ScanSaveWorkerPointers.java> IMAGE_OFFSET_SCAN_SUMMARY\tmatches=2
2026-10-30 INFO ScanSaveWorkerPointers.java> ADDRESS_PAGE_CANDIDATE\t7100024010\tADRP X8,0x7100024000\tregister=x8
2026-10-30 INFO ScanSaveWorkerPointers.java> PAGE_PLUS_OFFSET_CANDIDATE\t7100024010\t7100024014\tregister=x8\tADD X8,X8,#0xd70
2026-10-30 INFO ScanSaveWorkerPointers.java> ADDRESS_MATERIALIZATION_SUMMARY\texecutable_blocks=1\tinstruction_count=5\tadr_adrp=2\tpage_candidates=3\tpage_plus_offset_candidates=1\texact_worker_candidates=1\tcandidate_lines=3\tcandidate_output_truncated=false
2026-10-30 INFO ScanSaveWorkerPointers.java> SUMMARY\tmain_sha256={main_sha256}\timage_base=0x7100000000\tinitialized_blocks=18\tbytes_scanned=23113044\tcandidate_lines=2\tcandidate_output_truncated=false\tsourceHashUnchanged={source_unchanged}\treadOnly={read_only}
""".strip()


class SaveWorkerPointerScanTests(unittest.TestCase):
    def test_preserves_exact_build_no_hit_counts_and_unassigned_dword_candidates(self):
        report = build_save_worker_pointer_scan_report(
            trace_run(),
            trace_script_sha256="a" * 64,
            trace_wrapper_sha256="b" * 64,
            trace_log_sha256="c" * 64,
        )

        self.assertEqual(report["schema"], "lgpe-save-worker-pointer-scan-v1")
        self.assertEqual(report["status"], "STATIC_POINTER_SCAN_ONLY")
        self.assertEqual(report["main"]["sha256"], MAIN_SHA256)
        self.assertEqual(report["scan"]["initialized_blocks"], 18)
        self.assertEqual(report["scan"]["bytes_scanned"], 23113044)
        self.assertEqual(report["address_materialization"]["instruction_count"], 5)
        self.assertEqual(report["address_materialization"]["page_candidates"], 3)
        self.assertEqual(report["address_materialization"]["exact_worker_candidates"], 1)
        self.assertEqual(len(report["page_plus_offset_candidates"]), 1)
        self.assertEqual(
            report["page_plus_offset_candidates"][0]["classification"],
            "UNASSIGNED_PAGE_PLUS_OFFSET_CANDIDATE",
        )
        self.assertEqual(report["targets"]["SAVE_WORKER"]["absolute_qword_matches"], 0)
        self.assertEqual(report["targets"]["SAVE_ID_HELPER"]["image_offset_dword_matches"], 2)
        self.assertEqual(len(report["unassigned_candidates"]), 2)
        self.assertEqual(
            {row["block"] for row in report["unassigned_candidates"]},
            {".rela.plt", ".hash"},
        )
        self.assertEqual(report["interpretation"]["worker_registration"], "UNKNOWN")

    def test_report_selects_latest_trace_run(self):
        older = trace_run().replace("absolute_qword=0", "absolute_qword=7")
        report = build_save_worker_pointer_scan_report(
            older + "\n" + trace_run(),
            trace_script_sha256="a" * 64,
            trace_wrapper_sha256="b" * 64,
            trace_log_sha256="c" * 64,
        )
        self.assertEqual(report["targets"]["SAVE_WORKER"]["absolute_qword_matches"], 0)

    def test_report_rejects_wrong_main_and_unverified_source_integrity(self):
        for transcript, message in (
            (trace_run(main_sha256="0" * 64), "main SHA-256 mismatch"),
            (trace_run(read_only="false"), "source integrity"),
            (trace_run(source_unchanged="false"), "source integrity"),
        ):
            with self.subTest(message=message):
                with self.assertRaisesRegex(ValueError, message):
                    build_save_worker_pointer_scan_report(
                        transcript,
                        trace_script_sha256="a" * 64,
                        trace_wrapper_sha256="b" * 64,
                        trace_log_sha256="c" * 64,
                    )

    def test_cli_hashes_input_log_and_writes_report(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            trace_path = Path(temp_dir) / "trace.log"
            output_path = Path(temp_dir) / "pointer-scan.json"
            trace_path.write_text(trace_run(), encoding="utf-8")

            result = main([
                "save-worker-pointer-scan",
                "--trace-log", str(trace_path),
                "--output", str(output_path),
            ])

            self.assertEqual(result, 0)
            report = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(report["status"], "STATIC_POINTER_SCAN_ONLY")
            self.assertEqual(
                report["trace"]["log_sha256"],
                hashlib.sha256(trace_path.read_bytes()).hexdigest(),
            )


if __name__ == "__main__":
    unittest.main()
