import unittest
from pathlib import Path

from lgpe_research.gfbcol_main_crossref import (
    cross_reference_slot0_candidates,
    summarize_gfbcol_token_owner_trace,
    summarize_gfbcol_token_handler_trace,
)


MAIN_SHA256 = "1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8"


def _main_report():
    return {
        "checks_passed": True,
        "image_base": "0x7100000000",
        "source": {"bytes": 1234, "sha256": MAIN_SHA256},
        "exact_instruction_links": [
            {
                "token": "col_wall",
                "string_address": "0x7100f03218",
                "bl_address": "0x710024f48c",
                "bl_target_address": "0x710000b660",
                "status": "ADDRESS_BYTES_MATCH",
            },
            {
                "token": "col_sky",
                "string_address": "0x7100f03234",
                "bl_address": "0x710024f584",
                "bl_target_address": "0x710000b660",
                "status": "ADDRESS_BYTES_MATCH",
            },
        ],
    }


def _slot0_report():
    return {
        "source_version": "Pokemon Let's Go Pikachu 1.0.2",
        "analysis_status": "HYPOTHESIS_ONLY",
        "schema_status": "UNKNOWN",
        "inventory": {"sha256": "b" * 64, "gfbcol_sources": 2},
        "selection": {"limit": 0, "selected_sources": 2},
        "sources_read": 2,
        "source_failures": [],
        "slot0_child_table_count": 2,
        "valid_string_shape_candidates": 2,
        "unresolved_child_fields": 0,
        "candidate_text_counts": {"col_wall": 1, "material_A": 1},
        "field_names_assigned": False,
        "field_types_assigned": False,
        "entries": [
            {
                "source": "bin/field/model/a.gfbcol",
                "source_sha256": "c" * 64,
                "elements": [
                    {
                        "element_index": 0,
                        "table_offset": 48,
                        "string_candidate": {
                            "classification": "UTF8_NUL_TERMINATED_LENGTH_PREFIX_CANDIDATE",
                            "decoded_text": "col_wall",
                            "length": 8,
                            "raw_bytes_hex": "636f6c5f77616c6c",
                            "target_offset": 80,
                        },
                    }
                ],
            },
            {
                "source": "bin/field/model/b.gfbcol",
                "source_sha256": "d" * 64,
                "elements": [
                    {
                        "element_index": 0,
                        "table_offset": 64,
                        "string_candidate": {
                            "classification": "UTF8_NUL_TERMINATED_LENGTH_PREFIX_CANDIDATE",
                            "decoded_text": "material_A",
                            "length": 10,
                            "raw_bytes_hex": "6d6174657269616c5f41",
                            "target_offset": 96,
                        },
                    }
                ],
            },
        ],
    }


def _trace_log():
    offsets = ("24f48c", "24f4e4", "24f534", "24f584", "24f5d4", "24f624")
    references = "\n".join(
        f"TARGET_XREF\tfrom=main+0x{offset}\ttype=UNCONDITIONAL_CALL"
        "\towner=NONE\tinstruction=bl 0x710000b660"
        for offset in offsets
    )
    contexts = "\n".join(
        f"CALL_CONTEXT\tcallsite=main+0x{offset}\taddress=main+0x{offset}"
        "\towner=NONE\tflow=UNCONDITIONAL_CALL\tassembly=bl 0x710000b660"
        for offset in offsets
    )
    return (
        references
        + "\n" + contexts
        + "\nSUMMARY\tmain_sha256=" + MAIN_SHA256
        + "\thandler=main+0xb660\tincoming_references=225"
        + "\texpected_call_sites=6/6\tinstructions=102\tdirect_calls=5"
        + "\tcontext_instructions=101"
        + "\tsourceHashUnchanged=true\treadOnly=true\tsemantics=UNKNOWN\n"
    )


def _owner_trace_log():
    offsets = ("24f48c", "24f4e4", "24f534", "24f584", "24f5d4", "24f624")
    calls = "\n".join(
        f"INS\tmain+0x{offset}\t00000094\tbl 0x710000b660" for offset in offsets
    )
    tokens = ("col_wall", "col_water", "col_jump", "col_sky", "col_sekichiku", "col_safety")
    helper_calls = "\n".join(
        f'FUN_710000b660(&local,(byte *)"{token}");' for token in tokens
    )
    counter_offsets = ("0x30", "0x34", "0x38", "0x3c", "0x40", "0x44", "0x48", "0x4c")
    increments = "\n".join(
        f"*(int *)(param_1 + {offset}) = *(int *)(param_1 + {offset}) + 1;"
        for offset in counter_offsets
    )
    comparisons = "\n".join("if (lVar3 == param_5) {}" for _ in range(6))
    return (
        "GUARD\tgame=Let's Go Pikachu 1.0.2\tmain_sha256=" + MAIN_SHA256
        + "\tbase=0x7100000000\tread_only=true\n"
        + "ENTRY_XREF\tfrom=main+0x15437d8\ttype=DATA\towner=NONE\tinstruction=NONE\n"
        + "ENTRY_DATA_WINDOW\tcell=main+0x15437d8\tvalue=0x710024f460"
        + "\tblock=.data\twritable=true\texecutable=false\n"
        + "CANDIDATE_FUNCTION\tentry=main+0x24f460\tbytes=564"
        + "\tmin=main+0x24f460\tmax=main+0x24f693\ttemporary_boundary=true\n"
        + calls + "\nDECOMPILED_BEGIN\tmain+0x24f460\tchars=100\n"
        + "long *plVar1;\n*(long *)(local + 0x58);\n"
        + "(**(code **)(*(long *)(local + 0x48) + 0x18))();\n"
        + helper_calls + "\n" + comparisons + "\n"
        + increments + "\n}\nDECOMPILED_END\tmain+0x24f460\n"
        + "SUMMARY\tmain_sha256=" + MAIN_SHA256
        + "\tentry=main+0x24f460\tcall_sites=6/6\tinstructions=141"
        + "\tentry_xrefs=1\ttemporary_boundary=true\tsourceHashUnchanged=true"
        + "\treadOnly=true\tsemantics=UNKNOWN\n"
    )


class GfbcolMainCrossrefTests(unittest.TestCase):
    def test_cross_reference_reports_literal_value_matches_without_assigning_schema(self):
        result = cross_reference_slot0_candidates(_main_report(), _slot0_report())

        self.assertEqual(result["source_version"], "Pokemon Let's Go Pikachu 1.0.2")
        self.assertEqual(result["schema_status"], "UNKNOWN")
        self.assertFalse(result["field_names_assigned"])
        self.assertFalse(result["field_types_assigned"])
        self.assertEqual(result["summary"]["exact_main_tokens"], 2)
        self.assertEqual(result["summary"]["tokens_matching_candidate_strings"], 1)
        self.assertEqual(result["summary"]["matched_candidate_occurrences"], 1)
        self.assertEqual(result["gfbcol_probe"]["source_hashes"], [
            {"source": "bin/field/model/a.gfbcol", "source_sha256": "c" * 64},
            {"source": "bin/field/model/b.gfbcol", "source_sha256": "d" * 64},
        ])
        self.assertEqual(
            [item["decoded_text"] for item in result["gfbcol_probe"]["candidate_observations"]],
            ["col_wall", "material_A"],
        )
        self.assertEqual(
            result["gfbcol_probe"]["candidate_observations"][0]["raw_bytes_hex"],
            "636f6c5f77616c6c",
        )
        by_token = {item["token"]: item for item in result["exact_main_token_candidates"]}
        self.assertEqual(by_token["col_wall"]["candidate_occurrences"], 1)
        self.assertEqual(by_token["col_wall"]["sources"][0]["source"], "bin/field/model/a.gfbcol")
        self.assertEqual(by_token["col_sky"]["candidate_occurrences"], 0)

    def test_rejects_probe_results_with_source_failures(self):
        report = _slot0_report()
        report["source_failures"] = [{"source": "bin/field/model/missing.gfbcol", "error": "missing"}]

        with self.assertRaisesRegex(ValueError, "source failures"):
            cross_reference_slot0_candidates(_main_report(), report)

    def test_rejects_non_exact_main_string_links(self):
        report = _main_report()
        report["exact_instruction_links"][0]["status"] = "HYPOTHESIS_ONLY"

        with self.assertRaisesRegex(ValueError, "exact byte links"):
            cross_reference_slot0_candidates(report, _slot0_report())

    def test_trace_summary_requires_all_six_expected_build_callsites(self):
        result = summarize_gfbcol_token_handler_trace(_trace_log(), MAIN_SHA256)

        self.assertEqual(result["main_sha256"], MAIN_SHA256)
        self.assertEqual(result["handler"], "main+0xb660")
        self.assertEqual(result["incoming_references"], 225)
        self.assertEqual(result["expected_call_sites"], 6)
        self.assertEqual(result["context_instructions"], 101)
        self.assertEqual(result["verified_callsite_offsets"], [
            "24f48c", "24f4e4", "24f534", "24f584", "24f5d4", "24f624",
        ])
        self.assertTrue(result["read_only"])

    def test_trace_summary_rejects_missing_callsite(self):
        trace = _trace_log().replace("main+0x24f624", "main+0x24f628")

        with self.assertRaisesRegex(ValueError, "six expected callsites"):
            summarize_gfbcol_token_handler_trace(trace, MAIN_SHA256)

    def test_owner_trace_reports_the_provisional_exact_build_comparison_chain(self):
        result = summarize_gfbcol_token_owner_trace(_owner_trace_log(), MAIN_SHA256)

        self.assertEqual(result["entry"], "main+0x24f460")
        self.assertEqual(result["function_bytes"], 564)
        self.assertEqual(result["call_sites"], 6)
        self.assertEqual(result["entry_xrefs"], 1)
        self.assertEqual(result["entry_data_cell"], "main+0x15437d8")
        self.assertEqual(result["entry_data_value"], "0x710024f460")
        self.assertEqual(result["token_counter_offsets"], {
            "col_wall": "0x30", "col_water": "0x34", "col_jump": "0x38",
            "col_sky": "0x3c", "col_sekichiku": "0x40", "col_safety": "0x44",
        })
        self.assertEqual(result["fallback_counter_offset"], "0x48")
        self.assertEqual(result["total_counter_offset"], "0x4c")
        self.assertEqual(result["semantics"], "UNKNOWN")

    def test_owner_trace_rejects_an_unverified_or_incomplete_candidate(self):
        trace = _owner_trace_log().replace("call_sites=6/6", "call_sites=5/6")

        with self.assertRaisesRegex(ValueError, "six direct callsites"):
            summarize_gfbcol_token_owner_trace(trace, MAIN_SHA256)

    def test_owner_trace_rejects_code_reference_with_address_and_assembly_fields(self):
        trace = _owner_trace_log().replace(
            "ENTRY_DATA_WINDOW",
            "ENTRY_XREF\tfrom=main+0x24f48c\ttype=UNCONDITIONAL_CALL"
            "\towner=main+0x24f460\tinstruction=bl 0x710024f460\n"
            "ENTRY_DATA_WINDOW",
        ).replace("\tentry_xrefs=1\t", "\tentry_xrefs=2\t")

        with self.assertRaisesRegex(ValueError, "entry reference"):
            summarize_gfbcol_token_owner_trace(trace, MAIN_SHA256)

    def test_owner_trace_rejects_reference_summary_count_mismatch(self):
        trace = _owner_trace_log().replace("entry_xrefs=1", "entry_xrefs=2")

        with self.assertRaisesRegex(ValueError, "entry reference"):
            summarize_gfbcol_token_owner_trace(trace, MAIN_SHA256)

    def test_owner_trace_parses_ghidra_prefixed_reference_lines(self):
        trace = _owner_trace_log().replace(
            "ENTRY_XREF\tfrom=main+0x15437d8\ttype=DATA\towner=NONE\tinstruction=NONE",
            "INFO  InspectGfbcolTokenOwner.java> ENTRY_XREF"
            "\tfrom=main+0x15437d8\ttype=DATA\towner=NONE"
            "\tinstruction=NONE (GhidraScript)  ",
        )

        self.assertEqual(
            summarize_gfbcol_token_owner_trace(trace, MAIN_SHA256)["entry_xrefs"], 1
        )

    def test_ghidra_wrappers_clear_append_only_script_logs_before_rerun(self):
        project = Path(__file__).resolve().parents[1]
        for wrapper in (
            "scripts/ghidra/Run-InspectGfbcolTokenHandler.ps1",
            "scripts/ghidra/Run-InspectGfbcolTokenOwner.ps1",
        ):
            script = (project / wrapper).read_text(encoding="utf-8")
            clear = script.index("Remove-Item -LiteralPath $ScriptLogPath")
            launch = script.index("[System.Diagnostics.Process]::Start($StartInfo)")
            self.assertLess(clear, launch, wrapper)


if __name__ == "__main__":
    unittest.main()
