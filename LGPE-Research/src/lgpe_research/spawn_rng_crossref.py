"""Cross-check opaque spawn selector values without assigning game semantics.

The exact-build code produces 0x90..0x92 from an RNG branch. This module
records numeric matches in pinned pkNX source and local LGPE personal/encounter
data, while keeping the meaning of the executable's opaque descriptor unknown.
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

from .core import ensure_inside, sha256, source_dirs

VALUES = (0x90, 0x91, 0x92)
EXPECTED_MAIN_SHA256 = "1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8"
EXPECTED_PKNX_COMMIT = "d191cd0e5c05f2af81d9a41c1f1d82e6621b351a"
EXPECTED_SPECIES_SOURCE_SHA256 = "4539de45e8b95f8e532e65a002f14139df5c92e1649f61d6ce2cfab10fa4f167"
EXPECTED_GAME_FILE_MAPPING_SHA256 = "c439e07b11e522b52070f61d35bdb77a35189147ef9df3343680785224fa5b92"
EXPECTED_ENCOUNTER_STATIC_SOURCE_SHA256 = "7d6606801788be39d28890e751126f42aade289963f684ae7f27085b3d331a91"
EXPECTED_FIXED_GENDER_SOURCE_SHA256 = "b981dab73e8148c50cde48e3218c25414f8d9178ba996e5290ef255ae5733ac6"
EXPECTED_GHIDRA_TRACE_SCRIPT_SHA256 = "e24dd90b2cbf1de394a13a178e90b57367c70435edad9d71d390407a6b8aacb9"
EXPECTED_GHIDRA_TRACE_WRAPPER_SHA256 = "f7d8aa01a975e2ff36adda63d9149d0cb597b11b20049228c40ef81239358f29"
EXPECTED_CAPTURE_RESULT_TRACE_SCRIPT_SHA256 = "a06de6c85f3acfebf7aa70e6e8c89d2f3a7e823b0f9d9a28020975362b160192"
EXPECTED_CAPTURE_RESULT_TRACE_WRAPPER_SHA256 = "b7784cc94a8a6a9c727b704efa6d065bfdb404523f057b44f5e0514942282b38"
OPAQUE_PAIR_COMPARISON_QWORD = 0xCBF29CE484222645
EXPECTED_INPUTS = {
    "bin/pokelib/personal/personal_total.bin": (
        "0bd93e9122b1148f5ea844a5fe35334d17680430d9164bce799dd08f6cf3cddf",
        "80e4b1a7674146e07b864a1c48ac4101fce18bf9ab3306b049d80d2a1668ad9a",
    ),
    "bin/field/param/encount/encount_data_p.bin": (
        "3dac771dffee508ff8fea41d255326640aefb67c88c2d96fd1ecda7b82b1ce46",
        "23e429a0470a356cffe44e323e8977db0e29c94c09937758676051980df077a2",
    ),
    "bin/field/param/encount/encount_data_e.bin": (
        "bea24bbbb4197681354e21f213cfde0148f9ea50cef60ef14ded333192fa80da",
        "c367918195863e36d8fe8ed8ce0943cc2383738cdeafa6bd3ea96f5a1db66bdd",
    ),
    "bin/script_event_data/event_encount.bin": (
        "2bbe6321c8c25dd75ed5d11db81fa4077bd513081c0c77d72b6574874ff5e814",
        "2f4c59c422f832cf74d3c13d1ee50c50dc3a07a5eec397209970d646e5e2d4eb",
    ),
}


def parse_species_enum(source: str) -> dict[int, str]:
    """Parse implicit/explicit C# enum ordinals, ignoring comments."""
    match = re.search(r"\benum\s+Species\s*:\s*ushort\s*\{(.*?)\}", source, re.S)
    if not match:
        raise ValueError("pinned pkNX Species enum was not found")
    body = re.sub(r"/\*.*?\*/|//[^\n]*", "", match.group(1), flags=re.S)
    result: dict[int, str] = {}
    next_value = 0
    for token in body.split(","):
        token = token.strip()
        if not token:
            continue
        name, separator, raw_value = token.partition("=")
        name = name.strip()
        if not re.fullmatch(r"[\w][\w]*", name, flags=re.UNICODE):
            raise ValueError(f"invalid enum member: {token!r}")
        value = int(raw_value.strip(), 0) if separator else next_value
        if value in result:
            raise ValueError(f"duplicate Species enum ordinal {value}")
        result[value] = name
        next_value = value + 1
    return result


def species_field_values(document) -> list[dict]:
    """Return numeric values under keys literally named Species."""
    hits: list[dict] = []

    def visit(value, path: str) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                child_path = f"{path}.{key}"
                if key.casefold() == "species" and isinstance(child, int) and not isinstance(child, bool):
                    hits.append({"path": child_path, "value": child})
                visit(child, child_path)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                visit(child, f"{path}[{index}]")

    visit(document, "$" )
    return hits


def _manifest_records(path: Path) -> dict[str, dict]:
    records: dict[str, dict] = {}
    if not path.is_file():
        raise FileNotFoundError(path)
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        record = json.loads(line)
        source = str(record.get("source", "")).replace("\\", "/")
        if source in EXPECTED_INPUTS:
            if source in records:
                raise ValueError(f"duplicate gamedata manifest row for {source}")
            records[source] = record
    missing = set(EXPECTED_INPUTS) - records.keys()
    if missing:
        raise ValueError(f"gamedata manifest is missing: {sorted(missing)}")
    return records


def _verified_json(project: Path, romfs: Path, relative: str, record: dict) -> tuple[Path, dict]:
    source = ensure_inside(romfs / relative, romfs)
    if not source.is_file():
        raise FileNotFoundError(source)
    source_hash, decoded_hash = EXPECTED_INPUTS[relative]
    actual_source_hash = sha256(source)
    if actual_source_hash != source_hash or record.get("source_sha256") != source_hash:
        raise ValueError(f"source hash mismatch for {relative}: {actual_source_hash}")
    if record.get("status") != "DECODED":
        raise ValueError(f"source is not DECODED in gamedata manifest: {relative}")

    output_relative = Path(str(record.get("output", "")).replace("\\", "/"))
    if output_relative.is_absolute() or ".." in output_relative.parts:
        raise ValueError(f"unsafe decoded output path for {relative}")
    output = ensure_inside(project / output_relative, project)
    if not output.is_file():
        raise FileNotFoundError(output)
    actual_output_hash = sha256(output)
    if actual_output_hash != decoded_hash or record.get("output_sha256") != decoded_hash:
        raise ValueError(f"decoded output hash mismatch for {relative}: {actual_output_hash}")
    return output, json.loads(output.read_text(encoding="utf-8"))


def build_spawn_rng_crossref(project: Path, game_root: Path) -> dict:
    """Build a hash-guarded, semantics-cautious numeric cross-reference."""
    project = project.resolve()
    romfs = source_dirs(game_root)["romfs"]
    exefs = source_dirs(game_root)["exefs"]
    main = ensure_inside(exefs / "main", exefs)
    if not main.is_file():
        raise FileNotFoundError(main)
    main_hash = sha256(main)
    if main_hash != EXPECTED_MAIN_SHA256:
        raise ValueError(f"LGPE 1.0.2 main SHA-256 mismatch: {main_hash}")

    records = _manifest_records(project / "manifests" / "gamedata.jsonl")
    loaded = {}
    for relative in EXPECTED_INPUTS:
        loaded[relative] = _verified_json(project, romfs, relative, records[relative])
    personal = loaded["bin/pokelib/personal/personal_total.bin"][1]
    personal_entries = personal.get("entries")
    if not isinstance(personal_entries, list):
        raise ValueError("personal_total JSON has no entries array")
    if len(personal_entries) != 980 or personal.get("entry_size") != 84:
        raise ValueError("personal_total entry count/stride differs from verified LGPE decode")

    pknx = project / "tools" / "src" / "pkNX"
    species_source = pknx / "pkNX.Structures" / "Misc" / "Species.cs"
    if not species_source.is_file():
        raise FileNotFoundError(species_source)
    pknx_commit = subprocess.run(
        ["git", "-C", str(pknx), "rev-parse", "HEAD"],
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    if pknx_commit != EXPECTED_PKNX_COMMIT:
        raise ValueError(f"pinned pkNX revision mismatch: {pknx_commit}")
    enum_hash = sha256(species_source)
    if enum_hash != EXPECTED_SPECIES_SOURCE_SHA256:
        raise ValueError(f"pkNX Species.cs hash mismatch: {enum_hash}")
    enum = parse_species_enum(species_source.read_text(encoding="utf-8"))

    mapping_source = pknx / "pkNX.Game" / "File" / "GameFileMapping.cs"
    if not mapping_source.is_file():
        raise FileNotFoundError(mapping_source)
    mapping_hash = sha256(mapping_source)
    if mapping_hash != EXPECTED_GAME_FILE_MAPPING_SHA256:
        raise ValueError(f"pkNX GameFileMapping.cs hash mismatch: {mapping_hash}")
    mapping_literal = 'new(EncounterTableStatic, SingleFile, "bin", "script_event_data", "event_encount.bin")'
    if mapping_literal not in mapping_source.read_text(encoding="utf-8"):
        raise ValueError("pinned pkNX mapping for event_encount.bin was not found")

    encounter_static_source = pknx / "pkNX.Structures" / "Encounter" / "Gen7" / "EncounterStatic7b.cs"
    fixed_gender_source = pknx / "pkNX.Structures" / "Encounter" / "FixedGender.cs"
    if sha256(encounter_static_source) != EXPECTED_ENCOUNTER_STATIC_SOURCE_SHA256:
        raise ValueError("pinned pkNX EncounterStatic7b.cs hash mismatch")
    if sha256(fixed_gender_source) != EXPECTED_FIXED_GENDER_SOURCE_SHA256:
        raise ValueError("pinned pkNX FixedGender.cs hash mismatch")
    encounter_static_text = encounter_static_source.read_text(encoding="utf-8")
    fixed_gender_text = fixed_gender_source.read_text(encoding="utf-8")
    if "get => (FixedGender)(Data[0x0D] & 3);" not in encounter_static_text:
        raise ValueError("pinned EncounterStatic7b Gender getter no longer maps source offset 0x0D")
    if not all(fragment in fixed_gender_text for fragment in ("Random = 0", "Male = 1", "Female = 2")):
        raise ValueError("pinned FixedGender enum values changed")
    for index, offset in enumerate((0x10, 0x14, 0x18, 0x1C)):
        fragment = f"public uint Ptr{index} {{ get => ReadUInt32LittleEndian(Data[0x{offset:X}..]);"
        if fragment not in encounter_static_text:
            raise ValueError(f"pinned EncounterStatic7b Ptr{index} offset changed")

    trace_script = project / "scripts" / "ghidra" / "InspectEventEncounterPathXrefs.java"
    trace_wrapper = project / "scripts" / "ghidra" / "Run-InspectEventEncounterPathXrefs.ps1"
    for path, expected, label in (
        (trace_script, EXPECTED_GHIDRA_TRACE_SCRIPT_SHA256, "Ghidra trace script"),
        (trace_wrapper, EXPECTED_GHIDRA_TRACE_WRAPPER_SHA256, "Ghidra trace wrapper"),
    ):
        if not path.is_file():
            raise FileNotFoundError(path)
        actual = sha256(path)
        if actual != expected:
            raise ValueError(f"{label} SHA-256 mismatch: {actual}")

    consumer_trace_script = project / "scripts" / "ghidra" / "InspectCaptureResultConsumers.java"
    consumer_trace_wrapper = project / "scripts" / "ghidra" / "Run-InspectCaptureResultConsumers.ps1"
    for path, expected, label in (
        (
            consumer_trace_script,
            EXPECTED_CAPTURE_RESULT_TRACE_SCRIPT_SHA256,
            "capture-result consumer trace script",
        ),
        (
            consumer_trace_wrapper,
            EXPECTED_CAPTURE_RESULT_TRACE_WRAPPER_SHA256,
            "capture-result consumer trace wrapper",
        ),
    ):
        if not path.is_file():
            raise FileNotFoundError(path)
        actual = sha256(path)
        if actual != expected:
            raise ValueError(f"{label} SHA-256 mismatch: {actual}")

    personal_matches = {}
    for value in VALUES:
        matches = [
            entry for entry in personal_entries
            if entry.get("index") == value and entry.get("GoSpecies") == value
        ]
        if len(matches) != 1:
            raise ValueError(f"expected one personal index/GoSpecies match for 0x{value:x}, got {len(matches)}")
        personal_matches[value] = matches[0]
        if value not in enum:
            raise ValueError(f"pkNX Species enum lacks ordinal {value}")

    encounter_species = {}
    for relative in (
        "bin/field/param/encount/encount_data_p.bin",
        "bin/field/param/encount/encount_data_e.bin",
    ):
        document = loaded[relative][1]
        hits = species_field_values(document)
        encounter_species[relative] = {
            "source_sha256": EXPECTED_INPUTS[relative][0],
            "decoded_json_sha256": EXPECTED_INPUTS[relative][1],
            "species_field_count": len(hits),
            "selector_value_hits": [hit for hit in hits if hit["value"] in VALUES],
            "total_zone_rows": len(document.get("tables", [])),
        }

    event_relative = "bin/script_event_data/event_encount.bin"
    event_document = loaded[event_relative][1]
    event_entries = event_document.get("entries")
    if (
        event_document.get("format") != "LGPE EncounterStatic7b"
        or event_document.get("source_class") != "pkNX.Structures.EncounterStatic7b / EditorGG.EditStatic"
        or event_document.get("entry_size") != 64
        or not isinstance(event_entries, list)
        or len(event_entries) != 10
    ):
        raise ValueError("event_encount JSON differs from the hash-verified EncounterStatic7b evidence")
    event_source = ensure_inside(romfs / event_relative, romfs)
    event_raw = event_source.read_bytes()
    if len(event_raw) != len(event_entries) * event_document["entry_size"]:
        raise ValueError("event_encount byte length does not match the decoded entry count and stride")
    event_hits = []
    event_rows = []
    opaque_pair_rows = []
    for index, entry in enumerate(event_entries):
        properties = entry.get("properties")
        if not isinstance(properties, dict):
            raise ValueError("event_encount entry has no properties object")
        start = index * event_document["entry_size"]
        raw_entry = event_raw[start:start + event_document["entry_size"]]
        if entry.get("index") != index or bytes.fromhex(entry.get("raw_hex", "")) != raw_entry:
            raise ValueError(f"event_encount decoded row {index} does not preserve the source bytes")
        source_species = int.from_bytes(raw_entry[0x08:0x0A], "little")
        source_form = raw_entry[0x0A]
        source_level = raw_entry[0x0B]
        source_gender = raw_entry[0x0D] & 3
        if (
            properties.get("Species") != source_species
            or properties.get("Form") != source_form
            or properties.get("Level") != source_level
            or properties.get("Gender") != source_gender
        ):
            raise ValueError(f"event_encount row {index} species/form/level/gender differs from its raw bytes")
        ptr_values = [
            int.from_bytes(raw_entry[offset:offset + 4], "little")
            for offset in (0x10, 0x14, 0x18, 0x1C)
        ]
        if any(properties.get(f"Ptr{ptr_index}") != value for ptr_index, value in enumerate(ptr_values)):
            raise ValueError(f"event_encount row {index} Ptr0..Ptr3 differ from their raw bytes")
        ptr01_qword = int.from_bytes(raw_entry[0x10:0x18], "little")
        ptr23_qword = int.from_bytes(raw_entry[0x18:0x20], "little")
        if ptr01_qword != (ptr_values[0] | (ptr_values[1] << 32)):
            raise ValueError(f"event_encount row {index} Ptr0/Ptr1 qword packing mismatch")
        if ptr23_qword != (ptr_values[2] | (ptr_values[3] << 32)):
            raise ValueError(f"event_encount row {index} Ptr2/Ptr3 qword packing mismatch")
        if (
            ptr01_qword == OPAQUE_PAIR_COMPARISON_QWORD
            and ptr23_qword == OPAQUE_PAIR_COMPARISON_QWORD
        ):
            pair_class = "BOTH_COMPARISON_CONSTANT"
        elif ptr01_qword == 0 and ptr23_qword == 0:
            pair_class = "BOTH_ZERO"
        else:
            pair_class = "OTHER"
        opaque_pair_rows.append({
            "index": index,
            "Ptr0": ptr_values[0],
            "Ptr1": ptr_values[1],
            "Ptr2": ptr_values[2],
            "Ptr3": ptr_values[3],
            "qword_Ptr0_Ptr1": f"0x{ptr01_qword:016x}",
            "qword_Ptr2_Ptr3": f"0x{ptr23_qword:016x}",
            "static_pair_comparison_class": pair_class,
            "matches_handler_special_pair_condition": pair_class in (
                "BOTH_COMPARISON_CONSTANT",
                "BOTH_ZERO",
            ),
        })
        event_rows.append({
            "index": index,
            "Species": source_species,
            "Species_enum_name": enum.get(source_species),
            "Form": source_form,
            "Level": source_level,
            "Gender": source_gender,
            "Gender_enum_name": {0: "Random", 1: "Male", 2: "Female"}.get(source_gender),
        })
        if properties.get("Species") in VALUES:
            event_hits.append({
                "index": entry.get("index"),
                "Species": properties["Species"],
                "Form": properties.get("Form"),
                "Level": properties.get("Level"),
            })
    expected_event_hits = [
        {"index": 2, "Species": 0x90, "Form": 0, "Level": 50},
        {"index": 3, "Species": 0x91, "Form": 0, "Level": 50},
        {"index": 4, "Species": 0x92, "Form": 0, "Level": 50},
    ]
    if event_hits != expected_event_hits:
        raise ValueError(f"event_encount selector-value rows changed: {event_hits!r}")
    expected_special_pair_rows = [0, 1, 6, 8, 9]
    actual_special_pair_rows = [
        row["index"] for row in opaque_pair_rows
        if row["static_pair_comparison_class"] == "BOTH_COMPARISON_CONSTANT"
    ]
    if actual_special_pair_rows != expected_special_pair_rows:
        raise ValueError(
            f"event_encount opaque-pair comparison rows changed: {actual_special_pair_rows!r}"
        )

    handler_tests = [
        {"normalized_species_u32": 0x85, "normalized_form_u8": 1},
        {"normalized_species_u32": 0x19, "normalized_form_u8": 8},
    ]
    handler_crossrefs = []
    for condition in handler_tests:
        matching_rows = [
            row for row in event_rows
            if row["Species"] == condition["normalized_species_u32"]
            and row["Form"] == condition["normalized_form_u8"]
        ]
        handler_crossrefs.append({
            **condition,
            "species_enum_name": enum.get(condition["normalized_species_u32"]),
            "source_matches": matching_rows,
        })
    expected_handler_matches = [
        [{"index": 1, "Species": 133, "Species_enum_name": "Eevee", "Form": 1, "Level": 5, "Gender": 0, "Gender_enum_name": "Random"}],
        [{"index": 0, "Species": 25, "Species_enum_name": "Pikachu", "Form": 8, "Level": 5, "Gender": 0, "Gender_enum_name": "Random"}],
    ]
    if [item["source_matches"] for item in handler_crossrefs] != expected_handler_matches:
        raise ValueError(f"event handler species/form source matches changed: {handler_crossrefs!r}")

    return {
        "schema": "lgpe-spawn-rng-value-crossref-v10",
        "status": "CORRELATED_UNASSIGNED",
        "game": "Pokemon Let's Go Pikachu 1.0.2",
        "main": {"sha256": main_hash, "image_base": "0x7100000000"},
        "code_evidence": {
            "candidate_va": "main+0x2fdf90",
            "opaque_value_accessor_va": "main+0x218470",
            "rng_values": [f"0x{value:x}" for value in VALUES],
            "candidate_runtime_reachability": "UNVERIFIED",
            "accessor_return_field_semantics": "UNKNOWN",
            "event_static_loader_chain": {
                "resource_path": "bin/script_event_data/event_encount.bin",
                "ghidra_version": "12.2_PUBLIC",
                "mode": ["-noanalysis", "-readOnly"],
                "runtime_execution": "UNVERIFIED",
                "trace_script": "scripts/ghidra/InspectEventEncounterPathXrefs.java",
                "trace_script_sha256": EXPECTED_GHIDRA_TRACE_SCRIPT_SHA256,
                "trace_wrapper": "scripts/ghidra/Run-InspectEventEncounterPathXrefs.ps1",
                "trace_wrapper_sha256": EXPECTED_GHIDRA_TRACE_WRAPPER_SHA256,
                "path_string_va": "main+0xf0415a",
                "path_string_xref": "main+0x2ba87c -> main+0x2ba7c0",
                "path_string_direct_xref_count": 1,
                "load_function_direct_callers": [
                    "main+0x289ae4",
                    "main+0x28e904",
                    "main+0x28f3ec",
                ],
                "path_builder_va": "main+0x1d4ff0",
                "resource_request_helper_va": "main+0xa63a0",
                "completion_check_va": "main+0x2ba980",
                "record_table_build_va": "main+0x2baa10",
                "record_table_build": {
                    "count_expression": "resource_buffer_size >> 6",
                    "input_record_stride_bytes": 64,
                    "internal_record_copy_bytes": 89,
                },
                "record_lookup_va": "main+0x2baba0",
                "record_lookup_direct_callers": [
                    {"from": "main+0x289db4", "owner": None},
                    {"from": "main+0x28ebe8", "owner": "main+0x28eb60"},
                    {"from": "main+0x28f4a8", "owner": "main+0x28f430"},
                ],
                "completion_handler_va": "main+0x28f430",
                "completion_handler_direct_calls": [
                    "main+0x2baba0",
                    "main+0xd2fb28",
                    "main+0x1ca030",
                    "main+0xd2fac8",
                    "main+0x2f5a40",
                    "main+0x2f5ec0",
                    "main+0x2f5f60",
                    "main+0x2f6440",
                    "main+0x1c5df0",
                    "main+0xd2faf8",
                ],
                "direct_call_to_rng_candidate": False,
                "rng_candidate_connection": "NOT_ESTABLISHED",
            },
            "event_static_handler_cross_reference": {
                "handler_function_va": "main+0x28f430",
                "handler_owner_function_va": "main+0x28f300",
                "record_lookup_va": "main+0x2baba0",
                "record_table_build_va": "main+0x2baa10",
                "runtime_execution": "UNVERIFIED",
                "handler_owner_entry_data_reference": {
                    "from": "main+0x1547368",
                    "reference_type": "DATA",
                    "stored_value": "main+0x28f300",
                    "ghidra_data_type": "undefined *",
                    "memory_block": ".data",
                    "block_permissions": {"read": True, "write": True, "execute": False},
                    "window_start": "main+0x1547348",
                    "window_qwords": [
                        "0x7100002a90",
                        "0x7100011160",
                        "0x710028f2e0",
                        "0x710028f2f0",
                        "0x710028f300",
                        "0x710028f6c0",
                        "0xffffffffffffffb8",
                        "0x0000000000000000",
                    ],
                    "window_semantics": "UNKNOWN",
                    "pointer_target_code_observations": [
                        {
                            "pointer_cell": "main+0x1547348",
                            "target": "main+0x2a90",
                            "outgoing_reference": "DATA",
                            "exact_function": "NOT_DEFINED_IN_SAVED_DATABASE",
                            "containing_function": "NOT_DEFINED_IN_SAVED_DATABASE",
                            "observed_instructions": [
                                {"address": "main+0x2a90", "text": "ldr x8,[x0, #0x58]"},
                                {"address": "main+0x2a94", "text": "add x9,x8,#0x54"},
                                {"address": "main+0x2a98", "text": "ldaxr w10,[x9]"},
                            ],
                            "incoming_reference_summary": {
                                "reference_count": 1175,
                                "reference_types": {"DATA": 1175},
                                "owner_labels": {"<no-function>": 1175},
                                "sample_from": [
                                    "main+0x1527040", "main+0x1527158", "main+0x1527200",
                                    "main+0x1527898", "main+0x1547348",
                                ],
                            },
                        },
                        {
                            "pointer_cell": "main+0x1547350",
                            "target": "main+0x11160",
                            "outgoing_reference": "DATA",
                            "exact_function": "FUN_7100011160",
                            "containing_function": "FUN_7100011160",
                            "observed_instructions": [
                                {"address": "main+0x11160", "text": "stp x29,x30,[sp, #-0x10]!"},
                                {"address": "main+0x11164", "text": "mov x29,sp"},
                                {"address": "main+0x11168", "text": "adrp x8,0x71015fa000"},
                            ],
                            "incoming_reference_summary": {
                                "reference_count": 65,
                                "reference_types": {"DATA": 65},
                                "owner_labels": {"<no-function>": 65},
                                "sample_from": [
                                    "main+0x15278a0", "main+0x1527968", "main+0x1537628",
                                    "main+0x1545f58", "main+0x1547350",
                                ],
                            },
                        },
                        {
                            "pointer_cell": "main+0x1547358",
                            "target": "main+0x28f2e0",
                            "outgoing_reference": "DATA",
                            "exact_function": "NOT_DEFINED_IN_SAVED_DATABASE",
                            "containing_function": "NOT_DEFINED_IN_SAVED_DATABASE",
                            "observed_instructions": [
                                {"address": "main+0x28f2e0", "text": "mov w0,#0x1"},
                                {"address": "main+0x28f2e4", "text": "ret"},
                            ],
                            "incoming_reference_summary": {
                                "reference_count": 1,
                                "reference_types": {"DATA": 1},
                                "owner_labels": {"<no-function>": 1},
                                "sample_from": ["main+0x1547358"],
                            },
                        },
                        {
                            "pointer_cell": "main+0x1547360",
                            "target": "main+0x28f2f0",
                            "outgoing_reference": "DATA",
                            "exact_function": "NOT_DEFINED_IN_SAVED_DATABASE",
                            "containing_function": "NOT_DEFINED_IN_SAVED_DATABASE",
                            "observed_instructions": [
                                {"address": "main+0x28f2f0", "text": "ret"},
                            ],
                            "incoming_reference_summary": {
                                "reference_count": 1,
                                "reference_types": {"DATA": 1},
                                "owner_labels": {"<no-function>": 1},
                                "sample_from": ["main+0x1547360"],
                            },
                        },
                        {
                            "pointer_cell": "main+0x1547368",
                            "target": "main+0x28f300",
                            "outgoing_reference": "DATA",
                            "exact_function": "FUN_710028f300",
                            "containing_function": "FUN_710028f300",
                            "observed_instructions": [
                                {"address": "main+0x28f300", "text": "stp x22,x21,[sp, #-0x30]!"},
                                {"address": "main+0x28f304", "text": "stp x20,x19,[sp, #0x10]"},
                                {"address": "main+0x28f308", "text": "stp x29,x30,[sp, #0x20]"},
                            ],
                            "incoming_reference_summary": {
                                "reference_count": 1,
                                "reference_types": {"DATA": 1},
                                "owner_labels": {"<no-function>": 1},
                                "sample_from": ["main+0x1547368"],
                            },
                        },
                        {
                            "pointer_cell": "main+0x1547370",
                            "target": "main+0x28f6c0",
                            "outgoing_reference": "DATA",
                            "exact_function": "NOT_DEFINED_IN_SAVED_DATABASE",
                            "containing_function": "NOT_DEFINED_IN_SAVED_DATABASE",
                            "observed_instructions": [
                                {"address": "main+0x28f6c0", "text": "ret"},
                            ],
                            "incoming_reference_summary": {
                                "reference_count": 1,
                                "reference_types": {"DATA": 1},
                                "owner_labels": {"<no-function>": 1},
                                "sample_from": ["main+0x1547370"],
                            },
                        },
                    ],
                    "direct_references_to_cell_in_saved_database": 0,
                    "page_base_reference_summary": {
                        "address": "main+0x1547000",
                        "reference_count": 5,
                        "reference_types": {"DATA": 4, "READ": 1},
                        "unique_owners": 3,
                        "sample_from_addresses": [
                            "main+0x28a308",
                            "main+0x28ca2c",
                            "main+0x28ca6c",
                            "main+0x295eac",
                            "main+0x295eb8",
                        ],
                        "specific_cell_use": "NOT_ESTABLISHED",
                    },
                    "runtime_dispatch": "UNVERIFIED",
                },
                "handler_owner_direct_calls": [
                    "main+0x28f3ec -> main+0x2ba7c0",
                    "main+0x28f400 -> main+0x2ba980",
                    "main+0x28f40c -> main+0x28f430",
                ],
                "trace_script": "scripts/ghidra/InspectEventEncounterPathXrefs.java",
                "trace_script_sha256": EXPECTED_GHIDRA_TRACE_SCRIPT_SHA256,
                "trace_wrapper": "scripts/ghidra/Run-InspectEventEncounterPathXrefs.ps1",
                "trace_wrapper_sha256": EXPECTED_GHIDRA_TRACE_WRAPPER_SHA256,
                "normalization": {
                    "input_record_stride_bytes": 64,
                    "species_input_offset": "0x08 (u16)",
                    "species_internal_offset": "0x08 (zero-extended u32)",
                    "form_input_offset": "0x0a (u8)",
                    "form_internal_offset": "0x0c (u8)",
                    "level_input_offset": "0x0b (u8)",
                    "level_internal_offset": "0x0d (u8)",
                    "gender_input_offset": "0x0d (low two bits)",
                    "gender_internal_offset": "0x14 (u8)",
                },
                "branch_tests": handler_crossrefs,
                "gender_override": {
                    "helper_function_va": "main+0x1ca030",
                    "helper_call_sites": ["main+0x28f4fc", "main+0x28f508"],
                    "helper_return_expression": "byte [param+0x111]",
                    "input_object_offset": "0x111 (opaque field)",
                    "writes_to_normalized_gender_offset": "0x14",
                    "setter_function_va": "main+0x1ca020",
                    "setter_body": "byte [param+0x111] = param_2",
                    "setter_direct_call_reference": {
                        "from": "main+0xf058",
                        "caller": "main+0xe420",
                        "argument_context": ["mov w1,#0x1", "mov x0,x20"],
                        "observed_second_argument": "constant 1",
                    },
                    "setter_caller_entry_data_reference": {
                        "from": "main+0x15278b8",
                        "reference_type": "DATA",
                        "stored_value": "main+0xe420",
                        "ghidra_data_type": "undefined *",
                        "memory_block": ".data",
                        "block_permissions": {"read": True, "write": True, "execute": False},
                        "window_start": "main+0x1527898",
                        "window_qwords": [
                            "0x7100002a90",
                            "0x7100011160",
                            "0x710000e2c0",
                            "0x710000e2d0",
                            "0x710000e420",
                            "0x7100010e60",
                            "0xffffffffffffffff",
                            "0x0000000000000000",
                        ],
                        "direct_references_to_cell_in_saved_database": 0,
                        "page_base_reference_summary": {
                            "address": "main+0x1527000",
                            "reference_count": 375,
                            "reference_types": {"DATA": 178, "PARAM": 197},
                            "unique_owners": 82,
                            "sample_from_addresses": [
                                "main+0xc9ba0c",
                                "main+0x5fb254",
                                "main+0x36a9b8",
                                "main+0xcaa1cc",
                                "main+0x469578",
                            ],
                            "specific_cell_use": "NOT_ESTABLISHED",
                        },
                        "runtime_dispatch": "UNVERIFIED",
                    },
                    "setter_decompile_comparison": {
                        "caller": "main+0xe420",
                        "decompiled_switch_case": "0xb",
                        "decompiled_argument_expression": "((int)uVar2 + (int)uVar1 & 1U) != 0",
                        "decompiler_warning": "Type propagation algorithm not settling",
                        "instruction_context_conflict": True,
                        "status": "UNRESOLVED",
                    },
                    "related_object_paths": {
                        "event_handler": "global+0x98 -> object+0x58 -> object+0x78",
                        "setter_caller": "param_2+0x98 -> object+0x58 -> object+0x78",
                        "object_identity": "UNRESOLVED",
                    },
                    "outcomes": [
                        {"first_helper_return": 0, "gender_value": 1, "gender_enum_name": "Male"},
                        {
                            "first_helper_return_nonzero": True,
                            "second_helper_return": 1,
                            "gender_value": 2,
                            "gender_enum_name": "Female",
                        },
                    ],
                    "pknx_encounter_static_source": "pkNX.Structures/Encounter/Gen7/EncounterStatic7b.cs",
                    "pknx_encounter_static_source_sha256": EXPECTED_ENCOUNTER_STATIC_SOURCE_SHA256,
                    "pknx_fixed_gender_source": "pkNX.Structures/Encounter/FixedGender.cs",
                    "pknx_fixed_gender_source_sha256": EXPECTED_FIXED_GENDER_SOURCE_SHA256,
                    "pknx_commit": pknx_commit,
                    "runtime_execution": "UNVERIFIED",
                    "opaque_input_semantics": "UNKNOWN",
                },
                "interpretation": "The static handler tests normalized species/form pairs that match event_encount source rows, then assigns a Gender value from an opaque byte field. This does not establish gameplay meaning or runtime execution.",
            },
            "event_record_opaque_pair_cross_reference": {
                "handler_function_va": "main+0x28eb60",
                "record_lookup_va": "main+0x2baba0",
                "record_table_build_va": "main+0x2baa10",
                "record_table_build": {
                    "input_record_stride_bytes": 64,
                    "internal_record_copy_bytes": 89,
                    "source_fields": ["Ptr0", "Ptr1", "Ptr2", "Ptr3"],
                    "source_bytes_to_normalized_record": [
                        {"source": "0x10..0x17", "normalized": "0x20..0x27", "fields": ["Ptr0", "Ptr1"]},
                        {"source": "0x18..0x1f", "normalized": "0x28..0x2f", "fields": ["Ptr2", "Ptr3"]},
                    ],
                    "mapping_evidence": "main+0x2baa10 copies source qwords at +0x10/+0x18 into local normalized-record qwords at +0x20/+0x28, then copies 0x59 bytes into the indexed map",
                },
                "consumer_object_mapping": [
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
                "handler_comparison_qword": f"0x{OPAQUE_PAIR_COMPARISON_QWORD:016x}",
                "handler_special_pair_condition": "both qwords equal the comparison constant OR both qwords are zero",
                "pknx_source": "pkNX.Structures/Encounter/Gen7/EncounterStatic7b.cs",
                "pknx_source_sha256": EXPECTED_ENCOUNTER_STATIC_SOURCE_SHA256,
                "pknx_commit": pknx_commit,
                "pknx_comment_on_0x10_0x1f": "possible text line references; not confirmed by that source",
                "source_rows": opaque_pair_rows,
                "static_special_pair_row_indexes": actual_special_pair_rows,
                "runtime_execution": "UNVERIFIED",
                "pointer_field_semantics": "UNKNOWN",
                "interpretation": "The local event rows' pkNX-named Ptr0..Ptr3 fields flow into the two qwords read by this exact-build handler; five rows statically match its constant-pair comparison. The names do not establish field meaning, capture-result semantics, or runtime use.",
                "trace_script": "scripts/ghidra/InspectCaptureResultConsumers.java",
                "trace_script_sha256": EXPECTED_CAPTURE_RESULT_TRACE_SCRIPT_SHA256,
                "trace_wrapper": "scripts/ghidra/Run-InspectCaptureResultConsumers.ps1",
                "trace_wrapper_sha256": EXPECTED_CAPTURE_RESULT_TRACE_WRAPPER_SHA256,
            },
        },
        "pknx_reference": {
            "repository": "tools/src/pkNX",
            "commit": pknx_commit,
            "license": "GPL-3.0",
            "source": "pkNX.Structures/Misc/Species.cs",
            "source_sha256": enum_hash,
            "enum_ordinals": [
                {"value": value, "name": enum[value]} for value in VALUES
            ],
        },
        "pknx_path_mapping": {
            "repository": "tools/src/pkNX",
            "commit": pknx_commit,
            "source": "pkNX.Game/File/GameFileMapping.cs",
            "source_sha256": mapping_hash,
            "mapping": "bin/script_event_data/event_encount.bin -> EncounterTableStatic",
        },
        "personal_total": {
            "source": "bin/pokelib/personal/personal_total.bin",
            "source_sha256": EXPECTED_INPUTS["bin/pokelib/personal/personal_total.bin"][0],
            "decoded_json_sha256": EXPECTED_INPUTS["bin/pokelib/personal/personal_total.bin"][1],
            "rows": [
                {
                    "index": value,
                    "GoSpecies": personal_matches[value]["GoSpecies"],
                    "enum_name": enum[value],
                }
                for value in VALUES
            ],
        },
        "ordinary_encounter_tables": encounter_species,
        "event_static_encounters": {
            "source": event_relative,
            "source_sha256": EXPECTED_INPUTS[event_relative][0],
            "decoded_json_sha256": EXPECTED_INPUTS[event_relative][1],
            "format": event_document["format"],
            "source_class": event_document["source_class"],
            "entry_size": event_document["entry_size"],
            "entry_count": len(event_entries),
            "selector_value_hits": event_hits,
        },
        "interpretation": {
            "supported": "0x90..0x92 numerically match pkNX Species ordinals, personal-table index/GoSpecies values, and Species fields in three hash-verified LGPE EncounterStatic7b records. Separately, the exact-build event handler's normalized species/form checks match two rows in event_encount.bin; its branch reads an opaque byte and conditionally writes the pinned Male/Female Gender encodings.",
            "hypothesis": "The RNG selector values may correspond to those static event Species values, but the traced event-table path is a separate static data path and no link to the RNG candidate has been established.",
            "not_established": [
                "FUN_7100218470 returns a species identifier",
                "the opaque descriptor selects a legendary encounter",
                "the candidate function is reachable at runtime",
                "the event handler's static Gender override executes at runtime or reflects the active gameplay outcome",
                "the event handler's +0x111 byte is the same runtime object instance written by FUN_710000e420",
                "the xoroshiro-derived decompiler expression feeds the direct setter call at main+0xf058",
                "the data pointer at main+0x15278b8 is read or used for runtime dispatch",
                "the 4 KiB page-base references at main+0x1527000 access the specific pointer cell at main+0x15278b8",
                "the data pointer at main+0x1547368 is read or used for runtime dispatch to FUN_710028f300",
                "the 5 page-base references at main+0x1547000 access the specific pointer cell at main+0x1547368",
                "the qword run at main+0x1547348 is a vtable, function table, or a table with a particular type",
                "the EncounterStatic7b Ptr0..Ptr3 fields have confirmed semantic meanings",
                "the Ptr0..Ptr3 pair comparison establishes a capture-result meaning or runtime outcome",
                "the common targets at main+0x2a90 and main+0x11160 establish a type or role for the adjacent qword run",
                "FUN_71002fdf90 or FUN_7100218470 connects to the separately traced event_encount loader/lookup chain",
            ],
        },
    }


def write_spawn_rng_crossref(project: Path, game_root: Path, output: Path) -> dict:
    project = project.resolve()
    output = ensure_inside(output.resolve(), project)
    report = build_spawn_rng_crossref(project, game_root)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report["output"] = str(output)
    return report
