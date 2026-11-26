import unittest

from lgpe_research.core import NCA, PROJECT, VERSION
from lgpe_research.spawn_rng_crossref import (
    build_spawn_rng_crossref,
    parse_species_enum,
    species_field_values,
)

_LOCAL_GAME_ROOT = PROJECT.parent
_LOCAL_EVIDENCE = [
    _LOCAL_GAME_ROOT / VERSION / NCA / "0" / "main",
    PROJECT / "decoded" / VERSION / "romfs" / "bin/pokelib/personal/personal_total.json",
    PROJECT / "decoded" / VERSION / "romfs" / "bin/field/param/encount/encount_data_p.json",
    PROJECT / "decoded" / VERSION / "romfs" / "bin/field/param/encount/encount_data_e.json",
    PROJECT / "decoded" / VERSION / "romfs" / "bin/script_event_data/event_encount.json",
]


class SpawnRngCrossReferenceTests(unittest.TestCase):
    def test_parses_implicit_ordinals_and_comments(self):
        parsed = parse_species_enum("""
            public enum Species : ushort {
                None,
                First, // ordinal one
                Second = 144,
                Third,
            }
        """)
        self.assertEqual(parsed, {0: "None", 1: "First", 144: "Second", 145: "Third"})

    def test_rejects_duplicate_enum_ordinals(self):
        with self.assertRaisesRegex(ValueError, "duplicate Species enum ordinal"):
            parse_species_enum("enum Species : ushort { First = 144, Second = 144 }")

    def test_collects_only_integer_fields_named_species(self):
        hits = species_field_values({
            "tables": [{"slots": [{"Species": 144}, {"Species": True}, {"Form": 144}]}],
            "note": "Species 144",
        })
        self.assertEqual(hits, [{"path": "$.tables[0].slots[0].Species", "value": 144}])

    @unittest.skipUnless(all(path.is_file() for path in _LOCAL_EVIDENCE), "local LGPE 1.0.2 evidence unavailable")
    def test_local_hash_pinned_cross_reference_stays_unassigned(self):
        report = build_spawn_rng_crossref(PROJECT, _LOCAL_GAME_ROOT)
        self.assertEqual(report["schema"], "lgpe-spawn-rng-value-crossref-v10")
        self.assertEqual(report["status"], "CORRELATED_UNASSIGNED")
        chain = report["code_evidence"]["event_static_loader_chain"]
        self.assertEqual(chain["path_string_xref"], "main+0x2ba87c -> main+0x2ba7c0")
        self.assertEqual(chain["runtime_execution"], "UNVERIFIED")
        self.assertEqual(chain["path_string_direct_xref_count"], 1)
        self.assertEqual(chain["record_table_build"]["input_record_stride_bytes"], 64)
        handler = report["code_evidence"]["event_static_handler_cross_reference"]
        self.assertEqual(handler["handler_function_va"], "main+0x28f430")
        self.assertEqual(handler["handler_owner_function_va"], "main+0x28f300")
        self.assertEqual(handler["record_lookup_va"], "main+0x2baba0")
        self.assertEqual(handler["runtime_execution"], "UNVERIFIED")
        owner_reference = handler["handler_owner_entry_data_reference"]
        self.assertEqual(owner_reference["stored_value"], "main+0x28f300")
        self.assertEqual(owner_reference["window_semantics"], "UNKNOWN")
        self.assertEqual(
            [
                (
                    item["pointer_cell"], item["target"], item["exact_function"],
                    item["containing_function"], item["observed_instructions"][0]["text"],
                )
                for item in owner_reference["pointer_target_code_observations"]
            ],
            [
                (
                    "main+0x1547348", "main+0x2a90", "NOT_DEFINED_IN_SAVED_DATABASE",
                    "NOT_DEFINED_IN_SAVED_DATABASE", "ldr x8,[x0, #0x58]",
                ),
                (
                    "main+0x1547350", "main+0x11160", "FUN_7100011160",
                    "FUN_7100011160", "stp x29,x30,[sp, #-0x10]!",
                ),
                (
                    "main+0x1547358", "main+0x28f2e0", "NOT_DEFINED_IN_SAVED_DATABASE",
                    "NOT_DEFINED_IN_SAVED_DATABASE", "mov w0,#0x1",
                ),
                (
                    "main+0x1547360", "main+0x28f2f0", "NOT_DEFINED_IN_SAVED_DATABASE",
                    "NOT_DEFINED_IN_SAVED_DATABASE", "ret",
                ),
                (
                    "main+0x1547368", "main+0x28f300", "FUN_710028f300",
                    "FUN_710028f300", "stp x22,x21,[sp, #-0x30]!",
                ),
                (
                    "main+0x1547370", "main+0x28f6c0", "NOT_DEFINED_IN_SAVED_DATABASE",
                    "NOT_DEFINED_IN_SAVED_DATABASE", "ret",
                ),
            ],
        )
        expected_incoming_counts = {
            "main+0x2a90": 1175,
            "main+0x11160": 65,
            "main+0x28f2e0": 1,
            "main+0x28f2f0": 1,
            "main+0x28f300": 1,
            "main+0x28f6c0": 1,
        }
        for item in owner_reference["pointer_target_code_observations"]:
            incoming = item["incoming_reference_summary"]
            self.assertEqual(incoming["reference_count"], expected_incoming_counts[item["target"]])
            self.assertEqual(incoming["reference_types"], {"DATA": incoming["reference_count"]})
            self.assertEqual(incoming["owner_labels"], {"<no-function>": incoming["reference_count"]})
            self.assertIn(item["pointer_cell"], incoming["sample_from"])
        self.assertEqual(owner_reference["direct_references_to_cell_in_saved_database"], 0)
        self.assertEqual(
            owner_reference["page_base_reference_summary"]["reference_count"], 5
        )
        self.assertEqual(
            owner_reference["page_base_reference_summary"]["reference_types"],
            {"DATA": 4, "READ": 1},
        )
        self.assertEqual(
            handler["handler_owner_direct_calls"],
            [
                "main+0x28f3ec -> main+0x2ba7c0",
                "main+0x28f400 -> main+0x2ba980",
                "main+0x28f40c -> main+0x28f430",
            ],
        )
        self.assertEqual(
            handler["normalization"]["form_internal_offset"],
            "0x0c (u8)",
        )
        self.assertEqual(
            handler["gender_override"]["helper_return_expression"],
            "byte [param+0x111]",
        )
        self.assertEqual(
            handler["gender_override"]["outcomes"],
            [
                {"first_helper_return": 0, "gender_value": 1, "gender_enum_name": "Male"},
                {
                    "first_helper_return_nonzero": True,
                    "second_helper_return": 1,
                    "gender_value": 2,
                    "gender_enum_name": "Female",
                },
            ],
        )
        self.assertEqual(
            handler["gender_override"]["helper_call_sites"],
            ["main+0x28f4fc", "main+0x28f508"],
        )
        self.assertEqual(handler["gender_override"]["opaque_input_semantics"], "UNKNOWN")
        gender = handler["gender_override"]
        self.assertEqual(gender["setter_function_va"], "main+0x1ca020")
        self.assertEqual(gender["setter_body"], "byte [param+0x111] = param_2")
        self.assertEqual(
            gender["setter_caller_entry_data_reference"]["stored_value"], "main+0xe420"
        )
        self.assertEqual(
            gender["setter_caller_entry_data_reference"]["direct_references_to_cell_in_saved_database"],
            0,
        )
        self.assertEqual(
            gender["setter_caller_entry_data_reference"]["runtime_dispatch"], "UNVERIFIED"
        )
        self.assertEqual(
            gender["setter_caller_entry_data_reference"]["page_base_reference_summary"],
            {
                "address": "main+0x1527000",
                "reference_count": 375,
                "reference_types": {"DATA": 178, "PARAM": 197},
                "unique_owners": 82,
                "sample_from_addresses": [
                    "main+0xc9ba0c", "main+0x5fb254", "main+0x36a9b8",
                    "main+0xcaa1cc", "main+0x469578",
                ],
                "specific_cell_use": "NOT_ESTABLISHED",
            },
        )
        self.assertEqual(
            gender["setter_caller_entry_data_reference"]["window_qwords"][4],
            "0x710000e420",
        )
        self.assertEqual(
            gender["setter_direct_call_reference"],
            {
                "from": "main+0xf058",
                "caller": "main+0xe420",
                "argument_context": ["mov w1,#0x1", "mov x0,x20"],
                "observed_second_argument": "constant 1",
            },
        )
        self.assertEqual(gender["setter_decompile_comparison"]["status"], "UNRESOLVED")
        self.assertTrue(gender["setter_decompile_comparison"]["instruction_context_conflict"])
        self.assertEqual(
            gender["setter_decompile_comparison"]["decompiler_warning"],
            "Type propagation algorithm not settling",
        )
        self.assertEqual(gender["related_object_paths"]["object_identity"], "UNRESOLVED")
        self.assertEqual(
            handler["branch_tests"],
            [
                {
                    "normalized_species_u32": 0x85,
                    "normalized_form_u8": 1,
                    "species_enum_name": "Eevee",
                    "source_matches": [
                        {
                            "index": 1, "Species": 133, "Species_enum_name": "Eevee", "Form": 1,
                            "Level": 5, "Gender": 0, "Gender_enum_name": "Random",
                        }
                    ],
                },
                {
                    "normalized_species_u32": 0x19,
                    "normalized_form_u8": 8,
                    "species_enum_name": "Pikachu",
                    "source_matches": [
                        {
                            "index": 0, "Species": 25, "Species_enum_name": "Pikachu", "Form": 8,
                            "Level": 5, "Gender": 0, "Gender_enum_name": "Random",
                        }
                    ],
                },
            ],
        )
        self.assertEqual(
            chain["record_lookup_direct_callers"],
            [
                {"from": "main+0x289db4", "owner": None},
                {"from": "main+0x28ebe8", "owner": "main+0x28eb60"},
                {"from": "main+0x28f4a8", "owner": "main+0x28f430"},
            ],
        )
        self.assertFalse(chain["direct_call_to_rng_candidate"])
        self.assertEqual(
            [row["enum_name"] for row in report["personal_total"]["rows"]],
            ["Articuno", "Zapdos", "Moltres"],
        )
        self.assertEqual(
            [len(table["selector_value_hits"]) for table in report["ordinary_encounter_tables"].values()],
            [0, 0],
        )
        self.assertEqual(
            report["event_static_encounters"]["selector_value_hits"],
            [
                {"index": 2, "Species": 144, "Form": 0, "Level": 50},
                {"index": 3, "Species": 145, "Form": 0, "Level": 50},
                {"index": 4, "Species": 146, "Form": 0, "Level": 50},
            ],
        )
        opaque_pairs = report["code_evidence"]["event_record_opaque_pair_cross_reference"]
        self.assertEqual(opaque_pairs["handler_function_va"], "main+0x28eb60")
        self.assertEqual(opaque_pairs["record_table_build_va"], "main+0x2baa10")
        self.assertEqual(opaque_pairs["record_table_build"]["input_record_stride_bytes"], 64)
        self.assertEqual(opaque_pairs["record_table_build"]["internal_record_copy_bytes"], 89)
        self.assertEqual(
            opaque_pairs["consumer_object_mapping"],
            [
                {
                    "normalized_record_offset": "0x20",
                    "object_offset": "0x2a0",
                    "accessor_va": "main+0x2f6b60",
                    "source_fields": ["Ptr0", "Ptr1"],
                },
                {
                    "normalized_record_offset": "0x28",
                    "object_offset": "0x2a8",
                    "accessor_va": "main+0x2f6b40",
                    "source_fields": ["Ptr2", "Ptr3"],
                },
            ],
        )
        self.assertEqual(opaque_pairs["static_special_pair_row_indexes"], [0, 1, 6, 8, 9])
        self.assertEqual(len(opaque_pairs["source_rows"]), 10)
        self.assertEqual(
            (
                opaque_pairs["source_rows"][2]["qword_Ptr0_Ptr1"],
                opaque_pairs["source_rows"][2]["qword_Ptr2_Ptr3"],
            ),
            ("0xf70f3a61e0e57a41", "0x0d1ce5ccc86e0299"),
        )
        self.assertEqual(
            [row["static_pair_comparison_class"] for row in opaque_pairs["source_rows"]],
            [
                "BOTH_COMPARISON_CONSTANT", "BOTH_COMPARISON_CONSTANT", "OTHER", "OTHER", "OTHER",
                "OTHER", "BOTH_COMPARISON_CONSTANT", "OTHER", "BOTH_COMPARISON_CONSTANT",
                "BOTH_COMPARISON_CONSTANT",
            ],
        )
        self.assertEqual(opaque_pairs["pointer_field_semantics"], "UNKNOWN")
        self.assertEqual(opaque_pairs["runtime_execution"], "UNVERIFIED")
        self.assertIn("FUN_7100218470 returns a species identifier", report["interpretation"]["not_established"])
        self.assertIn(
            "the xoroshiro-derived decompiler expression feeds the direct setter call at main+0xf058",
            report["interpretation"]["not_established"],
        )
        self.assertIn(
            "the data pointer at main+0x15278b8 is read or used for runtime dispatch",
            report["interpretation"]["not_established"],
        )
        self.assertIn(
            "the 4 KiB page-base references at main+0x1527000 access the specific pointer cell at main+0x15278b8",
            report["interpretation"]["not_established"],
        )
        self.assertIn(
            "the data pointer at main+0x1547368 is read or used for runtime dispatch to FUN_710028f300",
            report["interpretation"]["not_established"],
        )
        self.assertIn(
            "the qword run at main+0x1547348 is a vtable, function table, or a table with a particular type",
            report["interpretation"]["not_established"],
        )
        self.assertIn(
            "the common targets at main+0x2a90 and main+0x11160 establish a type or role for the adjacent qword run",
            report["interpretation"]["not_established"],
        )
        self.assertIn(
            "FUN_71002fdf90 or FUN_7100218470 connects to the separately traced event_encount loader/lookup chain",
            report["interpretation"]["not_established"],
        )


if __name__ == "__main__":
    unittest.main()
