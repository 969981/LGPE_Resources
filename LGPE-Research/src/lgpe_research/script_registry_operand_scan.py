"""Parse exact-build Ghidra instruction-operand evidence for the script registry page."""
from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any


MAIN_SHA256 = "1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8"
IMAGE_BASE = 0x7100000000
PAGE_BASE = 0x710153C000
PAGE_TEXT = "0x710153c000"
SCRIPT_NAME = "InspectScriptRegistryOperandScan.java"
WRAPPER_NAME = "Run-InspectScriptRegistryOperandScan.ps1"
EXPECTED_PROGRAM_PATH_SUFFIX = (
    "1.0.2/2b7730a9e56498bbafac2002d4908c6b_NCA/0/main"
)
EXPECTED_DATA_CELLS = {
    "MapChangeCoreNamePointer": "0x153c878",
    "CaptureCallFunctionPointer": "0x153c880",
    "GetCaptureResultFunctionPointer": "0x153c890",
    "OperandPageCandidate_153ced8": "0x153ced8",
    "OperandPageCandidate_153cf20": "0x153cf20",
    "OperandPageCandidate_153cf68": "0x153cf68",
    "OperandPageCandidate_153cfb0": "0x153cfb0",
}
EXPECTED_FUNCTION_POINTERS = {
    "CaptureCallFunctionPointer": "0x71001a61e0",
    "GetCaptureResultFunctionPointer": "0x71001a64c0",
}

_SUMMARY = re.compile(
    r"SUMMARY\s+instructionCount=(\d+)\s+operandHits=(\d+)\s+"
    r"ownerCount=(\d+)\s+decompiled=(\d+)\s+failures=(\d+)\s+"
    r"readOnlySource=(true|false)\s+readOnlyProject=(true|false)"
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _main_offset(address: str) -> str:
    value = int(address, 16)
    if value < IMAGE_BASE:
        raise ValueError(f"Ghidra address is below the expected image base: {address}")
    return f"0x{value - IMAGE_BASE:x}"


def _clean_log_fields(fields: list[str]) -> list[str]:
    return [
        re.sub(r"\s+\(GhidraScript\)\s*$", "", field).strip()
        for field in fields
    ]


def _key_values(fields: list[str]) -> dict[str, str]:
    values: dict[str, str] = {}
    for field in fields:
        key, separator, value = field.partition("=")
        if not separator or not key or key in values:
            raise ValueError(f"malformed or duplicate Ghidra summary field: {field}")
        values[key] = value
    return values


def build_script_registry_operand_scan_report(
    project: Path,
    trace_log: Path,
    *,
    main_sha256: str,
) -> dict[str, Any]:
    if main_sha256 != MAIN_SHA256:
        raise ValueError("source is not bound to the expected LGPE Pikachu 1.0.2 main")

    project = project.resolve()
    trace_log = trace_log.resolve()
    scripts = project / "scripts" / "ghidra"
    script_path = scripts / SCRIPT_NAME
    wrapper_path = scripts / WRAPPER_NAME
    for path in (trace_log, script_path, wrapper_path):
        if not path.is_file():
            raise FileNotFoundError(f"required operand-scan evidence missing: {path}")

    log = trace_log.read_text(encoding="utf-8", errors="replace")
    program_marker = f"{SCRIPT_NAME}> PROGRAM\t"
    program_lines = [line.split(program_marker, 1)[1] for line in log.splitlines() if program_marker in line]
    if len(program_lines) != 1:
        raise ValueError(f"expected one Ghidra PROGRAM record, found {len(program_lines)}")
    program_fields = _clean_log_fields(program_lines[0].split("\t", 2))
    if len(program_fields) != 3:
        raise ValueError("malformed Ghidra PROGRAM record")
    program_name, base_field, executable_path = program_fields
    if program_name != "main" or base_field.casefold() != "base=7100000000":
        raise ValueError("Ghidra PROGRAM record is not the expected main image/base")
    executable_path = re.sub(r"\s+\(GhidraScript\)\s*$", "", executable_path).strip()
    normalized_path = executable_path.replace("\\", "/").casefold()
    if not normalized_path.endswith(EXPECTED_PROGRAM_PATH_SUFFIX.casefold()):
        raise ValueError("Ghidra PROGRAM path does not identify the expected local 1.0.2 NCA main")

    summary_matches = list(_SUMMARY.finditer(log))
    if len(summary_matches) != 1:
        raise ValueError(f"expected one Ghidra operand-scan summary, found {len(summary_matches)}")
    summary_match = summary_matches[0]
    instruction_count, operand_count, owner_count, decompiled, failures = map(
        int, summary_match.groups()[:5]
    )
    read_only_source, read_only_project = summary_match.groups()[5:]
    if read_only_source != "true" or read_only_project != "true":
        raise ValueError("Ghidra operand scan was not verified as read-only")
    if instruction_count <= 0 or decompiled + failures != owner_count:
        raise ValueError("Ghidra instruction/decompilation counts are inconsistent")

    hits: dict[str, dict[str, Any]] = {}
    contexts: dict[str, list[dict[str, str]]] = {}
    data_cells: dict[str, dict[str, Any]] = {}
    data_references: list[dict[str, Any]] = []
    pointer_slots: list[dict[str, Any]] = []
    pointer_slot_errors: list[dict[str, str]] = []
    code_targets: dict[str, dict[str, Any]] = {}
    code_target_summary: dict[str, int] | None = None
    code_target_errors: list[dict[str, str]] = []
    for line in log.splitlines():
        marker = f"{SCRIPT_NAME}> OPERAND_HIT\t"
        if marker in line:
            fields = _clean_log_fields(line.split(marker, 1)[1].split("\t", 3))
            if len(fields) != 3:
                raise ValueError(f"malformed operand hit line: {line}")
            address, owner, assembly = fields
            if address in hits:
                raise ValueError(f"duplicate operand-hit address: {address}")
            if PAGE_TEXT not in assembly.lower():
                raise ValueError(f"operand hit does not materialize the expected page: {line}")
            hits[address] = {
                "address": f"0x{address}",
                "main_offset": _main_offset(address),
                "owner": None if owner == "NONE" else {
                    "address": f"0x{owner}",
                    "main_offset": _main_offset(owner),
                },
                "assembly": assembly,
            }
            contexts[address] = []
            continue

        context_marker = f"{SCRIPT_NAME}> CONTEXT\t"
        if context_marker in line:
            fields = _clean_log_fields(line.split(context_marker, 1)[1].split("\t", 2))
            if len(fields) != 3:
                raise ValueError(f"malformed operand context line: {line}")
            hit_address, address, assembly = fields
            if hit_address in contexts:
                contexts[hit_address].append({
                    "address": f"0x{address}",
                    "main_offset": _main_offset(address),
                    "assembly": assembly,
                })
            continue

        data_marker = f"{SCRIPT_NAME}> DATA_VALUE\t"
        if data_marker in line:
            fields = _clean_log_fields(line.split(data_marker, 1)[1].split("\t", 9))
            if len(fields) != 9:
                raise ValueError(f"malformed DATA_VALUE line: {line}")
            label, cell, raw_value, mapped, block, executable, exact, owner, data_type = fields
            if label in data_cells:
                raise ValueError(f"duplicate DATA_VALUE label: {label}")
            if label not in EXPECTED_DATA_CELLS:
                raise ValueError(f"unexpected DATA_VALUE label: {label}")
            if _main_offset(cell) != EXPECTED_DATA_CELLS[label]:
                raise ValueError(f"DATA_VALUE cell mismatch for {label}: {cell}")
            data_cells[label] = {
                "cell": f"0x{cell}",
                "main_offset": _main_offset(cell),
                "raw_value": raw_value,
                "target_mapped": mapped.casefold() == "true",
                "target_block": block,
                "target_executable": executable.casefold() == "true",
                "target_function_exact": None if exact == "NONE" else {
                    "address": f"0x{exact}",
                    "main_offset": _main_offset(exact),
                },
                "target_function_containing": None if owner == "NONE" else {
                    "address": f"0x{owner}",
                    "main_offset": _main_offset(owner),
                },
                "defined_data_type": data_type,
            }
            continue

        data_ref_marker = f"{SCRIPT_NAME}> DATA_REF\t"
        if data_ref_marker in line:
            fields = _clean_log_fields(line.split(data_ref_marker, 1)[1].split("\t", 5))
            if len(fields) != 5:
                raise ValueError(f"malformed DATA_REF line: {line}")
            label, cell, source, ref_type, owner = fields
            data_references.append({
                "label": label,
                "cell": f"0x{cell}",
                "source": f"0x{source}",
                "source_main_offset": _main_offset(source),
                "reference_type": ref_type,
                "owner": None if owner == "NONE" else {
                    "address": f"0x{owner}",
                    "main_offset": _main_offset(owner),
                },
            })
            continue

        slot_marker = f"{SCRIPT_NAME}> POINTER_SLOT\t"
        if slot_marker in line:
            fields = _clean_log_fields(line.split(slot_marker, 1)[1].split("\t", 9))
            if len(fields) != 9:
                raise ValueError(f"malformed POINTER_SLOT line: {line}")
            label, index, slot, raw_value, mapped, block, executable, exact, owner = fields
            pointer_slots.append({
                "label": label,
                "index": int(index),
                "slot": f"0x{slot}",
                "slot_main_offset": _main_offset(slot),
                "raw_value": raw_value,
                "target_mapped": mapped.casefold() == "true",
                "target_block": block,
                "target_executable": executable.casefold() == "true",
                "target_function_exact": None if exact == "NONE" else {
                    "address": f"0x{exact}",
                    "main_offset": _main_offset(exact),
                },
                "target_function_containing": None if owner == "NONE" else {
                    "address": f"0x{owner}",
                    "main_offset": _main_offset(owner),
                },
            })
            continue

        slot_error_marker = f"{SCRIPT_NAME}> POINTER_SLOT_ERROR\t"
        if slot_error_marker in line:
            fields = _clean_log_fields(line.split(slot_error_marker, 1)[1].split("\t", 3))
            if len(fields) != 4:
                raise ValueError(f"malformed POINTER_SLOT_ERROR line: {line}")
            label, index, slot, error = fields
            pointer_slot_errors.append({
                "label": label,
                "index": index,
                "slot": f"0x{slot}",
                "error": error,
            })
            continue

        code_target_marker = f"{SCRIPT_NAME}> CODE_TARGET\t"
        if code_target_marker in line:
            fields = _clean_log_fields(line.split(code_target_marker, 1)[1].split("\t", 5))
            if len(fields) != 5:
                raise ValueError(f"malformed CODE_TARGET line: {line}")
            address, entry, byte_field, instruction_field, temporary_field = fields
            byte_values = _key_values([byte_field, instruction_field, temporary_field])
            if address in code_targets:
                raise ValueError(f"duplicate CODE_TARGET address: {address}")
            code_targets[address] = {
                "address": f"0x{address}",
                "main_offset": _main_offset(address),
                "entry": f"0x{entry}",
                "entry_main_offset": _main_offset(entry),
                "byte_count": int(byte_values["bytes"]),
                "instruction_count": int(byte_values["instructions"]),
                "temporary_boundary": byte_values["temporary"].casefold() == "true",
                "incoming_references": [],
                "instructions": [],
                "calls": [],
                "decompiled_chars": None,
                "decompile_error": None,
            }
            continue

        target_incoming_marker = f"{SCRIPT_NAME}> CODE_TARGET_INCOMING\t"
        if target_incoming_marker in line:
            fields = _clean_log_fields(line.split(target_incoming_marker, 1)[1].split("\t", 4))
            if len(fields) != 4:
                raise ValueError(f"malformed CODE_TARGET_INCOMING line: {line}")
            target, source, ref_type, owner = fields
            if target not in code_targets:
                raise ValueError(f"incoming reference precedes target declaration: {target}")
            code_targets[target]["incoming_references"].append({
                "source": f"0x{source}",
                "source_main_offset": _main_offset(source),
                "reference_type": ref_type,
                "owner": None if owner == "NONE" else {
                    "address": f"0x{owner}",
                    "main_offset": _main_offset(owner),
                },
            })
            continue

        target_instruction_marker = f"{SCRIPT_NAME}> CODE_TARGET_INSN\t"
        if target_instruction_marker in line:
            fields = _clean_log_fields(line.split(target_instruction_marker, 1)[1].split("\t", 4))
            if len(fields) != 4:
                raise ValueError(f"malformed CODE_TARGET_INSN line: {line}")
            target, address, instruction_bytes, assembly = fields
            if target not in code_targets:
                raise ValueError(f"instruction precedes target declaration: {target}")
            code_targets[target]["instructions"].append({
                "address": f"0x{address}",
                "main_offset": _main_offset(address),
                "bytes": instruction_bytes,
                "assembly": assembly,
            })
            continue

        target_call_marker = f"{SCRIPT_NAME}> CODE_TARGET_CALL\t"
        if target_call_marker in line:
            fields = _clean_log_fields(line.split(target_call_marker, 1)[1].split("\t", 4))
            if len(fields) != 4:
                raise ValueError(f"malformed CODE_TARGET_CALL line: {line}")
            target, callsite, callee, assembly = fields
            if target not in code_targets:
                raise ValueError(f"call precedes target declaration: {target}")
            code_targets[target]["calls"].append({
                "callsite": f"0x{callsite}",
                "callsite_main_offset": _main_offset(callsite),
                "callee": f"0x{callee}",
                "callee_main_offset": _main_offset(callee),
                "assembly": assembly,
                "direct": True,
            })
            continue

        target_indirect_marker = f"{SCRIPT_NAME}> CODE_TARGET_INDIRECT_CALL\t"
        if target_indirect_marker in line:
            fields = _clean_log_fields(line.split(target_indirect_marker, 1)[1].split("\t", 3))
            if len(fields) != 3:
                raise ValueError(f"malformed CODE_TARGET_INDIRECT_CALL line: {line}")
            target, callsite, assembly = fields
            if target not in code_targets:
                raise ValueError(f"indirect call precedes target declaration: {target}")
            code_targets[target]["calls"].append({
                "callsite": f"0x{callsite}",
                "callsite_main_offset": _main_offset(callsite),
                "callee": None,
                "callee_main_offset": None,
                "assembly": assembly,
                "direct": False,
            })
            continue

        target_decompiled_marker = f"{SCRIPT_NAME}> CODE_TARGET_DECOMPILED_BEGIN\t"
        if target_decompiled_marker in line:
            fields = _clean_log_fields(line.split(target_decompiled_marker, 1)[1].split("\t", 2))
            if len(fields) != 2:
                raise ValueError(f"malformed CODE_TARGET_DECOMPILED_BEGIN line: {line}")
            target, chars_field = fields
            if target not in code_targets:
                raise ValueError(f"decompilation precedes target declaration: {target}")
            char_values = _key_values([chars_field])
            code_targets[target]["decompiled_chars"] = int(char_values["chars"])
            continue

        target_decompile_error_marker = f"{SCRIPT_NAME}> CODE_TARGET_DECOMPILE_FAILED\t"
        if target_decompile_error_marker in line:
            fields = _clean_log_fields(line.split(target_decompile_error_marker, 1)[1].split("\t", 2))
            if len(fields) != 2:
                raise ValueError(f"malformed CODE_TARGET_DECOMPILE_FAILED line: {line}")
            target, error = fields
            if target not in code_targets:
                raise ValueError(f"decompilation failure precedes target declaration: {target}")
            code_targets[target]["decompile_error"] = error
            continue

        target_summary_marker = f"{SCRIPT_NAME}> CODE_TARGET_SUMMARY\t"
        if target_summary_marker in line:
            if code_target_summary is not None:
                raise ValueError("duplicate CODE_TARGET_SUMMARY")
            code_target_summary = {
                key: int(value)
                for key, value in _key_values(
                    _clean_log_fields(line.split(target_summary_marker, 1)[1].split("\t", 4))
                ).items()
            }
            continue

        for error_kind in ("CODE_TARGET_NOT_ENTRY", "CODE_TARGET_CREATE_FAILED"):
            error_marker = f"{SCRIPT_NAME}> {error_kind}\t"
            if error_marker in line:
                fields = _clean_log_fields(line.split(error_marker, 1)[1].split("\t", 2))
                code_target_errors.append({"kind": error_kind, "fields": "\t".join(fields)})
                break

    if len(hits) != operand_count:
        raise ValueError(f"summary says {operand_count} operand hits, parsed {len(hits)}")
    if set(data_cells) != set(EXPECTED_DATA_CELLS):
        raise ValueError("Ghidra data-cell probe set is incomplete")
    function_pointer_slot_crosschecks: list[dict[str, Any]] = []
    for label, expected_target in EXPECTED_FUNCTION_POINTERS.items():
        actual_target = data_cells[label]["raw_value"].casefold()
        if actual_target != expected_target.casefold():
            raise ValueError(f"function-pointer value mismatch for {label}: {actual_target}")
        function_pointer_slot_crosschecks.append({
            "label": label,
            "cell": data_cells[label]["cell"],
            "main_offset": data_cells[label]["main_offset"],
            "expected_target": expected_target,
            "actual_target": data_cells[label]["raw_value"],
            "target_matches": True,
            "saved_incoming_reference_count": sum(
                1 for reference in data_references if reference["label"] == label
            ),
        })
    if code_target_summary is None:
        raise ValueError("missing CODE_TARGET_SUMMARY")
    if code_target_summary.get("uniqueTargets") != len(code_targets):
        raise ValueError("CODE_TARGET_SUMMARY target count does not match parsed targets")
    if code_target_summary.get("decompiled", 0) + code_target_summary.get("failures", 0) != len(code_targets):
        raise ValueError("CODE_TARGET_SUMMARY decompilation counts are inconsistent")
    for address, target in code_targets.items():
        if len(target["instructions"]) != target["instruction_count"]:
            raise ValueError(f"instruction count mismatch for code target {address}")
        if (target["decompiled_chars"] is None) == (target["decompile_error"] is None):
            raise ValueError(f"code target {address} lacks a single decompile outcome")
    non_null_owners = {
        row["owner"]["address"] for row in hits.values() if row["owner"] is not None
    }
    if len(non_null_owners) != owner_count:
        raise ValueError(f"summary says {owner_count} owners, parsed {len(non_null_owners)}")
    for address, rows in contexts.items():
        if not any(row["address"].lower() == f"0x{address}".lower() for row in rows):
            raise ValueError(f"operand hit {address} has no matching context instruction")
        hits[address]["context"] = rows

    return {
        "schema": "lgpe-research.script-registry-operand-scan.v1",
        "status": "STATIC_PAGE_OPERAND_SCAN_ONLY",
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
            "program_name": program_name,
            "image_base": "0x7100000000",
            "program_path_suffix": EXPECTED_PROGRAM_PATH_SUFFIX,
            "instruction_count": instruction_count,
            "operand_hit_count": len(hits),
            "owner_count": owner_count,
            "decompiled_owner_count": decompiled,
            "decompile_failures": failures,
            "read_only_source": True,
            "read_only_project": True,
            "script_sha256": _sha256(script_path),
            "wrapper_sha256": _sha256(wrapper_path),
            "evidence_log_sha256": _sha256(trace_log),
            "evidence_log": trace_log.relative_to(project).as_posix(),
        },
        "search": {
            "operand_text_contains": PAGE_TEXT,
            "page_base": PAGE_TEXT,
            "target_function_slots": {
                "CaptureCall": "main+0x153c880",
                "GetCaptureResult": "main+0x153c890",
            },
            "matches": list(hits.values()),
            "data_cells": list(data_cells.values()),
            "data_references": data_references,
            "function_pointer_slot_crosschecks": function_pointer_slot_crosschecks,
            "indirect_target_slots": pointer_slots,
            "indirect_target_slot_errors": pointer_slot_errors,
            "code_targets": list(code_targets.values()),
            "code_target_summary": code_target_summary,
            "code_target_errors": code_target_errors,
        },
        "limitations": [
            "The scan finds explicit disassembly operand text for the page address; it does not establish dynamic or computed table indexing.",
            "Context and decompilation are static observations and do not prove runtime reachability or API semantics.",
        ],
    }
