import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from lgpe_research.script_registry_operand_scan import (
    MAIN_SHA256,
    build_script_registry_operand_scan_report,
)
import lgpe_research.cli as cli


def make_evidence(
    project: Path,
    *,
    operand_hits: int = 1,
    program_path: str = "1.0.2/2b7730a9e56498bbafac2002d4908c6b_NCA/0/main",
) -> Path:
    scripts = project / "scripts/ghidra"
    scripts.mkdir(parents=True)
    (scripts / "InspectScriptRegistryOperandScan.java").write_text(
        "// synthetic fixture", encoding="utf-8"
    )
    (scripts / "Run-InspectScriptRegistryOperandScan.ps1").write_text(
        "# synthetic fixture", encoding="utf-8"
    )
    log = project / "logs/ghidra-script-registry-operands-v1.stdout.log"
    log.parent.mkdir(parents=True)
    lines = [
        "2026 INFO InspectScriptRegistryOperandScan.java> PROGRAM\tmain\t"
        f"base=7100000000\t//192.168.1.5/j/ROMS/{program_path} (GhidraScript)",
        "2026 INFO InspectScriptRegistryOperandScan.java> OPERAND_HIT\t"
        "71001a61d0\t71001a61d0\tadrp x0,0x710153c000",
        "2026 INFO InspectScriptRegistryOperandScan.java> CONTEXT\t"
        "71001a61d0\t71001a61d0\tadrp x0,0x710153c000",
        "2026 INFO InspectScriptRegistryOperandScan.java> CONTEXT\t"
        "71001a61d0\t71001a61d4\tadd x0,x0,#0x878",
        "2026 INFO InspectScriptRegistryOperandScan.java> DATA_VALUE\t"
        "MapChangeCoreNamePointer\t710153c878\t0x7100f01b90\ttrue\t.rodata\tfalse\tNONE\tNONE\tqword",
        "2026 INFO InspectScriptRegistryOperandScan.java> DATA_VALUE\t"
        "CaptureCallFunctionPointer\t710153c880\t0x71001a61e0\ttrue\t.text\ttrue\t71001a61e0\t71001a61e0\tqword",
        "2026 INFO InspectScriptRegistryOperandScan.java> DATA_VALUE\t"
        "GetCaptureResultFunctionPointer\t710153c890\t0x71001a64c0\ttrue\t.text\ttrue\t71001a64c0\t71001a64c0\tqword",
        "2026 INFO InspectScriptRegistryOperandScan.java> DATA_VALUE\t"
        "OperandPageCandidate_153ced8\t710153ced8\t0x71001a7b70\ttrue\t.text\ttrue\t71001a7b70\t71001a7b70\tqword",
        "2026 INFO InspectScriptRegistryOperandScan.java> DATA_VALUE\t"
        "OperandPageCandidate_153cf20\t710153cf20\t0x71001a7c00\ttrue\t.text\ttrue\tNONE\t71001a7b70\tqword",
        "2026 INFO InspectScriptRegistryOperandScan.java> DATA_VALUE\t"
        "OperandPageCandidate_153cf68\t710153cf68\t0x71001a7e00\ttrue\t.text\ttrue\tNONE\t71001a7b70\tqword",
        "2026 INFO InspectScriptRegistryOperandScan.java> DATA_VALUE\t"
        "OperandPageCandidate_153cfb0\t710153cfb0\t0x71001a8710\ttrue\t.text\ttrue\t71001a8710\t71001a8710\tqword",
        "2026 INFO InspectScriptRegistryOperandScan.java> DATA_REF\t"
        "MapChangeCoreNamePointer\t710153c878\t71001a61d4\tDATA\t71001a61d0",
        "2026 INFO InspectScriptRegistryOperandScan.java> POINTER_SLOT\t"
        "OperandPageCandidate_153ced8\t0\t71001a7b70\t0x71001a7c00\ttrue\t.text\ttrue\tNONE\t71001a7b70",
        "2026 INFO InspectScriptRegistryOperandScan.java> CODE_TARGET\t"
        "7100193c90\t7100193c90\tbytes=8\tinstructions=2\ttemporary=true",
        "2026 INFO InspectScriptRegistryOperandScan.java> CODE_TARGET_INCOMING\t"
        "7100193c90\t710153ced8\tDATA\tNONE",
        "2026 INFO InspectScriptRegistryOperandScan.java> CODE_TARGET_INSN\t"
        "7100193c90\t7100193c90\t00f3ff2a\tblr x8",
        "2026 INFO InspectScriptRegistryOperandScan.java> CODE_TARGET_INSN\t"
        "7100193c90\t7100193c94\tc0035fd6\tret",
        "2026 INFO InspectScriptRegistryOperandScan.java> CODE_TARGET_INDIRECT_CALL\t"
        "7100193c90\t7100193c90\tblr x8",
        "2026 INFO InspectScriptRegistryOperandScan.java> CODE_TARGET_DECOMPILED_BEGIN\t"
        "7100193c90\tchars=88",
        "2026 INFO InspectScriptRegistryOperandScan.java> CODE_TARGET_SUMMARY\t"
        "uniqueTargets=1\ttemporaryBoundaries=1\tdecompiled=1\tfailures=0",
        "2026 INFO InspectScriptRegistryOperandScan.java> SUMMARY "
        f"instructionCount=2839329 operandHits={operand_hits} ownerCount=1 "
        "decompiled=1 failures=0 readOnlySource=true readOnlyProject=true",
    ]
    log.write_text("\n".join(lines), encoding="utf-8")
    return log


class ScriptRegistryOperandScanTests(unittest.TestCase):
    def test_parses_exact_build_hits_context_and_provenance_hashes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            log = make_evidence(project)

            report = build_script_registry_operand_scan_report(
                project, log, main_sha256=MAIN_SHA256
            )

            self.assertEqual(report["schema"], "lgpe-research.script-registry-operand-scan.v1")
            self.assertEqual(report["status"], "STATIC_PAGE_OPERAND_SCAN_ONLY")
            self.assertEqual(report["trace"]["instruction_count"], 2_839_329)
            self.assertEqual(report["trace"]["operand_hit_count"], 1)
            hit = report["search"]["matches"][0]
            self.assertEqual(hit["main_offset"], "0x1a61d0")
            self.assertEqual(hit["owner"]["main_offset"], "0x1a61d0")
            self.assertEqual(len(hit["context"]), 2)
            self.assertEqual(len(report["search"]["data_cells"]), 7)
            self.assertEqual(len(report["search"]["data_references"]), 1)
            self.assertEqual(len(report["search"]["function_pointer_slot_crosschecks"]), 2)
            self.assertEqual(
                report["search"]["function_pointer_slot_crosschecks"][0]["saved_incoming_reference_count"],
                0,
            )
            self.assertEqual(len(report["search"]["indirect_target_slots"]), 1)
            self.assertEqual(
                report["search"]["data_cells"][1]["target_function_exact"]["main_offset"],
                "0x1a61e0",
            )
            self.assertEqual(report["search"]["code_target_summary"]["uniqueTargets"], 1)
            self.assertEqual(len(report["search"]["code_targets"]), 1)
            self.assertEqual(len(report["search"]["code_targets"][0]["instructions"]), 2)
            self.assertFalse(report["search"]["code_targets"][0]["calls"][0]["direct"])
            self.assertEqual(len(report["trace"]["script_sha256"]), 64)
            self.assertEqual(len(report["trace"]["wrapper_sha256"]), 64)
            self.assertEqual(len(report["trace"]["evidence_log_sha256"]), 64)

    def test_rejects_a_different_main_build(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            log = make_evidence(project)
            with self.assertRaisesRegex(ValueError, "expected LGPE Pikachu 1.0.2 main"):
                build_script_registry_operand_scan_report(
                    project, log, main_sha256="0" * 64
                )

    def test_rejects_a_ghidra_program_from_a_different_nca_path(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            log = make_evidence(project, program_path="1.0.1/other_NCA/0/main")
            with self.assertRaisesRegex(ValueError, "does not identify the expected local 1.0.2 NCA"):
                build_script_registry_operand_scan_report(
                    project, log, main_sha256=MAIN_SHA256
                )

    def test_rejects_summary_count_mismatch(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            log = make_evidence(project, operand_hits=2)
            with self.assertRaisesRegex(ValueError, "summary says 2 operand hits"):
                build_script_registry_operand_scan_report(
                    project, log, main_sha256=MAIN_SHA256
                )

    def test_cli_writes_manifest_from_local_project_layout(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir) / "project"
            game_root = Path(temp_dir) / "game"
            exefs = game_root / "0"
            romfs = game_root / "1"
            exefs.mkdir(parents=True)
            (exefs / "main").write_bytes(b"fixture main")
            romfs.mkdir()
            log = make_evidence(project)
            output = project / "manifests/script-registry-operand-scan.json"

            with patch.object(cli, "PROJECT", project), patch.object(
                cli, "source_dirs", return_value={"exefs": exefs, "romfs": romfs}
            ), patch.object(cli, "sha256", return_value=MAIN_SHA256):
                result = cli.main([
                    "script-registry-operand-scan",
                    "--root", str(game_root),
                    "--trace-log", str(log),
                    "--output", str(output),
                ])

            self.assertEqual(result, 0)
            encoded = output.read_bytes()
            self.assertNotIn(b"\r", encoded)
            report = json.loads(encoded.decode("utf-8"))
            self.assertEqual(report["build"]["main_path"], "0/main")
            self.assertEqual(report["trace"]["operand_hit_count"], 1)


if __name__ == "__main__":
    unittest.main()
