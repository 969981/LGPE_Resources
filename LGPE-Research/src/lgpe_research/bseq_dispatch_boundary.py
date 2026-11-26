"""Validate an exact-build Ghidra probe of the BSEQ handler table boundary."""
from __future__ import annotations

import re


MAIN_SHA256 = "1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8"
TABLE_CELL = "7101608df8"
TABLE_ADDRESS = "71015d4c70"
TARGET_ADDRESS = "7100ada060"


def _records(log_text: str, marker: str) -> list[dict[str, str]]:
    records = []
    for line in log_text.splitlines():
        wrapped_marker = f"InspectBseqDispatchBoundary.java> {marker}\t"
        marker_at = line.find(wrapped_marker)
        if marker_at >= 0:
            payload = line[marker_at:].split("> ", 1)[1]
        elif line.startswith(f"{marker}\t"):
            payload = line
        else:
            continue
        payload = re.sub(r"\s+\(GhidraScript\)\s*$", "", payload)
        fields: dict[str, str] = {}
        for part in payload.split("\t")[1:]:
            if "=" in part:
                key, value = part.split("=", 1)
                fields[key] = value
        records.append(fields)
    return records


def _one(records: list[dict[str, str]], label: str) -> dict[str, str]:
    if not records:
        raise ValueError(f"missing Ghidra {label} record")
    return records[-1]


def build_bseq_dispatch_boundary_report(
    log_text: str,
    *,
    script_sha256: str,
    wrapper_sha256: str,
    log_sha256: str,
) -> dict:
    """Validate the probe output without treating neighboring pointers as table bounds."""
    build = _one(_records(log_text, "BUILD"), "build")
    summary = _one(_records(log_text, "SUMMARY"), "summary")
    if (
        build.get("main_sha256") != MAIN_SHA256
        or build.get("image_base") != "0x7100000000"
        or build.get("game") != "Pokemon-Lets-Go-Pikachu"
        or build.get("version") != "1.0.2"
        or build.get("nca_id") != "2b7730a9e56498bbafac2002d4908c6b"
    ):
        raise ValueError("Ghidra probe is not bound to the expected LGPE Pikachu 1.0.2 main")
    if (
        summary.get("main_sha256") != MAIN_SHA256
        or summary.get("read_only_source") != "true"
        or summary.get("read_only_project") != "true"
    ):
        raise ValueError("Ghidra probe did not finish with the exact-build read-only summary")

    instruction = _one(_records(log_text, "TARGET_INSTRUCTION"), "target instruction")
    if (
        instruction.get("address") != TARGET_ADDRESS
        or instruction.get("mnemonic", "").casefold() != "ret"
        or instruction.get("length") != "4"
        or instruction.get("bytes_le") != "c0 03 5f d6"
    ):
        raise ValueError("exact-build DummyLabel target bytes do not match one AArch64 RET instruction")
    incoming = _records(log_text, "TARGET_INCOMING_REF")
    incoming_summary = _one(_records(log_text, "TARGET_INCOMING_SUMMARY"), "target incoming-reference summary")
    if incoming_summary.get("address") != TARGET_ADDRESS or int(incoming_summary.get("count", "-1")) != len(incoming):
        raise ValueError("DummyLabel target incoming-reference count disagrees with its reference records")
    if len(incoming) != 1 or incoming[0].get("from") != "71015d4c70" or incoming[0].get("type") != "DATA":
        raise ValueError("DummyLabel target does not have the expected single table-slot data reference")

    table_summary = _one(_records(log_text, "EXTRA_DISPATCH_SUMMARY"), "extended dispatch scan summary")
    if (
        table_summary.get("cell") != TABLE_CELL
        or table_summary.get("table") != TABLE_ADDRESS
        or table_summary.get("first_index") != "256"
        or table_summary.get("full_table_length_proven") != "false"
    ):
        raise ValueError("extended dispatch scan address or conservative boundary claim is invalid")
    slots = _records(log_text, "EXTRA_DISPATCH_SLOT")
    inspected = int(table_summary.get("inspected", "-1"))
    executable_count = int(table_summary.get("executable_targets", "-1"))
    trailing_nonexec = int(table_summary.get("trailing_nonexec", "-1"))
    max_extra_slots = int(table_summary.get("max_extra_slots", "-1"))
    if inspected != len(slots) or inspected > max_extra_slots:
        raise ValueError("extended dispatch slot count does not match the scan summary")
    indexes = [int(slot["index"]) for slot in slots]
    if indexes != list(range(256, 256 + inspected)):
        raise ValueError("extended dispatch slot indexes are not contiguous from index 256")
    if any(slot.get("executable") not in {"true", "false"} for slot in slots):
        raise ValueError("extended dispatch scan contains an invalid executable flag")
    if sum(slot["executable"] == "true" for slot in slots) != executable_count:
        raise ValueError("extended dispatch executable-target count disagrees with slot records")
    calculated_trailing = 0
    for slot in reversed(slots):
        if slot["executable"] == "true":
            break
        calculated_trailing += 1
    if calculated_trailing != trailing_nonexec:
        raise ValueError("extended dispatch trailing non-executable count disagrees with slot records")
    if table_summary.get("stop_reason") == "configured_nonexec_run_observed" and trailing_nonexec != 8:
        raise ValueError("configured non-executable stop run does not match the probe policy")

    return {
        "schema": "lgpe-research.bseq-dispatch-boundary.v1",
        "status": "STATIC_TARGET_BYTES_AND_EXTENDED_POINTER_SCAN",
        "build": {
            "game": "Pokemon: Let's Go, Pikachu!",
            "version": "1.0.2",
            "nca_id": "2b7730a9e56498bbafac2002d4908c6b",
            "image_base": "0x7100000000",
            "main_sha256": MAIN_SHA256,
        },
        "target_probe": {
            "address": "main+0xada060",
            "instruction": instruction["mnemonic"],
            "instruction_bytes_le": instruction["bytes_le"],
            "instruction_length": int(instruction["length"]),
            "incoming_references": [
                {"from": "main+0x15d4c70", "type": incoming[0]["type"], "operand": int(incoming[0]["operand"])}
            ],
            "finding": "The observed table target is a single RET instruction; no indirect branch is present at this address.",
        },
        "extended_pointer_scan": {
            "global_pointer_cell": "0x7101608df8",
            "table_address": "0x71015d4c70",
            "first_index": 256,
            "last_index": indexes[-1] if indexes else None,
            "inspected_slots": inspected,
            "executable_targets": executable_count,
            "non_executable_targets": inspected - executable_count,
            "trailing_nonexec_run": trailing_nonexec,
            "configured_max_extra_slots": max_extra_slots,
            "stop_reason": table_summary.get("stop_reason"),
            "full_table_length_proven": False,
            "observations": [
                {
                    "index": int(slot["index"]),
                    "slot_address": "0x" + slot["address"],
                    "target_address": "0x" + slot["target"],
                    "target_is_executable": slot["executable"] == "true",
                }
                for slot in slots
            ],
        },
        "limitations": [
            "The extended scan walks mapped values after the known 256-pointer probe; executable pointers in adjacent data cannot be distinguished from table entries by this scan alone.",
            "The full dispatch-table length and command-ID bounds remain UNKNOWN.",
            "Parser labels and static table pointers do not establish command semantics or runtime execution.",
        ],
        "provenance": {
            "script": "scripts/ghidra/InspectBseqDispatchBoundary.java",
            "script_sha256": script_sha256,
            "wrapper": "scripts/ghidra/Run-InspectBseqDispatchBoundary.ps1",
            "wrapper_sha256": wrapper_sha256,
            "normalized_evidence_log": "logs/ghidra-bseq-dispatch-boundary-v1-evidence.tsv",
            "normalized_evidence_sha256": log_sha256,
            "raw_stdout_log": "logs/ghidra-bseq-dispatch-boundary-v1.stdout.log",
            "ghidra": "12.2 PUBLIC",
            "jdk": "25.0.5",
            "analysis_mode": "-noanalysis -readOnly",
            "source_main_unchanged": True,
            "project_database_modified": False,
        },
    }
