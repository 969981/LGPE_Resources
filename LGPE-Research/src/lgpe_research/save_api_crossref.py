"""Build a compact, version-pinned report from a Ghidra save API trace log."""

from __future__ import annotations

import re
from typing import Any


EXPECTED_MAIN_SHA256 = "1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8"
EXPECTED_IMAGE_BASE = 0x7100000000
TRACE_MARKER = "InspectSaveApiReferences.java>"


def _latest_run_records(text: str) -> list[str]:
    records = []
    for line in text.splitlines():
        if TRACE_MARKER not in line:
            continue
        payload = line.split(TRACE_MARKER, 1)[1].strip()
        if payload.endswith(" (GhidraScript)"):
            payload = payload[: -len(" (GhidraScript)")].rstrip()
        records.append(payload)

    summary_indexes = [
        index for index, record in enumerate(records) if record.startswith("SUMMARY\t")
    ]
    if not summary_indexes:
        raise ValueError("Ghidra save API trace has no SUMMARY record")
    start = summary_indexes[-2] + 1 if len(summary_indexes) > 1 else 0
    return records[start : summary_indexes[-1] + 1]


def _fields(parts: list[str]) -> dict[str, str]:
    result = {}
    for part in parts:
        if "=" in part:
            key, value = part.split("=", 1)
            result[key] = value
    return result


def _versioned_address(value: str) -> str:
    normalized = value.lower().removeprefix("0x")
    try:
        absolute = int(normalized, 16)
    except ValueError as error:
        raise ValueError(f"invalid Ghidra address: {value!r}") from error
    offset = absolute - EXPECTED_IMAGE_BASE
    if offset < 0:
        raise ValueError(f"address {value!r} is outside the expected main image")
    return f"main+0x{offset:x}"


def build_save_api_crossref_report(
    trace_text: str,
    *,
    trace_script_sha256: str,
    trace_wrapper_sha256: str,
) -> dict[str, Any]:
    """Parse only the latest run, rejecting the wrong build or a writable run."""
    for label, value in (
        ("trace script", trace_script_sha256),
        ("trace wrapper", trace_wrapper_sha256),
    ):
        if not re.fullmatch(r"[0-9a-f]{64}", value):
            raise ValueError(f"{label} SHA-256 must be 64 lowercase hexadecimal characters")

    records = _latest_run_records(trace_text)
    summary: dict[str, str] | None = None
    save_api_code_calls: dict[str, int] = {}
    filesystem_api_code_calls: dict[str, int] = {}
    filesystem_api_symbols: set[str] = set()
    api_thunks: set[str] = set()
    api_xrefs: list[dict[str, str]] = []
    mutation_callsites: list[dict[str, str]] = []
    operation_owners: list[dict[str, str]] = []
    operation_parents: list[dict[str, str]] = []
    save_worker_incoming: int | None = None

    for record in records:
        parts = record.split("\t")
        kind = parts[0]
        if kind == "SUMMARY":
            summary = _fields(parts[1:])
        elif kind == "API_CODE_CALLS" and len(parts) >= 3:
            values = _fields(parts[2:])
            save_api_code_calls[parts[1]] = int(values["count"])
        elif kind == "FS_API_CODE_CALLS" and len(parts) >= 3:
            values = _fields(parts[2:])
            filesystem_api_code_calls[parts[1]] = int(values["count"])
        elif kind == "FS_API_SYMBOL" and len(parts) >= 2:
            filesystem_api_symbols.add(parts[1])
        elif kind == "API_THUNK" and len(parts) >= 2:
            api_thunks.add(parts[1].lower())
        elif kind == "API_XREF" and len(parts) >= 6:
            values = _fields(parts[4:])
            api_xrefs.append(
                {
                    "callsite": parts[1],
                    "reference_type": parts[2],
                    "api": parts[3],
                    "caller": values.get("caller", "<no-function>"),
                    "caller_name": values.get("caller_name", "<no-function>"),
                }
            )
        elif kind == "FS_OPERATION_CALLSITE" and len(parts) >= 5:
            values = _fields(parts[3:])
            mutation_callsites.append(
                {
                    "callsite": _versioned_address(parts[1]),
                    "api": parts[2],
                    "caller": _versioned_address(values["caller"]),
                    "caller_name": values["caller_name"],
                }
            )
        elif kind == "FS_OPERATION_OWNER_XREF_SUMMARY":
            values = _fields(parts[1:])
            operation_owners.append(
                {
                    "function": _versioned_address(values["function"]),
                    "name": values["name"],
                    "incoming_references": int(values["incoming_references"]),
                }
            )
        elif kind == "FS_OPERATION_PARENT_CALLSITE" and len(parts) >= 5:
            values = _fields(parts[2:])
            operation_parents.append(
                {
                    "callsite": _versioned_address(parts[1]),
                    "child": _versioned_address(values["child"]),
                    "parent": _versioned_address(values["parent"]),
                    "parent_name": values["parent_name"],
                }
            )
        elif kind == "INTERNAL_TARGET" and len(parts) >= 4 and parts[1] == "SAVE_WORKER":
            values = _fields(parts[3:])
            save_worker_incoming = int(values["incoming_references"])

    if summary is None:
        raise ValueError("latest Ghidra run has no parseable SUMMARY record")
    if summary.get("main_sha256") != EXPECTED_MAIN_SHA256:
        raise ValueError(f"main SHA-256 mismatch: {summary.get('main_sha256')!r}")
    if summary.get("image_base") != f"0x{EXPECTED_IMAGE_BASE:x}":
        raise ValueError(f"main image base mismatch: {summary.get('image_base')!r}")
    if summary.get("sourceHashUnchanged") != "true" or summary.get("readOnly") != "true":
        raise ValueError("read-only source integrity could not be verified")
    if int(summary.get("decompile_failures", "-1")) != 0:
        raise ValueError("Ghidra reported decompilation failures")
    if save_worker_incoming is None:
        raise ValueError("trace is missing the save worker incoming-reference result")

    fs_call_sites = []
    for reference in api_xrefs:
        if "nn::fs::" not in reference["api"] or "CALL" not in reference["reference_type"]:
            continue
        if reference["caller"].lower() in api_thunks or reference["caller"] == "<no-function>":
            continue
        fs_call_sites.append(
            {
                "callsite": _versioned_address(reference["callsite"]),
                "api": reference["api"],
                "caller": _versioned_address(reference["caller"]),
                "caller_name": reference["caller_name"],
            }
        )

    return {
        "schema": "lgpe-save-api-crossref-v1",
        "status": "STATIC_REFS_ONLY",
        "game": "Pokemon Let's Go Pikachu 1.0.2",
        "main": {
            "sha256": summary["main_sha256"],
            "image_base": summary["image_base"],
            "source_path": "../1.0.2/2b7730a9e56498bbafac2002d4908c6b_NCA/0/main",
        },
        "trace": {
            "tool": "Ghidra 12.2",
            "read_only": True,
            "source_hash_unchanged": True,
            "script": "scripts/ghidra/InspectSaveApiReferences.java",
            "script_sha256": trace_script_sha256,
            "wrapper": "scripts/ghidra/Run-InspectSaveApiReferences.ps1",
            "wrapper_sha256": trace_wrapper_sha256,
        },
        "counts": {
            key: int(value)
            for key, value in summary.items()
            if key not in {"main_sha256", "image_base", "sourceHashUnchanged", "readOnly"}
        },
        "save_data_api_code_calls": {
            name: count
            for name, count in sorted(save_api_code_calls.items())
            if "nn::fs::" in name and "SaveData" in name
        },
        "filesystem_api_symbols": sorted(filesystem_api_symbols),
        "filesystem_api_code_calls": dict(sorted(filesystem_api_code_calls.items())),
        "filesystem_api_call_sites": sorted(
            fs_call_sites, key=lambda item: (item["caller"], item["callsite"], item["api"])
        ),
        "filesystem_mutation_callsites": sorted(
            mutation_callsites, key=lambda item: (item["callsite"], item["api"])
        ),
        "filesystem_operation_owners": sorted(operation_owners, key=lambda item: item["function"]),
        "filesystem_operation_parent_callsites": sorted(
            operation_parents, key=lambda item: (item["callsite"], item["child"])
        ),
        "save_worker": {
            "address": "main+0x24d70",
            "incoming_references": save_worker_incoming,
        },
        "interpretation": {
            "primary_player_save_owner": "UNKNOWN",
            "runtime_execution": "UNVERIFIED",
            "mount_save_data_callsite": "main+0x24e6c",
            "commit_save_data_direct_code_calls": save_api_code_calls.get(
                "<EXTERNAL>::nn::fs::CommitSaveData", 0
            ),
            "ensure_save_data_direct_code_calls": save_api_code_calls.get(
                "<EXTERNAL>::nn::fs::EnsureSaveData", 0
            ),
            "write_file_direct_code_calls": filesystem_api_code_calls.get(
                "<EXTERNAL>::nn::fs::WriteFile", 0
            ),
            "limitations": [
                "Ghidra reference counts describe the saved analysis database, not runtime execution.",
                "Indirect calls and dynamically registered worker entrypoints remain unresolved.",
                "Zero direct imported-API references do not exclude equivalent indirect or wrapped operations.",
                "CreateFile and FlushFile call paths are not assigned to player-save ownership.",
            ],
        },
    }
