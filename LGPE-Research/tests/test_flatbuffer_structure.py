import json
import struct
import tempfile
import unittest
from pathlib import Path

from lgpe_research.collision_batch import run_collision_batch, verify_collision_outputs
from lgpe_research.flatbuffer_probe import probe_relative_targets
from lgpe_research.flatbuffer_structure import root_table_view
from lgpe_research.gfbcol_structure import root_reference_view


def four_slot_root() -> bytes:
    data = bytearray(36)
    struct.pack_into("<I", data, 0, 16)
    struct.pack_into("<HHHHHH", data, 4, 12, 20, 4, 8, 12, 16)
    struct.pack_into("<iIIII", data, 16, 12, 0x1234, 0x2345, 0x3456, 0x4567)
    return bytes(data)


def four_slot_root_with_relative_targets() -> bytes:
    data = bytearray(100)
    struct.pack_into("<I", data, 0, 16)
    struct.pack_into("<HHHHHH", data, 4, 12, 20, 4, 8, 12, 16)
    struct.pack_into("<iIIII", data, 16, 12, 28, 36, 44, 52)
    for target, first_word in zip((48, 60, 72, 84), (3, 2, 1, 4)):
        struct.pack_into("<I", data, target, first_word)
    return bytes(data)


def root_with_one_table_vector() -> bytes:
    data = bytearray(76)
    struct.pack_into("<I", data, 0, 16)
    struct.pack_into("<HHHHHH", data, 4, 12, 20, 4, 8, 12, 16)
    struct.pack_into("<iIIII", data, 16, 12, 20, 0, 0, 0)
    struct.pack_into("<I", data, 40, 1)
    struct.pack_into("<I", data, 44, 24)
    struct.pack_into("<HHH", data, 60, 6, 8, 4)
    struct.pack_into("<iI", data, 68, 8, 0x12345678)
    return bytes(data)


def root_with_one_string_table() -> bytes:
    data = bytearray(93)
    struct.pack_into("<I", data, 0, 16)
    struct.pack_into("<HHH", data, 4, 6, 20, 4)
    struct.pack_into("<iI", data, 16, 12, 20)
    struct.pack_into("<II", data, 40, 1, 16)
    struct.pack_into("<HHH", data, 52, 6, 8, 4)
    struct.pack_into("<iI", data, 60, 8, 16)
    struct.pack_into("<I", data, 80, 8)
    data[84:93] = b"col_wall\0"
    return bytes(data)


class FlatBufferRootViewTests(unittest.TestCase):
    def test_reads_untyped_root_table_slots(self):
        view = root_table_view(four_slot_root())
        self.assertEqual(
            (view["root_offset"], view["signed_vtable_delta"], view["vtable_offset"]),
            (16, 12, 4),
        )
        self.assertEqual((view["vtable_bytes"], view["object_bytes"]), (12, 20))
        self.assertEqual([slot["field_offset"] for slot in view["slots"]], [4, 8, 12, 16])
        self.assertEqual(view["slots"][0]["raw_prefix_hex"], "34120000")
        self.assertTrue(all(slot["value_type"] == "UNKNOWN" for slot in view["slots"]))

    def test_accepts_signed_vtable_displacement(self):
        data = bytearray(34)
        struct.pack_into("<I", data, 0, 16)
        struct.pack_into("<iI", data, 16, -12, 0x11223344)
        struct.pack_into("<HHH", data, 28, 6, 8, 4)
        view = root_table_view(bytes(data))
        self.assertEqual(view["vtable_offset"], 28)
        self.assertEqual(view["slots"][0]["raw_prefix_hex"], "44332211")

    def test_rejects_invalid_bounds_and_slot_offsets(self):
        valid = four_slot_root()
        cases = []
        cases.append(valid[:7])
        bad = bytearray(valid); struct.pack_into("<I", bad, 0, 0xffffffff); cases.append(bytes(bad))
        bad = bytearray(valid); struct.pack_into("<I", bad, 0, 17); cases.append(bytes(bad))
        bad = bytearray(valid); struct.pack_into("<i", bad, 16, 0); cases.append(bytes(bad))
        bad = bytearray(valid); struct.pack_into("<H", bad, 4, 3); cases.append(bytes(bad))
        bad = bytearray(valid); struct.pack_into("<H", bad, 4, 11); cases.append(bytes(bad))
        bad = bytearray(valid); struct.pack_into("<H", bad, 6, 0xffff); cases.append(bytes(bad))
        bad = bytearray(valid); struct.pack_into("<H", bad, 8, 20); cases.append(bytes(bad))
        overlap = bytearray(28)
        struct.pack_into("<I", overlap, 0, 16)
        struct.pack_into("<i", overlap, 16, -6)
        struct.pack_into("<HHH", overlap, 22, 6, 8, 4)
        cases.append(bytes(overlap))
        for data in cases:
            with self.subTest(data=data.hex()), self.assertRaises(ValueError):
                root_table_view(data)

    def test_nested_probe_preserves_table_envelopes_without_naming_fields(self):
        view = root_reference_view(root_with_one_table_vector())
        self.assertEqual(view["schema_status"], "UNKNOWN")
        self.assertFalse(view["field_names_assigned"])
        slot0 = view["slots"][0]
        self.assertEqual(slot0["classification"], "VECTOR_OF_VALID_TABLE_ENVELOPES")
        self.assertEqual(slot0["vector_count_candidate"], 1)
        self.assertEqual(slot0["elements"][0]["table"]["table_offset"], 68)
        self.assertEqual(slot0["elements"][0]["table"]["object_hex"], "0800000078563412")
        self.assertEqual(
            slot0["elements"][0]["table"]["slot0_string_candidate"]["classification"],
            "UNRESOLVED",
        )
        self.assertTrue(all(slot["classification"] == "UNRESOLVED" for slot in view["slots"][1:]))

    def test_nested_probe_decodes_only_bounded_slot0_string_shape_candidates(self):
        view = root_reference_view(root_with_one_string_table())
        candidate = view["slots"][0]["elements"][0]["table"]["slot0_string_candidate"]

        self.assertEqual(view["schema_status"], "UNKNOWN")
        self.assertEqual(candidate["classification"], "UTF8_NUL_TERMINATED_LENGTH_PREFIX_CANDIDATE")
        self.assertEqual(candidate["decoded_text"], "col_wall")
        self.assertFalse(view["field_names_assigned"])

    def test_root_reference_view_does_not_read_uoffset_across_root_object_boundary(self):
        data = bytearray(64)
        struct.pack_into("<I", data, 0, 16)
        struct.pack_into("<HHH", data, 4, 6, 5, 4)
        struct.pack_into("<iI", data, 16, 12, 20)

        slot = root_reference_view(bytes(data))["slots"][0]

        self.assertEqual(slot["classification"], "UNRESOLVED")
        self.assertIn("complete four-byte", slot["reason"])

    def test_relative_target_probe_keeps_targets_untyped(self):
        result = probe_relative_targets(four_slot_root_with_relative_targets())

        self.assertEqual(result["analysis_status"], "HYPOTHESIS_ONLY")
        self.assertEqual(
            [slot["candidate_relative_target"] for slot in result["slots"]],
            [48, 60, 72, 84],
        )
        self.assertEqual(
            [slot["candidate_u32_at_target"] for slot in result["slots"]],
            [3, 2, 1, 4],
        )
        self.assertTrue(all(slot["minimum_byte_extent_fits"] for slot in result["slots"]))
        self.assertTrue(all(slot["target_is_4_byte_aligned"] for slot in result["slots"]))
        self.assertTrue(all(slot["interpretation_status"] == "UNKNOWN" for slot in result["slots"]))


class CollisionBatchTests(unittest.TestCase):
    def test_exports_mirrored_schema_unknown_json_and_revalidates_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            game = base / "game"
            romfs = game / "1.0.2" / "2b7730a9e56498bbafac2002d4908c6b_NCA" / "1"
            project = base / "LGPE-Research"
            rel = "bin/field/model/area01/sample.gfbcol"
            source = romfs / Path(rel)
            source.parent.mkdir(parents=True)
            source.write_bytes(four_slot_root())
            catalog = project / "manifests" / "files.csv"
            catalog.parent.mkdir(parents=True)
            catalog.write_text(
                "partition,relative_path,suffix,kind,bytes,signature,header_hex,sha256\n"
                f"romfs,{rel},.gfbcol,collision,{source.stat().st_size},unidentified,10000000,\n",
                encoding="utf-8",
            )

            first = run_collision_batch(game, project, limit=20, execute=True)
            target = project / "decoded" / "1.0.2" / "romfs" / Path(rel).with_suffix(".json")
            record = json.loads(target.read_text(encoding="utf-8"))
            row = json.loads((project / "manifests" / "collisions.jsonl").read_text(encoding="utf-8"))
            self.assertEqual(first["root_table_envelope_decoded"], 1)
            self.assertEqual(first["schema_unknown"], 1)
            self.assertEqual(row["status"], "UNKNOWN")
            self.assertEqual(row["structural_status"], "ROOT_TABLE_ENVELOPE_DECODED")
            self.assertEqual(record["schema_status"], "UNKNOWN")
            self.assertEqual(record["source"]["relative_path"], rel)
            self.assertEqual(record["root_table"], root_table_view(source.read_bytes()))
            self.assertEqual(record["nested_structure"]["schema_status"], "UNKNOWN")

            audit = verify_collision_outputs(game, project)
            self.assertEqual(audit["outputs_verified"], 1)
            self.assertEqual(audit["unknown"], 1)
            self.assertEqual(audit["errors"], [])

            first_bytes = target.read_bytes()
            second = run_collision_batch(game, project, limit=20, execute=True)
            self.assertEqual(second["outputs_verified"], 1)
            self.assertEqual(target.read_bytes(), first_bytes)

    def test_migrates_verified_root_only_output_to_nested_structure(self):
        import hashlib

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            game = base / "game"
            romfs = game / "1.0.2" / "2b7730a9e56498bbafac2002d4908c6b_NCA" / "1"
            project = base / "LGPE-Research"
            rel = "bin/field/model/area01/legacy.gfbcol"
            source = romfs / Path(rel)
            source.parent.mkdir(parents=True)
            source_bytes = four_slot_root()
            source.write_bytes(source_bytes)
            catalog = project / "manifests" / "files.csv"
            catalog.parent.mkdir(parents=True)
            catalog.write_text(
                "partition,relative_path,suffix,kind,bytes,signature,header_hex,sha256\n"
                f"romfs,{rel},.gfbcol,collision,{len(source_bytes)},unidentified,10000000,\n",
                encoding="utf-8",
            )
            source_hash = hashlib.sha256(source_bytes).hexdigest()
            output = project / "decoded" / "1.0.2" / "romfs" / Path(rel).with_suffix(".json")
            output.parent.mkdir(parents=True)
            legacy_record = {
                "format_candidate": "FlatBuffers-compatible root/table envelope",
                "analysis_scope": "root table and vtable only; no child traversal",
                "schema_status": "UNKNOWN",
                "slot_semantics": "UNKNOWN",
                "source": {
                    "partition": "romfs",
                    "relative_path": rel,
                    "bytes": len(source_bytes),
                    "sha256": source_hash,
                },
                "decoder": {
                    "implementation": "lgpe_research.flatbuffer_structure.root_table_view",
                    "version": 1,
                },
                "root_table": root_table_view(source_bytes),
            }
            legacy_bytes = (json.dumps(legacy_record, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()
            output.write_bytes(legacy_bytes)
            manifest_path = project / "manifests" / "collisions.jsonl"
            manifest_path.parent.mkdir(parents=True, exist_ok=True)
            legacy_row = {
                "domain": "collision",
                "partition": "romfs",
                "source": rel,
                "source_bytes": len(source_bytes),
                "signature": "unidentified",
                "output": output.relative_to(project).as_posix(),
                "status": "UNKNOWN",
                "structural_status": "ROOT_TABLE_ENVELOPE_DECODED",
                "schema_status": "UNKNOWN",
                "source_sha256": source_hash,
                "output_sha256": hashlib.sha256(legacy_bytes).hexdigest(),
                "output_bytes": len(legacy_bytes),
                "decoder": legacy_record["decoder"],
            }
            manifest_path.write_text(json.dumps(legacy_row) + "\n", encoding="utf-8")
            result = run_collision_batch(game, project, limit=0, execute=True)
            migrated = json.loads(output.read_text(encoding="utf-8"))
            migrated_row = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(result["outputs_verified"], 1)
            self.assertEqual(migrated["decoder"]["version"], 3)
            self.assertIn("nested_structure", migrated)
            self.assertEqual(migrated_row["decoder"]["version"], 3)
            interrupted_row = dict(migrated_row)
            interrupted_row["decoder"] = {
                "implementation": "lgpe_research.flatbuffer_structure.root_table_view",
                "version": 1,
            }
            interrupted_row["output_sha256"] = "0" * 64
            manifest_path.write_text(json.dumps(interrupted_row) + "\n", encoding="utf-8")
            recovered = run_collision_batch(game, project, limit=0, execute=True)
            recovered_row = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(recovered["outputs_verified"], 1)
            self.assertEqual(recovered_row["decoder"]["version"], 3)
            self.assertEqual(verify_collision_outputs(game, project)["errors"], [])

    def test_migrates_hash_verified_v2_output_to_string_candidates(self):
        import hashlib

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            game = base / "game"
            romfs = game / "1.0.2" / "2b7730a9e56498bbafac2002d4908c6b_NCA" / "1"
            project = base / "LGPE-Research"
            rel = "bin/field/model/area01/string.gfbcol"
            source = romfs / Path(rel)
            source.parent.mkdir(parents=True)
            source_bytes = root_with_one_string_table()
            source.write_bytes(source_bytes)
            catalog = project / "manifests" / "files.csv"
            catalog.parent.mkdir(parents=True)
            catalog.write_text(
                "partition,relative_path,suffix,kind,bytes,signature,header_hex,sha256\n"
                f"romfs,{rel},.gfbcol,collision,{len(source_bytes)},unidentified,10000000,\n",
                encoding="utf-8",
            )
            source_hash = hashlib.sha256(source_bytes).hexdigest()
            output = project / "decoded" / "1.0.2" / "romfs" / Path(rel).with_suffix(".json")
            output.parent.mkdir(parents=True)
            old_nested = root_reference_view(source_bytes)
            for slot in old_nested["slots"]:
                for element in slot.get("elements", []):
                    element["table"].pop("slot0_string_candidate", None)
            old_nested["analysis_scope"] = "root-slot vector extents and child table envelopes only"
            old_record = {
                "format_candidate": "FlatBuffers-compatible root/table envelope",
                "analysis_scope": "root table, root-slot vector candidates, and child table envelopes; no field semantics",
                "schema_status": "UNKNOWN",
                "slot_semantics": "UNKNOWN",
                "source": {
                    "partition": "romfs",
                    "relative_path": rel,
                    "bytes": len(source_bytes),
                    "sha256": source_hash,
                },
                "decoder": {
                    "implementation": "lgpe_research.gfbcol_structure.root_reference_view",
                    "version": 2,
                },
                "root_table": root_table_view(source_bytes),
                "nested_structure": old_nested,
            }
            old_bytes = (json.dumps(old_record, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()
            output.write_bytes(old_bytes)
            manifest = project / "manifests" / "collisions.jsonl"
            old_row = {
                "domain": "collision",
                "partition": "romfs",
                "source": rel,
                "source_bytes": len(source_bytes),
                "signature": "unidentified",
                "output": output.relative_to(project).as_posix(),
                "status": "UNKNOWN",
                "structural_status": "ROOT_TABLE_ENVELOPE_DECODED",
                "schema_status": "UNKNOWN",
                "source_sha256": source_hash,
                "output_sha256": hashlib.sha256(old_bytes).hexdigest(),
                "output_bytes": len(old_bytes),
                "decoder": old_record["decoder"],
            }
            manifest.write_text(json.dumps(old_row) + "\n", encoding="utf-8")

            result = run_collision_batch(game, project, limit=0, execute=True)
            upgraded = json.loads(output.read_text(encoding="utf-8"))
            upgraded_row = json.loads(manifest.read_text(encoding="utf-8"))
            audit = verify_collision_outputs(game, project)

            self.assertEqual(result["outputs_verified"], 1)
            self.assertEqual(result["slot0_string_shape_candidates"], 1)
            self.assertEqual(upgraded["decoder"]["version"], 3)
            self.assertEqual(
                upgraded["nested_structure"]["slots"][0]["elements"][0]["table"]
                ["slot0_string_candidate"]["decoded_text"],
                "col_wall",
            )
            self.assertEqual(upgraded_row["decoder"]["version"], 3)
            self.assertEqual(audit["slot0_string_shape_candidates"], 1)
            self.assertEqual(audit["errors"], [])


if __name__ == "__main__":
    unittest.main()
