"""Validate a read-only exact-build trace of capture-named result handlers."""
from __future__ import annotations

import re
from typing import Any


MAIN_SHA256 = "1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8"
MARKER = "InspectCaptureGetterCallers.java>"


def _payloads(text: str) -> list[str]:
    records = []
    inside_decomp = False
    for line in text.splitlines():
        marker_at = line.find(MARKER)
        if marker_at < 0:
            if inside_decomp:
                records.append(line)
            continue
        payload = line[marker_at:].split("> ", 1)[1].strip()
        payload = re.sub(r"\s+\(GhidraScript\)\s*$", "", payload)
        records.append(payload)
        if payload.startswith("DECOMPILED_BEGIN\t"):
            inside_decomp = True
        elif payload.startswith("DECOMPILED_END\t"):
            inside_decomp = False
    return records


def _records(records: list[str], kind: str) -> list[dict[str, str]]:
    output = []
    for record in records:
        parts = record.split("\t")
        if not parts or parts[0] != kind:
            continue
        fields: dict[str, str] = {}
        for part in parts[1:]:
            if "=" in part:
                key, value = part.split("=", 1)
                fields[key] = value
        output.append(fields)
    return output


def _one(records: list[dict[str, str]], label: str) -> dict[str, str]:
    if not records:
        raise ValueError(f"missing Ghidra {label} record")
    return records[-1]


def _function_decomp(records: list[str], address: str) -> str:
    start = f"DECOMPILED_BEGIN\t{address}\t"
    end = f"DECOMPILED_END\t{address}"
    start_at = next((i for i, record in enumerate(records) if record.startswith(start)), None)
    if start_at is None:
        raise ValueError(f"missing decompilation for {address}")
    end_at = next((i for i in range(start_at + 1, len(records)) if records[i].startswith(end)), None)
    if end_at is None:
        raise ValueError(f"unterminated decompilation for {address}")
    return "\n".join(records[start_at + 1 : end_at])


def build_capture_getter_crossref_report(
    log_text: str,
    *,
    script_sha256: str,
    wrapper_sha256: str,
    log_sha256: str,
) -> dict[str, Any]:
    """Validate Ghidra evidence and retain direct-call ownership uncertainty."""
    for label, value in (("script", script_sha256), ("wrapper", wrapper_sha256), ("log", log_sha256)):
        if not re.fullmatch(r"[0-9a-f]{64}", value):
            raise ValueError(f"{label} SHA-256 must be 64 lowercase hexadecimal characters")

    records = _payloads(log_text)
    build = _one(_records(records, "BUILD"), "build")
    summary = _one(_records(records, "SUMMARY"), "summary")
    expected_build = {
        "game": "Pokemon-Lets-Go-Pikachu",
        "version": "1.0.2",
        "nca_id": "2b7730a9e56498bbafac2002d4908c6b",
        "image_base": "0x7100000000",
        "main_sha256": MAIN_SHA256,
    }
    if any(build.get(key) != value for key, value in expected_build.items()):
        raise ValueError("Ghidra trace is not bound to the expected LGPE Pikachu 1.0.2 main")
    if (
        summary.get("main_sha256") != MAIN_SHA256
        or summary.get("readOnlySource") != "true"
        or summary.get("readOnlyProject") != "true"
        or int(summary.get("failures", "-1")) != 0
        or int(summary.get("decompiled", "-1")) != 7
        or int(summary.get("instructions", "-1")) != 1264
        or int(summary.get("directCalls", "-1")) != 71
        or int(summary.get("temporaryFunctions", "-1")) != 1
    ):
        raise ValueError("Ghidra trace did not finish with the expected exact-build read-only summary")

    incoming = _records(records, "INCOMING")
    incoming_summaries = _records(records, "INCOMING_SUMMARY")
    for item in incoming_summaries:
        actual = sum(row.get("target") == item.get("target") for row in incoming)
        if int(item.get("count", "-1")) != actual:
            raise ValueError(f"incoming-reference count disagrees for {item.get('target')}")

    handler_refs = [row for row in incoming if row.get("target") == "main+0x28ee10"]
    expected_calls = {
        ("main+0x3059d4", "main+0x305970", "UNCONDITIONAL_CALL"),
        ("main+0x28e978", "main+0x28e7f0", "UNCONDITIONAL_CALL"),
        ("main+0x319fe0", "main+0x319f80", "UNCONDITIONAL_CALL"),
        ("main+0x8549fc", "NONE", "UNCONDITIONAL_CALL"),
    }
    actual_calls = {
        (row.get("from"), row.get("owner"), row.get("type")) for row in handler_refs
    }
    if actual_calls != expected_calls:
        raise ValueError("shared handler direct callers do not match the expected 1.0.2 references")
    if len(handler_refs) != 4:
        raise ValueError("shared handler direct-reference count is not four")

    expected_other_refs = {
        "main+0x1a64c0": {("main+0x153c890", "NONE", "DATA")},
        "main+0x1aae40": {("main+0x1a6524", "main+0x1a64c0", "UNCONDITIONAL_CALL")},
        "main+0x28e7f0": {("main+0x15472a0", "NONE", "DATA")},
        "main+0x28eb60": {("main+0x28e934", "main+0x28e7f0", "UNCONDITIONAL_CALL")},
        "main+0x305970": {
            ("main+0x2fdf34", "main+0x2fd8a0", "UNCONDITIONAL_CALL"),
            ("main+0x2fdf80", "main+0x2fd8a0", "UNCONDITIONAL_CALL"),
        },
        "main+0x319f80": {("main+0x319cc4", "NONE", "UNCONDITIONAL_CALL")},
    }
    for target, expected in expected_other_refs.items():
        actual = {
            (row.get("from"), row.get("owner"), row.get("type"))
            for row in incoming
            if row.get("target") == target
        }
        if actual != expected:
            raise ValueError(f"incoming references do not match the recorded evidence for {target}")

    temp_records = [r for r in records if r.startswith("TEMPORARY_FUNCTION_BOUNDARY\t")]
    if len(temp_records) != 1 or not temp_records[0].startswith(
        "TEMPORARY_FUNCTION_BOUNDARY\tmain+0x28e7f0\tread_only_database_changes_discarded=true"
    ):
        raise ValueError("temporary function boundary was not discarded for main+0x28e7f0")

    candidate = _function_decomp(records, "main+0x28e7f0")
    ordered_fragments = (
        "case 2:",
        "FUN_710028eb60(param_1);",
        "case 3:",
        "FUN_710028ee10(&lStack_68,lVar14,plVar15);",
    )
    positions = [candidate.find(fragment) for fragment in ordered_fragments]
    if any(position < 0 for position in positions) or positions != sorted(positions):
        raise ValueError("temporary candidate decompilation does not show the expected handler order")
    helper = _function_decomp(records, "main+0x28ee10")
    helper_fragments = (
        "(param_3,0x3b0,8)",
        "*(long *)(param_2 + 0x68)",
        "*(long *)(param_2 + 0x70)",
        "*param_1 = lVar1;",
    )
    if any(fragment not in helper for fragment in helper_fragments):
        raise ValueError("shared helper decompilation does not match the observed allocation/input/result operations")
    api_wrapper = _function_decomp(records, "main+0x1a64c0")
    wrapper_fragments = (
        "uVar11 = *(undefined8 *)(param_2 + 8);",
        "FUN_71001aae40(&local_68,lVar10,*(long **)(*(long *)PTR_DAT_71015faab8 + 0x68));",
        "*(undefined8 *)(lVar2 + 200) = uVar11;",
        "return 0;",
    )
    if any(fragment not in api_wrapper for fragment in wrapper_fragments):
        raise ValueError("GetCaptureResult wrapper decompilation does not match the observed input/helper/result flow")

    function_sizes = {}
    for record in records:
        if record.startswith("FUNCTION_BEGIN\t"):
            parts = record.split("\t")
            fields = _records(["FUNCTION_BEGIN\t" + "\t".join(parts[2:])], "FUNCTION_BEGIN")[0]
            function_sizes[parts[1]] = int(fields["bytes"])

    calls = _records(records, "CALL")
    target_calls = [row for row in calls if row.get("target") == "main+0x28ee10"]
    if {row.get("from") for row in target_calls} != {"main+0x28e978", "main+0x3059d4", "main+0x319fe0"}:
        raise ValueError("direct-call instruction records do not corroborate defined handler callers")
    if not any(
        row.get("from") == "main+0x1a6524" and row.get("target") == "main+0x1aae40"
        for row in calls
    ):
        raise ValueError("GetCaptureResult wrapper callsite does not corroborate its handler reference")
    unowned_window = _records(records, "UNOWNED_WINDOW")
    window_by_address = {row.get("address"): row for row in unowned_window}
    required_window = {
        "main+0x8549f0": "ldr x1,[x8, #0x68]",
        "main+0x8549f4": "add x8,sp,#0x50",
        "main+0x8549f8": "mov x0,x22",
        "main+0x8549fc": "bl 0x710028ee10",
        "main+0x854a00": "ldr x8,[sp, #0x58]",
        "main+0x854a04": "str x8,[sp, #0x20]",
    }
    if any(window_by_address.get(address, {}).get("instruction") != instruction
           for address, instruction in required_window.items()):
        raise ValueError("unowned callsite context does not match the recorded input/result stack sequence")
    unowned = _one(_records(records, "UNOWNED_CALLSITE"), "unowned callsite")
    if unowned.get("address") != "main+0x8549fc" or unowned.get("owner") != "NONE":
        raise ValueError("unowned callsite is not the expected main+0x8549fc site")

    return {
        "schema": "lgpe-research.capture-getter-callers.v2",
        "status": "STATIC_SHARED_HANDLER_CALLERS",
        "build": {
            "game": "Pokemon: Let's Go, Pikachu!",
            "version": "1.0.2",
            "nca_id": "2b7730a9e56498bbafac2002d4908c6b",
            "image_base": "0x7100000000",
            "main_sha256": MAIN_SHA256,
        },
        "trace": {
            "tool": "Ghidra 12.2",
            "mode": "-noanalysis -readOnly",
            "script_sha256": script_sha256,
            "wrapper_sha256": wrapper_sha256,
            "evidence_log_sha256": log_sha256,
        },
        "probe_summary": {
            "decompiled_functions": int(summary["decompiled"]),
            "instructions": int(summary["instructions"]),
            "direct_calls": int(summary["directCalls"]),
            "temporary_function_boundaries": int(summary["temporaryFunctions"]),
            "failures": int(summary["failures"]),
            "read_only_source": True,
            "read_only_project": True,
            "main_hash_unchanged": True,
        },
        "capture_result_api_wrapper": {
            "address": "main+0x1a64c0",
            "byte_length": function_sizes.get("main+0x1a64c0"),
            "decompiled_instruction_count": 122,
            "incoming_data_reference": {
                "from": "main+0x153c890",
                "owner": "NONE",
                "reference_type": "DATA",
                "function_call": False,
            },
            "direct_handler_callsite": "main+0x1a6524",
            "direct_handler": "main+0x1aae40",
            "observed_input_access": "qword from param_2+0x8",
            "observed_result_projection": [
                "copies the qword to a returned object's offset +0xc8 on one branch",
                "writes zero to an adjacent 16-bit field on that branch",
                "returns constant zero",
            ],
            "field_and_outcome_semantics": "UNKNOWN",
        },
        "temporary_candidate": {
            "address": "main+0x28e7f0",
            "saved_database_function": False,
            "byte_length": function_sizes.get("main+0x28e7f0"),
            "decompiled_instruction_count": 217,
            "incoming_data_reference": {
                "from": "main+0x15472a0",
                "owner": "NONE",
                "function_call": False,
            },
            "static_order_observation": [
                "case 2 calls main+0x28eb60",
                "the decompiler output continues into case 3 and calls main+0x28ee10",
            ],
            "boundary_persisted": False,
        },
        "shared_handler": {
            "address": "main+0x28ee10",
            "byte_length": function_sizes.get("main+0x28ee10"),
            "decompiled_instruction_count": 120,
            "direct_incoming_reference_count": len(handler_refs),
            "direct_callers": [
                {
                    "callsite": row["from"],
                    "owner": row["owner"],
                    "reference_type": row["type"],
                    "owner_boundary_persisted": row["owner"] not in {"NONE", "main+0x28e7f0"},
                }
                for row in handler_refs
            ],
            "observed_decompile_operations": [
                "allocates 0x3b0 bytes",
                "reads object qwords through param_2+0x68 and param_2+0x70",
                "writes the local result pointer through param_1",
            ],
        },
        "other_callers": {
            "main+0x305970": {
                "incoming_direct_callers": ["main+0x2fdf34", "main+0x2fdf80"],
                "shared_handler_callsite": "main+0x3059d4",
            },
            "main+0x319f80": {
                "incoming_direct_callers": ["main+0x319cc4"],
                "shared_handler_callsite": "main+0x319fe0",
            },
            "unowned_region": {
                "shared_handler_callsite": "main+0x8549fc",
                "owner": "NONE",
                "result_stack_read": "main+0x854a00",
                "subsequent_stack_store": "main+0x854a04",
            },
        },
        "interpretation": {
            "handler_specific_to_capture": "NOT_ESTABLISHED",
            "capture_outcome_or_probability": "UNKNOWN",
            "rng_linkage": "UNKNOWN",
            "runtime_execution": "UNVERIFIED",
            "temporary_boundary_is_persisted_analysis": False,
        },
    }
