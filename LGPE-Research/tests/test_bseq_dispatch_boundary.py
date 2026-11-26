import importlib.util
from pathlib import Path
import unittest


PROJECT = Path(__file__).resolve().parents[1]
MODULE = PROJECT / "src" / "lgpe_research" / "bseq_dispatch_boundary.py"
SPEC = importlib.util.spec_from_file_location("bseq_dispatch_boundary", MODULE)
assert SPEC is not None and SPEC.loader is not None
BOUNDARY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BOUNDARY)


def sample_log(*, main_sha=None, instruction="ret", bytes_le="c0 03 5f d6", slot_count=2):
    main_sha = main_sha or BOUNDARY.MAIN_SHA256
    slots = [
        "INFO InspectBseqDispatchBoundary.java> EXTRA_DISPATCH_SLOT\tindex=256\taddress=71015d5470\ttarget=7100aef450\texecutable=true (GhidraScript)",
        "INFO InspectBseqDispatchBoundary.java> EXTRA_DISPATCH_SLOT\tindex=257\taddress=71015d5478\ttarget=00000000\texecutable=false (GhidraScript)",
    ][:slot_count]
    trailing = 0 if slot_count == 1 else 1
    return "\n".join([
        f"INFO InspectBseqDispatchBoundary.java> BUILD\tmain_sha256={main_sha}\timage_base=0x7100000000\tgame=Pokemon-Lets-Go-Pikachu\tversion=1.0.2\tnca_id=2b7730a9e56498bbafac2002d4908c6b (GhidraScript)",
        f"INFO InspectBseqDispatchBoundary.java> TARGET_INSTRUCTION\taddress=7100ada060\tmnemonic={instruction}\tlength=4\tbytes_le={bytes_le}\ttext={instruction} (GhidraScript)",
        "INFO InspectBseqDispatchBoundary.java> TARGET_INCOMING_REF\tfrom=71015d4c70\ttype=DATA\toperand=0 (GhidraScript)",
        "INFO InspectBseqDispatchBoundary.java> TARGET_INCOMING_SUMMARY\taddress=7100ada060\tcount=1 (GhidraScript)",
        *slots,
        f"INFO InspectBseqDispatchBoundary.java> EXTRA_DISPATCH_SUMMARY\tcell=7101608df8\ttable=71015d4c70\tfirst_index=256\tinspected={slot_count}\texecutable_targets=1\ttrailing_nonexec={trailing}\tmax_extra_slots=4096\tstop_reason=unmapped_or_uninitialized_slot\tfull_table_length_proven=false (GhidraScript)",
        f"INFO InspectBseqDispatchBoundary.java> SUMMARY\tmain_sha256={main_sha}\tread_only_source=true\tread_only_project=true (GhidraScript)",
    ])


class BseqDispatchBoundaryTests(unittest.TestCase):
    KWARGS = {
        "script_sha256": "1" * 64,
        "wrapper_sha256": "2" * 64,
        "log_sha256": "3" * 64,
    }

    def test_valid_probe_preserves_conservative_length_unknown(self):
        report = BOUNDARY.build_bseq_dispatch_boundary_report(sample_log(), **self.KWARGS)
        self.assertEqual(report["target_probe"]["instruction"], "ret")
        self.assertEqual(report["target_probe"]["instruction_bytes_le"], "c0 03 5f d6")
        self.assertEqual(report["extended_pointer_scan"]["inspected_slots"], 2)
        self.assertFalse(report["extended_pointer_scan"]["full_table_length_proven"])

    def test_wrong_main_build_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "expected LGPE Pikachu 1.0.2 main"):
            BOUNDARY.build_bseq_dispatch_boundary_report(sample_log(main_sha="0" * 64), **self.KWARGS)

    def test_wrong_instruction_encoding_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "RET instruction"):
            BOUNDARY.build_bseq_dispatch_boundary_report(
                sample_log(instruction="br", bytes_le="00 02 1f d6"), **self.KWARGS
            )

    def test_incomplete_slot_records_are_rejected(self):
        log = sample_log().replace("inspected=2", "inspected=3")
        with self.assertRaisesRegex(ValueError, "slot count"):
            BOUNDARY.build_bseq_dispatch_boundary_report(log, **self.KWARGS)

    def test_missing_read_only_summary_is_rejected(self):
        log = sample_log().replace("read_only_project=true", "read_only_project=false")
        with self.assertRaisesRegex(ValueError, "read-only summary"):
            BOUNDARY.build_bseq_dispatch_boundary_report(log, **self.KWARGS)


if __name__ == "__main__":
    unittest.main()
