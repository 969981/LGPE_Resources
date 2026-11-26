"""Hash-checked content cross-references for localized sort_string tables.

This module compares indexed values with already decoded, hash-verified LGPE
message lines. It does not write or register decoder outputs; exact-build
structure decodes and canonical per-source status are recorded separately.
"""
from __future__ import annotations

import csv
import hashlib
import json
import unicodedata
from pathlib import Path, PurePosixPath

from .core import NCA, PROJECT, VERSION, ensure_inside, sha256, source_dirs

SORT_ROOT = "bin/app/sort_string"
MESSAGE_ROOT = "bin/message"
FAMILY_TO_MESSAGE = {
    "item": ("itemname", "ITEMNAME"),
    "monsname": ("monsname", "MONSNAME"),
    "waza": ("wazaname", "WAZANAME"),
}
RESOURCE_REQUESTS = {
    "item": "main+0xb31400",
    "monsname": "main+0xb315e0",
    "waza": "main+0xb318c0",
}
MAIN_SHA256 = "1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8"
RESOURCE_LOADER = "main+0x374530"
SORT_TABLE_READER = "main+0x374a90"


def _read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _safe_output(project: Path, record: dict) -> Path:
    relative = Path(str(record.get("output", "")).replace("\\", "/"))
    if relative.is_absolute() or ".." in relative.parts or not relative.parts:
        raise ValueError(f"unsafe decoded output path for {record.get('source')}: {record.get('output')}")
    return ensure_inside(project / relative, project / "decoded")


def _verified_message(
    project: Path, root: Path, source_rel: str, rows_by_source: dict[str, list[dict]],
) -> tuple[dict, Path, Path, dict]:
    matches = rows_by_source.get(source_rel.casefold(), [])
    decoded = [row for row in matches if row.get("status") == "DECODED"]
    if len(decoded) != 1:
        raise ValueError(
            f"expected one DECODED companion message record for {source_rel}; found {len(decoded)}"
        )
    record = decoded[0]
    romfs = source_dirs(root)["romfs"]
    source = ensure_inside(romfs.joinpath(*PurePosixPath(source_rel).parts), romfs)
    output = _safe_output(project, record)
    actual_source_hash = sha256(source)
    actual_output_hash = sha256(output)
    if actual_source_hash != record.get("source_sha256"):
        raise ValueError(f"companion message source hash differs from manifest: {source_rel}")
    if actual_output_hash != record.get("output_sha256"):
        raise ValueError(f"companion message output hash differs from manifest: {record.get('output')}")
    payload = json.loads(output.read_text(encoding="utf-8"))
    if payload.get("schema") != "lgpe-gamedata-v1" or payload.get("format") != "LGPE-message":
        raise ValueError(f"companion output is not a decoded LGPE message: {record.get('output')}")
    lines = payload.get("lines")
    if not isinstance(lines, list) or len(lines) != record.get("count"):
        raise ValueError(f"companion message line count differs from manifest: {source_rel}")
    return record, source, output, payload


def _candidate_values(raw: bytes) -> tuple[list[int], list[int]]:
    if len(raw) % 2:
        raise ValueError(f"candidate sort_table has odd byte length: {len(raw)}")
    little = [int.from_bytes(raw[i:i + 2], "little") for i in range(0, len(raw), 2)]
    big = [int.from_bytes(raw[i:i + 2], "big") for i in range(0, len(raw), 2)]
    return little, big


def _line_index_map(lines: list[dict], source: str) -> dict[int, dict]:
    by_index: dict[int, dict] = {}
    for position, line in enumerate(lines):
        if not isinstance(line, dict) or not isinstance(line.get("index"), int):
            raise ValueError(f"message line {position} has no integer index: {source}")
        if line["index"] in by_index:
            raise ValueError(f"duplicate message line index {line['index']}: {source}")
        if not isinstance(line.get("id"), str) or not isinstance(line.get("text"), str):
            raise ValueError(f"message line {position} lacks an id or text: {source}")
        by_index[line["index"]] = line
    return by_index


def _is_one_based_permutation(values: list[int]) -> bool:
    return bool(values) and len(values) == len(set(values)) and set(values) == set(range(1, len(values) + 1))


def cross_reference_sort_table(
    raw: bytes, message_payload: dict, *, source: str, message_source: str,
    message_output: str,
) -> dict:
    """Compare a byte-level u16le candidate with companion message line IDs."""
    little, big = _candidate_values(raw)
    lines = message_payload.get("lines")
    if not isinstance(lines, list):
        raise ValueError(f"companion message has no lines array: {message_source}")
    by_index = _line_index_map(lines, message_source)
    family = PurePosixPath(source).name.split("_sort_table.dat", 1)[0]
    mapping = FAMILY_TO_MESSAGE.get(family)
    if mapping is None:
        raise ValueError(f"unrecognized localized sort_table family: {source}")
    _, expected_prefix = mapping
    if not little or not _is_one_based_permutation(little):
        raise ValueError("little-endian candidate values are not a nonempty 1-based permutation")
    if set(by_index) != set(range(len(little) + 1)):
        raise ValueError(
            f"companion message indexes do not contain 0..{len(little)}: "
            f"{message_source} has {len(by_index)} indexed lines"
        )

    resolved = []
    text_keys = []
    prefix_ok = True
    for ordinal, value in enumerate(little):
        line = by_index.get(value)
        if line is None:
            raise ValueError(f"candidate value {value} does not resolve to a message line: {message_source}")
        if not line["id"].startswith(expected_prefix + "_"):
            prefix_ok = False
        text_keys.append(unicodedata.normalize("NFKD", line["text"]).casefold())
        if ordinal < 12:
            resolved.append({
                "table_position": ordinal,
                "source_offset": ordinal * 2,
                "raw_hex": raw[ordinal * 2:ordinal * 2 + 2].hex(),
                "candidate_value_u16le": value,
                "message_line_index": line["index"],
                "message_id": line["id"],
                "text": line["text"],
            })

    adjacent = sum(left <= right for left, right in zip(text_keys, text_keys[1:]))
    return {
        "schema": "lgpe-sort-string-message-crossref-v1",
        "source_version": "Pokemon Let's Go Pikachu " + VERSION,
        "nca_folder": NCA,
        "source": source,
        "format_status": "DECODED",
        "reason": (
            "the exact-build reader establishes little-endian u16 elements and all values "
            "cross-reference decoded localized message lines; runtime execution is not established"
        ),
        "candidate": {
            "representation": "u16le-index-table",
            "entry_count": len(little),
            "little_endian_one_based_permutation": _is_one_based_permutation(little),
            "big_endian_one_based_permutation": _is_one_based_permutation(big),
            "value_min": min(little),
            "value_max": max(little),
            "resolved_message_line_count": len(little),
            "all_values_resolved": True,
            "message_id_prefix_matches_family": prefix_ok,
            "adjacent_nfkd_casefold_ordered_pairs": adjacent,
            "adjacent_pairs_total": max(0, len(little) - 1),
            "first_12_resolved_rows": resolved,
        },
        "message": {
            "source": message_source,
            "output": message_output,
            "line_count": len(lines),
            "line_zero": by_index[0]["text"],
        },
        "code_evidence": {
            "main_sha256": MAIN_SHA256,
            "main_image_base": "0x7100000000",
            "Ghidra": "12.2 PUBLIC",
            "static_resource_request_function": RESOURCE_REQUESTS[family],
            "static_request_sequence": "initial_index.dat, sort_table.dat, initial_to_sort.dat",
            "shared_resource_loader": RESOURCE_LOADER,
            "direct_element_read": SORT_TABLE_READER,
            "element_width_bytes": 2,
            "endianness": "little",
            "runtime_execution": "NOT_ESTABLISHED",
        },
    }


def build_sort_string_message_crossrefs(
    project: Path = PROJECT, root: Path = PROJECT.parent,
) -> dict:
    """Build a read-only content cross-reference report for all 27 sort tables."""
    project = Path(project).expanduser().resolve()
    root = Path(root).expanduser().resolve()
    romfs = source_dirs(root)["romfs"]
    sort_dir = ensure_inside(romfs / SORT_ROOT, romfs)
    profile_path = project / "manifests/sort_string_candidates.jsonl"
    file_catalog = project / "manifests/files.csv"
    gamedata_manifest = project / "manifests/gamedata.jsonl"
    for required in (profile_path, file_catalog, gamedata_manifest):
        if not required.is_file():
            raise FileNotFoundError(required)

    profile_rows = _read_jsonl(profile_path)
    profile_by_source = {str(row.get("source", "")).casefold(): row for row in profile_rows}
    if len(profile_by_source) != len(profile_rows):
        raise ValueError("duplicate source paths in sort_string candidate profile")
    with file_catalog.open("r", encoding="utf-8-sig", newline="") as stream:
        scan_by_source = {
            row["relative_path"].casefold(): row
            for row in csv.DictReader(stream)
            if row.get("partition") == "romfs"
        }
    if not scan_by_source:
        raise ValueError("files.csv has no ROMFS rows")
    gamedata_rows = _read_jsonl(gamedata_manifest)
    rows_by_source: dict[str, list[dict]] = {}
    for row in gamedata_rows:
        rows_by_source.setdefault(str(row.get("source", "")).casefold(), []).append(row)

    files = []
    source_paths = []
    for locale_dir in sorted(sort_dir.iterdir(), key=lambda item: item.name.casefold()):
        if locale_dir.is_symlink() or not locale_dir.is_dir():
            continue
        for source_path in sorted(locale_dir.iterdir(), key=lambda item: item.name.casefold()):
            if source_path.is_symlink() or not source_path.is_file() or not source_path.name.endswith(".dat"):
                continue
            relative = source_path.relative_to(romfs).as_posix()
            source_paths.append(relative)
            profile = profile_by_source.get(relative.casefold())
            scan = scan_by_source.get(relative.casefold())
            if profile is None or scan is None:
                raise ValueError(f"sort_string source missing from profile or scan catalog: {relative}")
            raw = source_path.read_bytes()
            source_hash = hashlib.sha256(raw).hexdigest()
            if source_hash != profile.get("sha256") or len(raw) != int(profile.get("bytes", -1)):
                raise ValueError(f"source differs from candidate profile: {relative}")
            if int(scan.get("bytes", -1)) != len(raw):
                raise ValueError(f"source size differs from scan catalog: {relative}")
            if scan.get("sha256") and scan["sha256"] != source_hash:
                raise ValueError(f"source hash differs from full scan catalog: {relative}")
            if not source_path.name.endswith("_sort_table.dat"):
                continue

            locale = source_path.parent.name
            family = source_path.name.removesuffix("_sort_table.dat")
            if family not in FAMILY_TO_MESSAGE:
                raise ValueError(f"unknown sort_table family: {relative}")
            message_stem, _prefix = FAMILY_TO_MESSAGE[family]
            message_rel = f"{MESSAGE_ROOT}/{locale}/common/{message_stem}.dat"
            message_record, message_source, message_output, payload = _verified_message(
                project, root, message_rel, rows_by_source,
            )
            result = cross_reference_sort_table(
                raw,
                payload,
                source=relative,
                message_source=message_rel,
                message_output=message_record["output"].replace("\\", "/"),
            )
            result["source_bytes"] = len(raw)
            result["source_sha256"] = source_hash
            result["message_source_sha256"] = sha256(message_source)
            result["message_output_sha256"] = sha256(message_output)
            result["message_tool_versions"] = message_record.get("tool_versions", {})
            files.append(result)

    expected_sources = sorted(source_paths, key=str.casefold)
    profile_sources = sorted(
        (str(row.get("source", "")) for row in profile_rows), key=str.casefold,
    )
    if expected_sources != profile_sources:
        raise ValueError("actual localized sort_string source paths differ from candidate profile")
    if len(source_paths) != 81 or len(files) != 27:
        raise ValueError(f"expected 81 sort_string files / 27 sort tables; found {len(source_paths)} / {len(files)}")

    source_statuses = {
        str(row.get("source", "")).casefold(): row.get("status", "UNKNOWN")
        for row in gamedata_rows
        if str(row.get("source", "")).casefold() in {path.casefold() for path in source_paths}
    }
    status_counts = {
        status: sum(source_statuses.get(path.casefold(), "UNKNOWN") == status for path in source_paths)
        for status in ("DECODED", "FAILED", "UNKNOWN", "PENDING", "UNSUPPORTED")
    }
    summary = {
        "source_version": "Pokemon Let's Go Pikachu " + VERSION,
        "nca_folder": NCA,
        "source_files_scanned": len(source_paths),
        "sort_table_candidates_cross_referenced": len(files),
        "sort_tables_with_one_based_permutation": sum(
            row["candidate"]["little_endian_one_based_permutation"] for row in files
        ),
        "sort_tables_with_all_message_lines_resolved": sum(
            row["candidate"]["all_values_resolved"] for row in files
        ),
        "sort_tables_with_message_id_prefix_match": sum(
            row["candidate"]["message_id_prefix_matches_family"] for row in files
        ),
        "sort_tables_also_big_endian_permutations": sum(
            row["candidate"]["big_endian_one_based_permutation"] for row in files
        ),
        "sort_tables_full_unicode_nfkd_casefold_order": sum(
            row["candidate"]["adjacent_nfkd_casefold_ordered_pairs"]
            == row["candidate"]["adjacent_pairs_total"] for row in files
        ),
        **{key.lower(): value for key, value in status_counts.items()},
        "interpretation": (
            "this content cross-reference does not write outputs or change status; counts are "
            "read from the canonical gamedata manifest. Exact-build readers are documented "
            "separately, and runtime execution is not established"
        ),
    }
    return {"summary": summary, "files": files}


def write_sort_string_message_crossrefs(
    project: Path = PROJECT, root: Path = PROJECT.parent,
    manifest: Path | None = None,
) -> dict:
    report = build_sort_string_message_crossrefs(project, root)
    project = Path(project).expanduser().resolve()
    destination = manifest or project / "manifests/sort_string_message_crossrefs.jsonl"
    destination = ensure_inside(Path(destination), project / "manifests")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in report["files"]),
        encoding="utf-8",
    )
    summary_path = destination.with_suffix(".summary.json")
    summary_path.write_text(
        json.dumps(report["summary"], ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return {"summary": report["summary"], "manifest": destination, "summary_file": summary_path}
