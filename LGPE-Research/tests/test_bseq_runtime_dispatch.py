import importlib.util
from pathlib import Path
import unittest


PROJECT = Path(__file__).resolve().parents[1]
SCRIPT = PROJECT / "scripts" / "research" / "build_bseq_runtime_dispatch.py"
SPEC = importlib.util.spec_from_file_location("bseq_runtime_dispatch", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
DISPATCH = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DISPATCH)


class BseqRuntimeDispatchTests(unittest.TestCase):
    def test_latest_bounded_table_block_is_parsed(self):
        log = """DISPATCH_TABLE\tcell=7101608df8\ttable=71015d4c70\tmax_slots=2
DISPATCH_SLOT\tindex=0\taddress=71015d4c70\ttarget=7100ada060\texecutable=true\tfunction=<none>
DISPATCH_SLOT\tindex=1\taddress=71015d4c78\ttarget=7100ada070\texecutable=true\tfunction=<none>
DISPATCH_TABLE_SUMMARY\tcell=7101608df8\tinspected=2\texecutable_targets=2\tterminating_nonexec_run=0
"""
        slots, summary = DISPATCH.parse_latest_dispatch_slots(log)
        self.assertEqual([slot["index"] for slot in slots], [0, 1])
        self.assertEqual(slots[0]["target_address"], 0x7100ADA060)
        self.assertEqual(summary["table_address"], "0x71015d4c70")
        self.assertFalse(summary["length_proven"])

    def test_latest_table_is_selected_when_log_has_prior_runs(self):
        prior = """DISPATCH_TABLE\tcell=7101608df8\ttable=7100001000\tmax_slots=1
DISPATCH_SLOT\tindex=0\taddress=7100001000\ttarget=7100002000\texecutable=true\tfunction=<none>
DISPATCH_TABLE_SUMMARY\tcell=7101608df8\tinspected=1\texecutable_targets=1\tterminating_nonexec_run=0
"""
        current = """DISPATCH_TABLE\tcell=7101608df8\ttable=71015d4c70\tmax_slots=1
DISPATCH_SLOT\tindex=0\taddress=71015d4c70\ttarget=7100ada060\texecutable=true\tfunction=<none>
DISPATCH_TABLE_SUMMARY\tcell=7101608df8\tinspected=1\texecutable_targets=1\tterminating_nonexec_run=0
"""
        slots, summary = DISPATCH.parse_latest_dispatch_slots(prior + current)
        self.assertEqual(summary["table_address"], "0x71015d4c70")
        self.assertEqual(slots[0]["target_address"], 0x7100ADA060)

    def test_non_executable_entry_fails_the_cross_reference(self):
        log = """DISPATCH_TABLE\tcell=7101608df8\ttable=71015d4c70\tmax_slots=1
DISPATCH_SLOT\tindex=0\taddress=71015d4c70\ttarget=00000000\texecutable=false\tfunction=<none>
DISPATCH_TABLE_SUMMARY\tcell=7101608df8\tinspected=1\texecutable_targets=0\tterminating_nonexec_run=1
"""
        with self.assertRaisesRegex(ValueError, "non-code entry"):
            DISPATCH.parse_latest_dispatch_slots(log)

    def test_missing_table_summary_is_rejected(self):
        log = "DISPATCH_TABLE\tcell=7101608df8\ttable=71015d4c70\tmax_slots=1\n"
        with self.assertRaisesRegex(ValueError, "summary is incomplete"):
            DISPATCH.parse_latest_dispatch_slots(log)


if __name__ == "__main__":
    unittest.main()
