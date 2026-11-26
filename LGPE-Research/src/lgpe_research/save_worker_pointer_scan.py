"""Parse the exact-build raw pointer scan for the save worker and helpers."""

from __future__ import annotations

import re
from typing import Any


EXPECTED_MAIN_SHA256 = "1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8"
EXPECTED_IMAGE_BASE = 0x7100000000
TRACE_MARKER = "ScanSaveWorkerPointers.java>"
EXPECTED_TARGETS = {
    "SAVE_WORKER": 0x7100024D70,
    "SAVE_ID_HELPER": 0x7100027200,
    "QUEUE_HELPER": 0x7100027440,
    "STATUS_HELPER": 0x71000275F0,
}


def _latest_run_records(text: str) -> list[str]:
    records = []
    for line in text.splitlines():
        if TRACE_MARKER not in line:
            continue
        record = line.split(TRACE_MARKER, 1)[1].strip()
        if record.endswith(" (GhidraScript)"):
            record = record[: -len(" (GhidraScript)")].rstrip()
        records.append(record)

    summaries = [i for i, record in enumerate(records) if record.startswith("SUMMARY\t")]
    if not summaries:
        raise ValueError("save-worker pointer scan has no SUMMARY record")
    start = summaries[-2] + 1 if len(summaries) > 1 else 0
    return records[start : summaries[-1] + 1]


def _fields(parts: list[str]) -> dict[str, str]:
    result = {}
    for part in parts:
        if "=" in part:
            key, value = part.split("=", 1)
            result[key] = value
    return result


def _address(value: str) -> str:
    normalized = value.lower().removeprefix("0x")
    try:
        absolute = int(normalized, 16)
    except ValueError as error:
        raise ValueError(f"invalid Ghidra address: {value!r}") from error
    offset = absolute - EXPECTED_IMAGE_BASE
    if offset < 0:
        raise ValueError(f"address {value!r} is outside the expected main image")
    return f"main+0x{offset:x}"


def build_save_worker_pointer_scan_report(
    trace_text: str,
    *,
    trace_script_sha256: str,
    trace_wrapper_sha256: str,
    trace_log_sha256: str,
) -> dict[str, Any]:
    """Validate and normalize the latest read-only scan, preserving candidates as unassigned."""
    for label, value in (
        ("trace script", trace_script_sha256),
        ("trace wrapper", trace_wrapper_sha256),
        ("trace log", trace_log_sha256),
    ):
        if not re.fullmatch(r"[0-9a-f]{64}", value):
            raise ValueError(f"{label} SHA-256 must be 64 lowercase hexadecimal characters")

    records = _latest_run_records(trace_text)
    targets: dict[str, dict[str, Any]] = {}
    candidates: list[dict[str, Any]] = []
    address_page_candidates: list[dict[str, Any]] = []
    page_plus_offset_candidates: list[dict[str, Any]] = []
    summary: dict[str, str] | None = None
    qword_total: int | None = None
    image_offset_total: int | None = None
    address_summary: dict[str, str] | None = None

    for record in records:
        parts = record.split("\t")
        kind = parts[0]
        if kind == "TARGET" and len(parts) >= 3:
            label = parts[2]
            if label not in EXPECTED_TARGETS:
                raise ValueError(f"unexpected save-worker scan target: {label}")
            target_address = int(parts[1], 16)
            if target_address != EXPECTED_TARGETS[label]:
                raise ValueError(f"target address mismatch for {label}")
            targets[label] = {
                "address": _address(parts[1]),
                "function": _fields(parts[3:]).get("function", "UNKNOWN"),
            }
        elif kind == "TARGET_XREF_SUMMARY" and len(parts) >= 3:
            label = parts[1]
            if label not in EXPECTED_TARGETS:
                raise ValueError(f"unexpected xref target: {label}")
            targets.setdefault(label, {"address": _address(hex(EXPECTED_TARGETS[label]))})[
                "incoming_references"
            ] = int(_fields(parts[2:])["count"])
        elif kind == "TARGET_SCAN_SUMMARY" and len(parts) >= 3:
            label = parts[1]
            if label not in EXPECTED_TARGETS:
                raise ValueError(f"unexpected pointer-scan target: {label}")
            values = _fields(parts[2:])
            target = targets.setdefault(label, {"address": _address(hex(EXPECTED_TARGETS[label]))})
            target["absolute_qword_matches"] = int(values["absolute_qword"])
            target["image_offset_dword_matches"] = int(values["image_offset_dword"])
        elif kind == "POINTER_CANDIDATE" and len(parts) >= 7:
            candidate_kind, block, slot, label, arrow, target = parts[1:7]
            if label not in EXPECTED_TARGETS or arrow != "->":
                raise ValueError("malformed or unexpected pointer candidate")
            if int(target, 16) != EXPECTED_TARGETS[label]:
                raise ValueError(f"candidate target mismatch for {label}")
            candidates.append({
                "kind": candidate_kind,
                "block": block,
                "slot": _address(slot),
                "target_label": label,
                "target": _address(target),
                "classification": "UNASSIGNED_RAW_CANDIDATE",
            })
        elif kind == "ADDRESS_PAGE_CANDIDATE" and len(parts) >= 4:
            values = _fields(parts[3:])
            address_page_candidates.append({
                "address": _address(parts[1]),
                "instruction": parts[2],
                "register": values.get("register", "UNKNOWN"),
            })
        elif kind == "PAGE_PLUS_OFFSET_CANDIDATE" and len(parts) >= 5:
            values = _fields(parts[3:])
            page_plus_offset_candidates.append({
                "page_materialization": _address(parts[1]),
                "offset_add": _address(parts[2]),
                "register": values.get("register", "UNKNOWN"),
                "instruction": parts[4],
                "classification": "UNASSIGNED_PAGE_PLUS_OFFSET_CANDIDATE",
            })
        elif kind == "QWORD_SCAN_SUMMARY" and len(parts) >= 2:
            qword_total = int(_fields(parts[1:])["matches"])
        elif kind == "IMAGE_OFFSET_SCAN_SUMMARY" and len(parts) >= 2:
            image_offset_total = int(_fields(parts[1:])["matches"])
        elif kind == "ADDRESS_MATERIALIZATION_SUMMARY" and len(parts) >= 2:
            address_summary = _fields(parts[1:])
        elif kind == "SUMMARY":
            summary = _fields(parts[1:])

    if summary is None:
        raise ValueError("latest pointer scan has no parseable SUMMARY")
    if address_summary is None:
        raise ValueError("latest pointer scan has no address-materialization summary")
    if summary.get("main_sha256") != EXPECTED_MAIN_SHA256:
        raise ValueError(f"main SHA-256 mismatch: {summary.get('main_sha256')!r}")
    if summary.get("image_base") != f"0x{EXPECTED_IMAGE_BASE:x}":
        raise ValueError(f"main image base mismatch: {summary.get('image_base')!r}")
    if summary.get("sourceHashUnchanged") != "true" or summary.get("readOnly") != "true":
        raise ValueError("read-only source integrity could not be verified")
    if summary.get("candidate_output_truncated") != "false":
        raise ValueError("pointer candidate output was truncated")
    if set(targets) != set(EXPECTED_TARGETS):
        raise ValueError("pointer scan is missing one or more expected target summaries")
    if any("absolute_qword_matches" not in row or "image_offset_dword_matches" not in row
           or "incoming_references" not in row for row in targets.values()):
        raise ValueError("pointer scan is missing per-target reference or match counts")
    summed_qwords = sum(row["absolute_qword_matches"] for row in targets.values())
    summed_offsets = sum(row["image_offset_dword_matches"] for row in targets.values())
    if qword_total != summed_qwords or image_offset_total != summed_offsets:
        raise ValueError("pointer scan total does not match per-target counts")

    return {
        "schema": "lgpe-save-worker-pointer-scan-v1",
        "status": "STATIC_POINTER_SCAN_ONLY",
        "game": "Pokemon Let's Go Pikachu 1.0.2",
        "main": {
            "sha256": EXPECTED_MAIN_SHA256,
            "image_base": f"0x{EXPECTED_IMAGE_BASE:x}",
            "source_path": "../1.0.2/2b7730a9e56498bbafac2002d4908c6b_NCA/0/main",
        },
        "trace": {
            "tool": "Ghidra 12.2",
            "read_only": True,
            "source_hash_unchanged": True,
            "script": "scripts/ghidra/ScanSaveWorkerPointers.java",
            "script_sha256": trace_script_sha256,
            "wrapper": "scripts/ghidra/Run-ScanSaveWorkerPointers.ps1",
            "wrapper_sha256": trace_wrapper_sha256,
            "log": "logs/ghidra-save-worker-pointers-v1-script.log",
            "log_sha256": trace_log_sha256,
        },
        "scan": {
            "initialized_blocks": int(summary["initialized_blocks"]),
            "bytes_scanned": int(summary["bytes_scanned"]),
            "candidate_lines": int(summary["candidate_lines"]),
            "candidate_output_truncated": False,
            "absolute_qword_matches": qword_total,
            "image_offset_dword_matches": image_offset_total,
        },
        "address_materialization": {
            "executable_blocks": int(address_summary["executable_blocks"]),
            "instruction_count": int(address_summary["instruction_count"]),
            "adr_adrp_count": int(address_summary["adr_adrp"]),
            "page_candidates": int(address_summary["page_candidates"]),
            "page_plus_offset_candidates": int(
                address_summary["page_plus_offset_candidates"]
            ),
            "exact_worker_candidates": int(address_summary["exact_worker_candidates"]),
            "candidate_lines": int(address_summary["candidate_lines"]),
            "candidate_output_truncated": (
                address_summary["candidate_output_truncated"] == "true"
            ),
        },
        "targets": targets,
        "unassigned_candidates": candidates,
        "address_page_candidates": address_page_candidates,
        "page_plus_offset_candidates": page_plus_offset_candidates,
        "interpretation": {
            "worker_registration": "UNKNOWN",
            "player_save_owner": "UNKNOWN",
            "runtime_execution": "UNVERIFIED",
            "limitations": [
                "The scan compares raw little-endian qwords and non-executable image-offset dwords; it does not normalize relocations or infer indirect-call semantics.",
                "The code scan matches ADR/ADRP rendered operands to the worker's 4 KiB page and checks only nearby same-register ADD immediates for offset 0xd70.",
                "Page and page-plus-offset instruction candidates are static address materialization evidence, not proof of worker registration or execution.",
                "Image-offset matches in .rela.plt and .hash are retained as candidates and are not assigned as function pointers.",
                "No raw absolute qword match does not exclude split ADRP/ADD materialization, relative encodings, or indirect dispatch through a different table.",
            ],
        },
    }
