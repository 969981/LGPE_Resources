"""Bounded AMX header inspection; bytecode remains UNKNOWN until body decoding is verified."""
from __future__ import annotations

import hashlib
import csv
import json
import struct
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

from .core import NCA, PROJECT, VERSION, ensure_inside, source_dirs


PAWN_REFERENCE_COMMIT = "db97293fa949d7627272a1c8d7a9470818bdbe91"
PAWN_REFERENCE_URL = "https://github.com/compuphase/pawn.git"
PAWN_REFERENCE_LICENSE = "Apache-2.0"
HEADER = struct.Struct("<IHBBhh12i")
HEADER_FIELDS = (
    "size", "magic", "file_version", "amx_version", "flags", "defsize",
    "cod", "dat", "hea", "stp", "cip", "publics", "natives", "libraries",
    "pubvars", "tags", "nametable", "overlays",
)
MAGIC_CELL_BYTES = {0xF1E2: 2, 0xF1E0: 4, 0xF1E1: 8}
STANDARD_PAWN_FUNCSTUB_BYTES = 8  # uint32 address + uint32 nameofs in the pinned amx.h
TABLE_OFFSETS = ("publics", "natives", "libraries", "pubvars", "tags", "nametable", "overlays")


def parse_amx_header(data: bytes) -> dict:
    """Parse the 60-byte AMX_HEADER envelope without decoding or executing its body."""
    if len(data) < HEADER.size:
        raise ValueError(f"truncated AMX header: {len(data)} bytes, need {HEADER.size}")
    values = HEADER.unpack_from(data)
    fields = dict(zip(HEADER_FIELDS, values))
    magic = fields["magic"]
    table_offsets = [fields[name] for name in TABLE_OFFSETS]
    table_offsets_monotonic = all(a <= b for a, b in zip(table_offsets, table_offsets[1:]))
    table_offsets_in_file = all(HEADER.size <= offset <= len(data) for offset in table_offsets)
    known_magic = magic in MAGIC_CELL_BYTES
    size_matches = fields["size"] == len(data)
    code_offset_in_file = HEADER.size <= fields["cod"] <= len(data)
    header_candidate = bool(
        known_magic and size_matches and table_offsets_monotonic
        and table_offsets_in_file and code_offset_in_file
    )

    is_pawn64 = magic == 0xF1E1
    name_table_offset = fields["nametable"]
    name_table_length = None
    if 0 <= name_table_offset <= len(data) - 2:
        name_table_length = struct.unpack_from("<H", data, name_table_offset)[0]
    defsize = fields["defsize"]
    defsize_supported = defsize == 0x1C or (
        defsize == 0x0C and name_table_length is not None and name_table_length < 0x40
    )
    runtime_checks = {
        "magic_is_0xf1e1": magic == 0xF1E1,
        "file_version_at_most_10": fields["file_version"] <= 10,
        "amx_version_at_least_6": fields["amx_version"] >= 6,
        "definition_record_size_supported": defsize_supported,
        "positive_stack_top": fields["stp"] > 0,
    }
    lgpe_runtime_header_check = {
        "status": "STATIC_PASS" if all(runtime_checks.values()) else "STATIC_REJECT",
        "source_main_sha256": "1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8",
        "parser_function": "0x710066fb20",
        "name_table_length": name_table_length,
        "definition_record_size": defsize,
        "flag_0x04_set": bool(fields["flags"] & 0x04),
        "checks": runtime_checks,
    }
    defsize_matches_reference = (
        fields["defsize"] == STANDARD_PAWN_FUNCSTUB_BYTES if is_pawn64 else None
    )
    hea_matches_size = fields["hea"] == fields["size"]
    observations = []
    if is_pawn64:
        observations.append("magic_matches_pinned_Pawn_AMX_MAGIC_64")
        observations.append("header_field_order_and_widths_match_pinned_AMX_HEADER")
        if fields["defsize"] != STANDARD_PAWN_FUNCSTUB_BYTES:
            observations.append("definition_record_size_differs_from_pinned_Pawn_AMX_FUNCSTUB_8")
        if not hea_matches_size:
            observations.append("hea_differs_from_size_pinned_Pawn_amx_Init_assertion")
    observations.append(
        "static_LGPE_1.0.2_AMX_header_gate_passed"
        if lgpe_runtime_header_check["status"] == "STATIC_PASS"
        else "static_LGPE_1.0.2_AMX_header_gate_rejected"
    )
    if not table_offsets_monotonic:
        observations.append("table_offsets_not_monotonic")
    if not table_offsets_in_file:
        observations.append("table_offset_outside_physical_file")
    if not size_matches:
        observations.append("size_field_differs_from_physical_file_length")
    if not code_offset_in_file:
        observations.append("code_offset_outside_physical_file")
    observations.append("bytecode_body_not_decoded_or_executed")

    return {
        "header_status": "AMX_HEADER_CANDIDATE" if header_candidate else "UNKNOWN_HEADER",
        "body_status": "UNKNOWN",
        "header_size": HEADER.size,
        "physical_file_bytes": len(data),
        "header_hex": data[:HEADER.size].hex(),
        "fields": fields,
        "known_magic_cell_bytes": MAGIC_CELL_BYTES.get(magic),
        "size_matches_physical_file": size_matches,
        "table_offsets_monotonic": table_offsets_monotonic,
        "table_offsets_within_physical_file": table_offsets_in_file,
        "code_offset_within_physical_file": code_offset_in_file,
        "lgpe_runtime_header_check": lgpe_runtime_header_check,
        "pinned_pawn64_comparison": {
            "repository": PAWN_REFERENCE_URL,
            "commit": PAWN_REFERENCE_COMMIT,
            "license": PAWN_REFERENCE_LICENSE,
            "defsize_expected_by_amx_funcstub": STANDARD_PAWN_FUNCSTUB_BYTES if is_pawn64 else None,
            "defsize_matches_reference": defsize_matches_reference,
            "hea_equals_size_reference_invariant": hea_matches_size,
            "compatibility": (
                "MISMATCH" if is_pawn64 and (defsize_matches_reference is False or not hea_matches_size)
                else "REFERENCE_HEADER_CHECKS_MATCH" if is_pawn64
                else "NOT_ESTABLISHED"
            ),
        },
        "observations": observations,
    }


def _read_jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            if isinstance(row, dict) and row.get("source"):
                rows.append(row)
    return rows


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".partial")
    temporary.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    temporary.replace(path)


def _manifest_identity(row: dict) -> str:
    """Use archive index identity so duplicate internal paths remain distinct."""
    if row.get("source_kind") == "gfpak_member":
        return "gfpak_member:" + ":".join(str(row.get(key, "")) for key in (
            "container_source", "container_index", "internal_path"
        )).casefold()
    return str(row.get("source", "")).casefold()


def _script_amx_archive_inputs(romfs: Path, project: Path) -> list[dict]:
    """Return receipt-bound extracted members from the one xref-confirmed AMX archive."""
    manifest = project / "manifests" / "archives.jsonl"
    if not manifest.is_file():
        return []
    archive_row = None
    with manifest.open("r", encoding="utf-8") as stream:
        for line in stream:
            if not line.strip():
                continue
            candidate = json.loads(line)
            if candidate.get("source") == "bin/archive/script_amx.gfpak":
                archive_row = candidate
                break
    if not archive_row or archive_row.get("status") != "DECODED":
        return []

    container_source = str(archive_row["source"])
    container_rel = PurePosixPath(container_source)
    if container_rel.is_absolute() or not container_rel.parts or ".." in container_rel.parts:
        raise ValueError(f"unsafe AMX archive source path: {container_source}")
    container_path = ensure_inside(romfs.joinpath(*container_rel.parts), romfs)
    container_error = None
    try:
        container_data = container_path.read_bytes()
        container_hash = hashlib.sha256(container_data).hexdigest()
        if len(container_data) != int(archive_row["source_size"]):
            container_error = "container size differs from archives.jsonl receipt"
        elif container_hash != str(archive_row["source_sha256"]):
            container_error = "container SHA-256 differs from archives.jsonl receipt"
    except OSError as exc:
        container_hash = ""
        container_error = f"{type(exc).__name__}: {exc}"

    decoded_root = ensure_inside(project / "decoded" / VERSION / "romfs", project / "decoded")
    contents_rel = container_rel.with_name(container_rel.name + ".contents")
    results = []
    for member in archive_row.get("members", []):
        internal_path = str(member.get("internal_path", "")).replace("\\", "/")
        internal_rel = PurePosixPath(internal_path)
        error = container_error
        if (not internal_rel.parts or internal_rel.is_absolute() or ".." in internal_rel.parts
                or ":" in internal_rel.parts[0]):
            error = error or f"unsafe archive member path: {internal_path}"
        source = contents_rel.joinpath(*internal_rel.parts).as_posix()
        member_file = decoded_root.joinpath(*PurePosixPath(source).parts)
        try:
            member_file = ensure_inside(member_file, decoded_root)
        except ValueError as exc:
            error = error or str(exc)
        results.append({
            "source_kind": "gfpak_member",
            "source": source,
            "path": member_file,
            "container_source": container_source,
            "container_sha256": container_hash,
            "container_index": member.get("index"),
            "internal_path": internal_path,
            "expected_member_bytes": member.get("size"),
            "expected_member_sha256": member.get("sha256"),
            "container_error": error,
        })
    return results


def catalog_amx_headers(root: Path, project: Path = PROJECT, limit: int = 0) -> dict:
    """Catalog real RomFS AMX files, preserving UNKNOWN body status and source hashes."""
    if limit < 0:
        raise ValueError("limit must be zero or positive")
    romfs = source_dirs(root)["romfs"]
    if not romfs.is_dir():
        raise FileNotFoundError(f"RomFS missing: {romfs}")
    scan_manifest = project / "manifests" / "files.csv"
    inputs = []
    if scan_manifest.is_file():
        with scan_manifest.open("r", encoding="utf-8-sig", newline="") as stream:
            for row in csv.DictReader(stream):
                if row.get("partition") != "romfs" or row.get("suffix", "").casefold() != ".amx":
                    continue
                relative = PurePosixPath(str(row.get("relative_path", "")))
                if relative.is_absolute() or not relative.parts or ".." in relative.parts:
                    continue
                candidate = romfs.joinpath(*relative.parts)
                if candidate.is_symlink():
                    continue
                source = ensure_inside(candidate, romfs)
                if source.is_file():
                    inputs.append(source)
        discovery = "manifests/files.csv"
    else:
        # The observed LGPE 1.0.2 AMX directory is small; require a full scan
        # before searching elsewhere so this command never recursively probes
        # the entire 27k-file mapped drive just to locate scripts.
        observed_dir = romfs / "bin" / "battle" / "ai_script"
        inputs = [path for path in observed_dir.glob("*")
                  if path.is_file() and not path.is_symlink() and path.suffix.casefold() == ".amx"]
        discovery = "observed_directory_fallback"
    inputs = sorted(set(inputs), key=lambda path: path.relative_to(romfs).as_posix().casefold())
    items = [{"source_kind": "romfs_file", "source": source.relative_to(romfs).as_posix(), "path": source}
             for source in inputs]
    archive_items = _script_amx_archive_inputs(romfs, project)
    items.extend(archive_items)
    if limit:
        items = items[:limit]

    rows = []
    for item in items:
        source = item["path"]
        relative = item["source"]
        source_fields = {key: item[key] for key in (
            "source_kind", "container_source", "container_sha256", "container_index", "internal_path"
        ) if key in item}
        if item.get("container_error"):
            rows.append({
                "source_version": VERSION,
                "nca_folder": NCA,
                "partition": "romfs",
                "source": relative,
                **source_fields,
                "expected_member_bytes": item.get("expected_member_bytes"),
                "expected_member_sha256": item.get("expected_member_sha256"),
                "status": "FAILED",
                "decoder_status": "CONTAINER_RECEIPT_INVALID",
                "error": item["container_error"],
                "analysis_tool": "lgpe amx-catalog / bounded AMX_HEADER parser",
                "analysis_timestamp_utc": datetime.now(timezone.utc).isoformat(),
            })
            continue
        try:
            data = source.read_bytes()
            digest = hashlib.sha256(data).hexdigest()
            if item["source_kind"] == "gfpak_member":
                expected_bytes = int(item["expected_member_bytes"])
                expected_hash = str(item["expected_member_sha256"])
                if len(data) != expected_bytes or digest != expected_hash:
                    rows.append({
                        "source_version": VERSION,
                        "nca_folder": NCA,
                        "partition": "romfs",
                        "source": relative,
                        **source_fields,
                        "source_bytes": len(data),
                        "source_sha256": digest,
                        "expected_member_bytes": expected_bytes,
                        "expected_member_sha256": expected_hash,
                        "status": "FAILED",
                        "decoder_status": "MEMBER_RECEIPT_MISMATCH",
                        "error": "extracted member differs from archives.jsonl size/SHA-256 receipt",
                        "analysis_tool": "lgpe amx-catalog / bounded AMX_HEADER parser",
                        "analysis_timestamp_utc": datetime.now(timezone.utc).isoformat(),
                    })
                    continue
            parsed = parse_amx_header(data)
            rows.append({
                "source_version": VERSION,
                "nca_folder": NCA,
                "partition": "romfs",
                "source": relative,
                **source_fields,
                "discovery": "manifests/archives.jsonl" if item["source_kind"] == "gfpak_member" else discovery,
                "source_bytes": len(data),
                "source_sha256": digest,
                **({
                    "expected_member_bytes": item["expected_member_bytes"],
                    "expected_member_sha256": item["expected_member_sha256"],
                } if item["source_kind"] == "gfpak_member" else {}),
                "status": "UNKNOWN",
                "decoder_status": "UNKNOWN_BODY",
                "analysis_tool": "lgpe amx-catalog / bounded AMX_HEADER parser",
                "analysis_timestamp_utc": datetime.now(timezone.utc).isoformat(),
                **parsed,
            })
        except OSError as exc:
            rows.append({
                "source_version": VERSION,
                "nca_folder": NCA,
                "partition": "romfs",
                "source": relative,
                **source_fields,
                "discovery": discovery,
                "status": "FAILED",
                "decoder_status": "READ_FAILED",
                "error": f"{type(exc).__name__}: {exc}",
            })
        except ValueError as exc:
            digest = hashlib.sha256(data).hexdigest()
            rows.append({
                "source_version": VERSION,
                "nca_folder": NCA,
                "partition": "romfs",
                "source": relative,
                **source_fields,
                "source_bytes": len(data),
                "source_sha256": digest,
                "status": "UNKNOWN",
                "decoder_status": "TRUNCATED_OR_INVALID_HEADER",
                "header_status": "UNKNOWN_HEADER",
                "body_status": "UNKNOWN",
                "header_hex": data[:HEADER.size].hex(),
                "error": str(exc),
                "analysis_tool": "lgpe amx-catalog / bounded AMX_HEADER parser",
                "analysis_timestamp_utc": datetime.now(timezone.utc).isoformat(),
            })

    manifest = project / "manifests" / "amx_headers.jsonl"
    existing = _read_jsonl(manifest)
    merged = {_manifest_identity(row): row for row in existing}
    for row in rows:
        identity = _manifest_identity(row)
        previous = merged.get(identity)
        if (
            previous
            and previous.get("source_sha256") == row.get("source_sha256")
            and previous.get("decoder_status") in {
                "COMPACT_CELLS_AND_EXACT_BUILD_OPCODE_STREAM_VALIDATED",
                "DECODE_OR_EXACT_GAME_VALIDATION_FAILED",
            }
        ):
            for key in (
                "status", "decoder_status", "body_status", "decoded_cell_count",
                "instruction_count", "output", "output_sha256", "output_bytes",
                "error", "analysis_tool", "analysis_tool_version",
            ):
                if key in previous:
                    row[key] = previous[key]
        merged[identity] = row
    output_rows = sorted(
        merged.values(),
        key=lambda row: (
            str(row.get("source", "")).casefold(),
            str(row.get("container_index", "")),
        ),
    )
    _write_jsonl(manifest, output_rows)
    return {
        "scanned": len(items),
        "loose_scanned": sum(item["source_kind"] == "romfs_file" for item in items),
        "archive_member_scanned": sum(item["source_kind"] == "gfpak_member" for item in items),
        "header_candidates": sum(row.get("header_status") == "AMX_HEADER_CANDIDATE" for row in rows),
        "static_header_pass": sum(
            row.get("lgpe_runtime_header_check", {}).get("status") == "STATIC_PASS" for row in rows
        ),
        "static_header_reject": sum(
            row.get("lgpe_runtime_header_check", {}).get("status") == "STATIC_REJECT" for row in rows
        ),
        "decoded": 0,
        "unknown": sum(row.get("status") == "UNKNOWN" for row in rows),
        "failed": sum(row.get("status") == "FAILED" for row in rows),
        "manifest_rows": len(output_rows),
        "manifest": str(manifest),
        "discovery": discovery,
        "body_status": "UNKNOWN_BODY_DECODER_NOT_IMPLEMENTED",
    }
