import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from lgpe_research.capture_getter_crossref import (
    MAIN_SHA256,
    build_capture_getter_crossref_report,
)
import lgpe_research.cli as cli


PROJECT = Path(__file__).resolve().parents[1]


def trace_run(*, main_sha=MAIN_SHA256, readonly="true", wrong_count=False, wrong_owner=False):
    refs = [
        ("main+0x1a64c0", "main+0x153c890", "DATA", "NONE"),
        ("main+0x1aae40", "main+0x1a6524", "UNCONDITIONAL_CALL", "main+0x1a64c0"),
        ("main+0x28e7f0", "main+0x15472a0", "DATA", "NONE"),
        ("main+0x28eb60", "main+0x28e934", "UNCONDITIONAL_CALL", "main+0x28e7f0"),
        ("main+0x28ee10", "main+0x3059d4", "UNCONDITIONAL_CALL", "main+0x305970"),
        ("main+0x28ee10", "main+0x28e978", "UNCONDITIONAL_CALL", "NONE" if wrong_owner else "main+0x28e7f0"),
        ("main+0x28ee10", "main+0x319fe0", "UNCONDITIONAL_CALL", "main+0x319f80"),
        ("main+0x28ee10", "main+0x8549fc", "UNCONDITIONAL_CALL", "NONE"),
        ("main+0x305970", "main+0x2fdf34", "UNCONDITIONAL_CALL", "main+0x2fd8a0"),
        ("main+0x305970", "main+0x2fdf80", "UNCONDITIONAL_CALL", "main+0x2fd8a0"),
        ("main+0x319f80", "main+0x319cc4", "UNCONDITIONAL_CALL", "NONE"),
    ]
    counts = {
        "main+0x1a64c0": 1,
        "main+0x1aae40": 1,
        "main+0x28e7f0": 1,
        "main+0x28eb60": 1,
        "main+0x28ee10": 3 if wrong_count else 4,
        "main+0x305970": 2,
        "main+0x319f80": 1,
    }
    rows = [
        f"INFO InspectCaptureGetterCallers.java> BUILD\tgame=Pokemon-Lets-Go-Pikachu\tversion=1.0.2\tnca_id=2b7730a9e56498bbafac2002d4908c6b\timage_base=0x7100000000\tmain_sha256={main_sha} (GhidraScript)",
        "INFO InspectCaptureGetterCallers.java> SCOPE\tDirect getter-handler callers and one caller layer; no capture-result semantics inferred. (GhidraScript)",
    ]
    rows.extend(
        f"INFO InspectCaptureGetterCallers.java> INCOMING\ttarget={target}\tfrom={source}\ttype={kind}\towner={owner}\tinstruction=bl (GhidraScript)"
        for target, source, kind, owner in refs
    )
    rows.extend(
        f"INFO InspectCaptureGetterCallers.java> INCOMING_SUMMARY\ttarget={target}\tcount={count} (GhidraScript)"
        for target, count in counts.items()
    )
    rows.extend([
        "INFO InspectCaptureGetterCallers.java> TEMPORARY_FUNCTION_BOUNDARY\tmain+0x28e7f0\tread_only_database_changes_discarded=true (GhidraScript)",
        "INFO InspectCaptureGetterCallers.java> FUNCTION_BEGIN\tmain+0x1aae40\tbytes=480 (GhidraScript)",
        "INFO InspectCaptureGetterCallers.java> FUNCTION_BEGIN\tmain+0x1a64c0\tbytes=488 (GhidraScript)",
        "INFO InspectCaptureGetterCallers.java> FUNCTION_BEGIN\tmain+0x28e7f0\tbytes=868 (GhidraScript)",
        "INFO InspectCaptureGetterCallers.java> FUNCTION_BEGIN\tmain+0x28eb60\tbytes=676 (GhidraScript)",
        "INFO InspectCaptureGetterCallers.java> FUNCTION_BEGIN\tmain+0x28ee10\tbytes=480 (GhidraScript)",
        "INFO InspectCaptureGetterCallers.java> FUNCTION_BEGIN\tmain+0x305970\tbytes=1384 (GhidraScript)",
        "INFO InspectCaptureGetterCallers.java> FUNCTION_BEGIN\tmain+0x319f80\tbytes=680 (GhidraScript)",
        "INFO InspectCaptureGetterCallers.java> DECOMPILED_BEGIN\tmain+0x1a64c0\tinstructions=122 (GhidraScript)",
        "INFO InspectCaptureGetterCallers.java> uVar11 = *(undefined8 *)(param_2 + 8); (GhidraScript)",
        "INFO InspectCaptureGetterCallers.java> FUN_71001aae40(&local_68,lVar10,*(long **)(*(long *)PTR_DAT_71015faab8 + 0x68)); (GhidraScript)",
        "INFO InspectCaptureGetterCallers.java> *(undefined8 *)(lVar2 + 200) = uVar11; (GhidraScript)",
        "INFO InspectCaptureGetterCallers.java> return 0; (GhidraScript)",
        "INFO InspectCaptureGetterCallers.java> DECOMPILED_END\tmain+0x1a64c0 (GhidraScript)",
        "INFO InspectCaptureGetterCallers.java> DECOMPILED_BEGIN\tmain+0x28e7f0\tinstructions=217 (GhidraScript)",
        "INFO InspectCaptureGetterCallers.java> case 2: (GhidraScript)",
        "INFO InspectCaptureGetterCallers.java> FUN_710028eb60(param_1); (GhidraScript)",
        "INFO InspectCaptureGetterCallers.java> case 3: (GhidraScript)",
        "INFO InspectCaptureGetterCallers.java> FUN_710028ee10(&lStack_68,lVar14,plVar15); (GhidraScript)",
        "INFO InspectCaptureGetterCallers.java> DECOMPILED_END\tmain+0x28e7f0 (GhidraScript)",
        "INFO InspectCaptureGetterCallers.java> DECOMPILED_BEGIN\tmain+0x28ee10\tinstructions=120 (GhidraScript)",
        "INFO InspectCaptureGetterCallers.java> puVar2 = (undefined8 *)(**(code **)(*param_3 + 0x10))(param_3,0x3b0,8); (GhidraScript)",
        "INFO InspectCaptureGetterCallers.java> lVar3 = *(long *)(param_2 + 0x68); (GhidraScript)",
        "INFO InspectCaptureGetterCallers.java> lVar3 = *(long *)(param_2 + 0x70); (GhidraScript)",
        "INFO InspectCaptureGetterCallers.java> *param_1 = lVar1; (GhidraScript)",
        "INFO InspectCaptureGetterCallers.java> DECOMPILED_END\tmain+0x28ee10 (GhidraScript)",
        "INFO InspectCaptureGetterCallers.java> CALL\tfrom=main+0x28e978\ttarget=main+0x28ee10\tcallee=main+0x28ee10\tinstruction=bl (GhidraScript)",
        "INFO InspectCaptureGetterCallers.java> CALL\tfrom=main+0x1a6524\ttarget=main+0x1aae40\tcallee=main+0x1aae40\tinstruction=bl (GhidraScript)",
        "INFO InspectCaptureGetterCallers.java> CALL\tfrom=main+0x3059d4\ttarget=main+0x28ee10\tcallee=main+0x28ee10\tinstruction=bl (GhidraScript)",
        "INFO InspectCaptureGetterCallers.java> CALL\tfrom=main+0x319fe0\ttarget=main+0x28ee10\tcallee=main+0x28ee10\tinstruction=bl (GhidraScript)",
        "INFO InspectCaptureGetterCallers.java> UNOWNED_CALLSITE\taddress=main+0x8549fc\towner=NONE\tinstruction=bl 0x710028ee10 (GhidraScript)",
    ])
    for address, instruction in (
        ("main+0x8549f0", "ldr x1,[x8, #0x68]"),
        ("main+0x8549f4", "add x8,sp,#0x50"),
        ("main+0x8549f8", "mov x0,x22"),
        ("main+0x8549fc", "bl 0x710028ee10"),
        ("main+0x854a00", "ldr x8,[sp, #0x58]"),
        ("main+0x854a04", "str x8,[sp, #0x20]"),
    ):
        rows.append(
            f"INFO InspectCaptureGetterCallers.java> UNOWNED_WINDOW\taddress={address}\towner=NONE\tbytes=00000000\tinstruction={instruction} (GhidraScript)"
        )
    rows.append(
        f"INFO InspectCaptureGetterCallers.java> SUMMARY\tmain_sha256={main_sha}\tdecompiled=7\tinstructions=1264\tdirectCalls=71\ttemporaryFunctions=1\tfailures=0\treadOnlySource={readonly}\treadOnlyProject=true (GhidraScript)"
    )
    return "\n".join(rows)


class CaptureGetterCrossReferenceTests(unittest.TestCase):
    KWARGS = {
        "script_sha256": "a" * 64,
        "wrapper_sha256": "b" * 64,
        "log_sha256": "c" * 64,
    }

    def test_report_keeps_shared_callers_and_unknown_capture_semantics(self):
        report = build_capture_getter_crossref_report(trace_run(), **self.KWARGS)
        self.assertEqual(report["status"], "STATIC_SHARED_HANDLER_CALLERS")
        self.assertEqual(report["shared_handler"]["direct_incoming_reference_count"], 4)
        self.assertEqual(report["capture_result_api_wrapper"]["direct_handler_callsite"], "main+0x1a6524")
        self.assertEqual(report["temporary_candidate"]["boundary_persisted"], False)
        self.assertEqual(report["interpretation"]["handler_specific_to_capture"], "NOT_ESTABLISHED")

    def test_rejects_wrong_game_build(self):
        with self.assertRaisesRegex(ValueError, "expected LGPE Pikachu 1.0.2"):
            build_capture_getter_crossref_report(trace_run(main_sha="0" * 64), **self.KWARGS)

    def test_rejects_non_read_only_trace(self):
        with self.assertRaisesRegex(ValueError, "read-only summary"):
            build_capture_getter_crossref_report(trace_run(readonly="false"), **self.KWARGS)

    def test_rejects_inconsistent_reference_count_and_wrong_owner(self):
        with self.assertRaisesRegex(ValueError, "count disagrees"):
            build_capture_getter_crossref_report(trace_run(wrong_count=True), **self.KWARGS)
        with self.assertRaisesRegex(ValueError, "direct callers"):
            build_capture_getter_crossref_report(trace_run(wrong_owner=True), **self.KWARGS)

    def test_cli_writes_hash_attributed_manifest_from_trace(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            temp_project = temp_root / "project"
            ghidra_dir = temp_project / "scripts" / "ghidra"
            ghidra_dir.mkdir(parents=True)
            for filename in (
                "InspectCaptureGetterCallers.java",
                "Run-InspectCaptureGetterCallers.ps1",
            ):
                shutil.copyfile(
                    PROJECT / "scripts" / "ghidra" / filename,
                    ghidra_dir / filename,
                )
            trace_path = temp_root / "trace.log"
            output_path = temp_project / "manifests" / "capture-getter-crossref-test.json"
            trace_path.write_text(trace_run(), encoding="utf-8")
            with patch.object(cli, "PROJECT", temp_project):
                result = cli.main([
                    "capture-getter-crossref",
                    "--trace-log", str(trace_path),
                    "--output", str(output_path),
                ])
                self.assertEqual(result, 0)
                report = json.loads(output_path.read_text(encoding="utf-8"))
                self.assertEqual(report["schema"], "lgpe-research.capture-getter-callers.v2")
                self.assertEqual(
                    report["trace"]["evidence_log_sha256"],
                    hashlib.sha256(trace_path.read_bytes()).hexdigest(),
                )


if __name__ == "__main__":
    unittest.main()
