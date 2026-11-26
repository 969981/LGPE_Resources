#!/usr/bin/env python3
"""Build a source-hash-bound BSEQ runtime dispatch cross-reference."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[2]
NCA = PROJECT.parent / "1.0.2" / "2b7730a9e56498bbafac2002d4908c6b_NCA"
MAIN = NCA / "0" / "main"
SAMPLE = NCA / "1" / "bin" / "battle" / "waza" / "sequence" / "ee000.bseq"
PBSEQTOOL = PROJECT / "tools" / "src" / "pbseqtool"
DICTIONARY = PBSEQTOOL / "commandDictionaries" / "LGPECommandReference.json"
HELPER_LOG = PROJECT / "logs" / "ghidra-sequence-helpers-v1-script.log"
CALLBACK_LOG = PROJECT / "logs" / "ghidra-sequence-callbacks-v1-script.log"
OWNER_VTABLE_LOG = PROJECT / "logs" / "ghidra-sequence-owner-vtables-v1-script.log"
MAIN_SHA256 = "1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8"
SAMPLE_SHA256 = "1b38facf44af506167a588da86c5a6926704336178669248e022e250366cc88f"
DICTIONARY_SHA256 = "b226d3fbfbf6bce22256f82e3a38a933faa48bb1bea5b73b13b493896b5746be"
PBSEQTOOL_COMMIT = "6f122d1b7945797cae472960b798bf28523f8acd"
IMAGE_BASE = 0x7100000000


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def checked_pbseqtool() -> tuple[object, object]:
    result = subprocess.run(
        ["git", "-c", f"safe.directory={PBSEQTOOL}", "-C", str(PBSEQTOOL), "rev-parse", "HEAD"],
        check=True, capture_output=True, text=True,
    )
    commit = result.stdout.strip()
    if commit != PBSEQTOOL_COMMIT:
        raise ValueError(f"pbseqtool commit mismatch: {commit}")
    dirty = subprocess.run(
        ["git", "-c", f"safe.directory={PBSEQTOOL}", "-C", str(PBSEQTOOL),
         "status", "--porcelain", "--untracked-files=no"],
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    if dirty:
        raise ValueError("pinned pbseqtool source has tracked modifications")

    sys.path.insert(0, str(PBSEQTOOL))
    reference_spec = importlib.util.spec_from_file_location(
        "lgpe_dispatch_cmd_reference", PBSEQTOOL / "cmdReference.py"
    )
    if reference_spec is None or reference_spec.loader is None:
        raise ImportError("cannot load pinned pbseqtool cmdReference.py")
    reference_module = importlib.util.module_from_spec(reference_spec)
    sys.modules["cmdReference"] = reference_module
    reference_spec.loader.exec_module(reference_module)

    sesd_spec = importlib.util.spec_from_file_location(
        "lgpe_dispatch_sesd", PBSEQTOOL / "sesd.py"
    )
    if sesd_spec is None or sesd_spec.loader is None:
        raise ImportError("cannot load pinned pbseqtool sesd.py")
    sesd_module = importlib.util.module_from_spec(sesd_spec)
    sesd_spec.loader.exec_module(sesd_module)
    return reference_module, sesd_module


def parse_latest_dispatch_slots(log_text: str) -> tuple[list[dict], dict]:
    marker = "DISPATCH_TABLE\tcell=7101608df8"
    start = log_text.rfind(marker)
    if start < 0:
        raise ValueError("Ghidra log has no 1.0.2 callback command-table probe")
    summary_match = re.search(
        r"DISPATCH_TABLE_SUMMARY\tcell=7101608df8\tinspected=(\d+)"
        r"\texecutable_targets=(\d+)\tterminating_nonexec_run=(\d+)",
        log_text[start:],
    )
    if summary_match is None:
        raise ValueError("Ghidra callback command-table summary is incomplete")
    table_match = re.search(
        r"DISPATCH_TABLE\tcell=7101608df8\ttable=([0-9a-f]+)\tmax_slots=(\d+)",
        log_text[start:],
    )
    if table_match is None:
        raise ValueError("Ghidra callback command-table address is missing")
    end = start + summary_match.end()
    block = log_text[start:end]
    slots = []
    pattern = re.compile(
        r"DISPATCH_SLOT\tindex=(\d+)\taddress=([0-9a-f]+)\t"
        r"target=([0-9a-f]+)\texecutable=(true|false)\tfunction=([^\s]+)"
    )
    for match in pattern.finditer(block):
        slots.append({
            "index": int(match.group(1)),
            "slot_address": int(match.group(2), 16),
            "target_address": int(match.group(3), 16),
            "executable": match.group(4) == "true",
        })
    inspected, executable, trailing_nonexec = map(int, summary_match.groups())
    if inspected != int(table_match.group(2)) or len(slots) != inspected:
        raise ValueError("Ghidra callback table row count differs from its probe summary")
    table_address = int(table_match.group(1), 16)
    if table_address != 0x71015D4C70:
        raise ValueError(f"callback handler table address mismatch: 0x{table_address:x}")
    if executable != inspected or any(not slot["executable"] for slot in slots):
        raise ValueError("the bounded callback table scan contains a non-code entry")
    if [slot["index"] for slot in slots] != list(range(inspected)):
        raise ValueError("callback table indexes are not a contiguous zero-based scan")
    if any(slot["slot_address"] != table_address + slot["index"] * 8 for slot in slots):
        raise ValueError("callback table slot addresses do not follow the observed 8-byte stride")
    return slots, {
        "global_pointer_cell": "0x7101608df8",
        "table_address": f"0x{int(table_match.group(1), 16):x}",
        "configured_max_slots": int(table_match.group(2)),
        "inspected_slots": inspected,
        "executable_targets": executable,
        "terminating_nonexec_run": trailing_nonexec,
        "length_proven": trailing_nonexec > 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output", type=Path,
        default=PROJECT / "manifests" / "bseq-runtime-dispatch.json",
    )
    args = parser.parse_args()

    for path in (MAIN, SAMPLE, DICTIONARY, HELPER_LOG, CALLBACK_LOG, OWNER_VTABLE_LOG):
        if not path.is_file():
            raise FileNotFoundError(f"required local evidence file is missing: {path}")
    main_hash = sha256(MAIN)
    sample_hash = sha256(SAMPLE)
    dictionary_hash = sha256(DICTIONARY)
    if main_hash != MAIN_SHA256:
        raise ValueError(f"LGPE 1.0.2 main hash mismatch: {main_hash}")
    if sample_hash != SAMPLE_SHA256:
        raise ValueError(f"ee000.bseq hash mismatch: {sample_hash}")
    if dictionary_hash != DICTIONARY_SHA256:
        raise ValueError(f"pinned LGPE parser dictionary hash mismatch: {dictionary_hash}")

    helper_log_text = HELPER_LOG.read_text(encoding="utf-8", errors="replace")
    callback_log_text = CALLBACK_LOG.read_text(encoding="utf-8", errors="replace")
    owner_log_text = OWNER_VTABLE_LOG.read_text(encoding="utf-8", errors="replace")
    helper_summary_matches = re.findall(
        r"SUMMARY\tmain_sha256=" + MAIN_SHA256
        + r"\timage_base=0x7100000000\tselected_functions=(\d+)"
        + r"\tdecompiled=(\d+)\tfunction_failures=(\d+)\tread_only=true",
        helper_log_text,
    )
    callback_summary_matches = re.findall(
        r"SUMMARY\tmain_sha256=" + MAIN_SHA256
        + r"\timage_base=0x7100000000\ttargets=(\d+)"
        + r"\tcreated_functions=(\d+)\tdecompiled=(\d+)\tfailures=(\d+)"
        + r"\tread_only_source=true\tproject_database_modified=true",
        callback_log_text,
    )
    if not helper_summary_matches or tuple(map(int, helper_summary_matches[-1])) != (40, 40, 0):
        raise ValueError("latest read-only Ghidra helper pass was not 40/40 successful")
    if not callback_summary_matches or tuple(map(int, callback_summary_matches[-1])) != (8, 5, 8, 0):
        raise ValueError("latest callback Ghidra pass was not 8 targets / 5 created / 8 decompiled / 0 failures")
    if (
        f"SUMMARY\ttargets=2\tmain_sha256={MAIN_SHA256}\tread_only=true" not in owner_log_text
        or "address_point_candidate=71015d3268\tmethod_slot=78" not in owner_log_text
        or "address_point_candidate=71015d3268\tmethod_slot=152" not in owner_log_text
        or "OWNER_VPTR_REF\taddress_point=71015d3268\tfrom=7100a77c68" not in owner_log_text
    ):
        raise ValueError("controller address-point candidate was not verified by the latest Ghidra pass")
    decompiled_addresses = {
        int(value, 16)
        for value in re.findall(r"DECOMPILED_END\t([0-9a-f]+)", callback_log_text)
    }
    function_bytes = {
        int(address, 16): int(size)
        for address, size in re.findall(
            r"FUNCTION_BEGIN\t([0-9a-f]+)\t[^\s]+\tbytes=(\d+)", callback_log_text
        )
    }
    function_instructions = {
        int(address, 16): int(count)
        for address, count in re.findall(
            r"FUNCTION_END\t([0-9a-f]+)\tinstructions=(\d+)", callback_log_text
        )
    }
    first_instructions = {}
    for address, instruction in re.findall(
        r"INSN\t([0-9a-f]+)\t([^\r\n]+)", callback_log_text
    ):
        first_instructions.setdefault(int(address, 16), instruction)

    slots, table_scan = parse_latest_dispatch_slots(helper_log_text)
    dictionary = json.loads(DICTIONARY.read_text(encoding="utf-8"))
    if dictionary.get("game") != "LGPE":
        raise ValueError("command reference is not labeled for LGPE")
    command_by_index = {}
    for entry in dictionary["commandInfo"]:
        raw_id = bytes.fromhex(entry["commandID"])
        if len(raw_id) != 2:
            raise ValueError(f"expected a 16-bit LGPE parser command ID: {entry['commandID']}")
        index = int.from_bytes(raw_id, "little")
        if index in command_by_index:
            raise ValueError(f"duplicate pinned dictionary index: {index}")
        if index >= len(slots):
            raise ValueError(f"dictionary command index {index} exceeds observed table scan")
        command_by_index[index] = {
            "id_hex": entry["commandID"],
            "id_bytes_hex": raw_id.hex(" "),
            "reference_names": entry["commandNames"],
        }
    if sorted(command_by_index) != list(range(227)):
        raise ValueError("pinned LGPE reference IDs are not the observed contiguous index range 0..226")

    reference_module, sesd_module = checked_pbseqtool()
    ref = reference_module.CmdReference(dictionary)
    parsed = sesd_module.SESD.from_bytes(SAMPLE.read_bytes(), "LGPE", ref)
    sample_commands = []
    for group in parsed.cmd_groups:
        for command in group.commands:
            raw_id = bytes.fromhex(command.id)
            index = int.from_bytes(raw_id, "little")
            slot = slots[index]
            sample_commands.append({
                "parser_name": command.name,
                "parser_id_hex": command.id,
                "raw_id_bytes_hex": raw_id.hex(" "),
                "table_index_from_exact_build_u16_le": index,
                "group_number_from_pinned_parser": command.group_num,
                "start_frame_from_pinned_parser": command.start_frame,
                "end_frame_from_pinned_parser": command.end_frame,
                "dispatch_slot": f"0x{slot['slot_address']:x}",
                "handler_address": f"0x{slot['target_address']:x}",
                "target_function_created": slot["target_address"] in function_bytes,
                "target_decompiler_completed": slot["target_address"] in decompiled_addresses,
                "observed_function_body_bytes": function_bytes.get(slot["target_address"]),
                "observed_instruction_count": function_instructions.get(slot["target_address"]),
                "observed_first_instruction": first_instructions.get(slot["target_address"]),
            })
    if len(sample_commands) != 5:
        raise ValueError(f"expected five parsed sample commands, got {len(sample_commands)}")
    if any(not item["target_function_created"] or not item["target_decompiler_completed"]
           for item in sample_commands):
        raise ValueError("one or more sample command handler targets were not decompiled")

    handler_slots = []
    for slot in slots:
        ref_entry = command_by_index.get(slot["index"])
        handler_slots.append({
            "index": slot["index"],
            "address": f"0x{slot['slot_address']:x}",
            "target": f"0x{slot['target_address']:x}",
            "target_is_executable": slot["executable"],
            "pinned_parser_reference": ref_entry,
        })

    output = {
        "schema": "lgpe-research.bseq-runtime-dispatch.v1",
        "status": "STATIC_DISPATCH_CROSSREF",
        "build": {
            "game": "Pokemon: Let's Go, Pikachu!",
            "version": "1.0.2",
            "nca_id": "2b7730a9e56498bbafac2002d4908c6b",
            "image_base": f"0x{IMAGE_BASE:x}",
            "main_path": "../1.0.2/2b7730a9e56498bbafac2002d4908c6b_NCA/0/main",
            "main_sha256": main_hash,
        },
        "static_chain": {
            "delegate_initializer": "main+0xaa0b80",
            "delegate_install_store": "main+0xa789b0",
            "controller_callback_field_offset": "0x3e0",
            "sequence_constructor": "main+0x2103c0",
            "sequence_callback_field_offset": "0x190",
            "frame_command_consumer": {
                "address": "main+0x210510",
                "callback_virtual_offset": "0x10",
                "fourth_callback_argument": 0,
                "dispatch_path": "handler_pointer_table",
            },
            "target_frame_consumer": {
                "address": "main+0x210880",
                "callback_virtual_offset": "0x10",
                "fourth_callback_argument": 1,
                "dispatch_path": "inline_switch_in_callback_dispatcher",
            },
            "delegate_vtable": {
                "global_cell": "0x7101608de8",
                "address_point": "0x71015d5ab0",
                "slots": [
                    {"index": 0, "target": "main+0xaa2310"},
                    {"index": 1, "target": "main+0xaa2370"},
                    {"index": 2, "target": "main+0xaa0eb0"},
                ],
            },
            "separate_controller_vtable_candidate": {
                "address_point": "0x71015d3268",
                "installed_by": "main+0xa77c20",
                "rtti_pointer": "0x0",
                "rtti_name_resolved": False,
                "observed_method_slots": [
                    {"slot": 78, "target": "main+0xa8acd0"},
                    {"slot": 152, "target": "main+0xa8ce20"},
                ],
                "is_bseq_callback_vptr": False,
            },
            "callback_dispatcher": {
                "address": "main+0xaa0eb0",
                "record_id_read": "first 32-bit word at callback record pointer",
                "mode_bit": "fourth argument bit 0",
                "zero_mode_call": "indirect handler table lookup by command id",
                "one_mode_call": "inline switch by command id",
            },
            "handler_table_scan": table_scan,
            "handler_slots": handler_slots,
        },
        "sample": {
            "romfs_path": "bin/battle/waza/sequence/ee000.bseq",
            "local_path": "../1.0.2/2b7730a9e56498bbafac2002d4908c6b_NCA/1/bin/battle/waza/sequence/ee000.bseq",
            "size": SAMPLE.stat().st_size,
            "sha256": sample_hash,
            "parser": {
                "name": "pbseqtool SESD parser",
                "commit": PBSEQTOOL_COMMIT,
                "dictionary_sha256": dictionary_hash,
                "license_status": "README permits use as a base; no formal LICENSE file",
            },
            "commands": sample_commands,
        },
        "analysis": {
            "ghidra": "12.2 PUBLIC",
            "jdk": "25.0.5",
            "read_only_source_binary": True,
            "ghidra_project_database_modified_to_create_missing_functions": True,
            "helper_script": "scripts/ghidra/InspectSequenceRuntimeHelpers.java",
            "helper_script_sha256": sha256(PROJECT / "scripts/ghidra/InspectSequenceRuntimeHelpers.java"),
            "helper_wrapper": "scripts/ghidra/Run-InspectSequenceRuntimeHelpers.ps1",
            "helper_wrapper_sha256": sha256(PROJECT / "scripts/ghidra/Run-InspectSequenceRuntimeHelpers.ps1"),
            "helper_log_sha256": sha256(HELPER_LOG),
            "callback_script": "scripts/ghidra/InspectSequenceCallbacks.java",
            "callback_script_sha256": sha256(PROJECT / "scripts/ghidra/InspectSequenceCallbacks.java"),
            "callback_wrapper": "scripts/ghidra/Run-InspectSequenceCallbacks.ps1",
            "callback_wrapper_sha256": sha256(PROJECT / "scripts/ghidra/Run-InspectSequenceCallbacks.ps1"),
            "callback_log_sha256": sha256(CALLBACK_LOG),
            "owner_vtable_script": "scripts/ghidra/InspectSequenceOwnerVtables.java",
            "owner_vtable_script_sha256": sha256(PROJECT / "scripts/ghidra/InspectSequenceOwnerVtables.java"),
            "owner_vtable_wrapper": "scripts/ghidra/Run-InspectSequenceOwnerVtables.ps1",
            "owner_vtable_wrapper_sha256": sha256(PROJECT / "scripts/ghidra/Run-InspectSequenceOwnerVtables.ps1"),
            "owner_vtable_log_sha256": sha256(OWNER_VTABLE_LOG),
        },
        "limits": [
            "The 256-slot table scan is capped at 256; no table terminator was observed, so its total length is not established.",
            "Parser command names and IDs are pinned external reference labels; this cross-reference establishes numeric dispatch targets, not gameplay semantics.",
            "Static code does not prove runtime reachability, command execution, animation/audio outcome, or timing.",
            "The parser-labeled DummyLabel sample target is one AArch64 RET instruction; exact bytes and its sole table-slot data reference are recorded in manifests/bseq-dispatch-boundary.json. This instruction evidence does not assign command gameplay semantics.",
            "The Ghidra project database was modified to create five previously undefined handler functions; the original main file hash was checked before and after and remained unchanged.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"Wrote {args.output}: {len(slots)} executable handler slots, "
        f"{len(command_by_index)} pinned dictionary IDs, "
        f"{len(sample_commands)} actual sample commands."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
