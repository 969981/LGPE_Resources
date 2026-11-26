"""Bounded LGPE 1.0.2 AMX compact-cell decode and exact-build validation."""
from __future__ import annotations

import hashlib
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

from .amx_catalog import _manifest_identity, _read_jsonl, _write_jsonl, catalog_amx_headers
from .batch import merge_failures
from .core import NCA, PROJECT, VERSION, add_receipts, ensure_inside, remove_receipts, sha256, source_dirs


GAME_MAIN_SHA256 = "1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8"
GAME_PARSER_FUNCTION = "0x710066fb20"
GAME_VALIDATOR_FUNCTION = "0x710066ff20"
DECODER_METHOD = "lgpe_research.amx_decode/reverse_compact_cells"
DECODER_VERSION = "1.0.0"
MANIFEST = "amx_headers.jsonl"


def decode_compact_cells(blob: bytes, cell_bytes: int = 8, expected_count: int | None = None) -> list[int]:
    """Decode signed, big-endian 7-bit groups into unsigned fixed-width cells.

    LGPE 1.0.2 expands this stream backwards in place. Reading a cell's groups
    forward here yields the same value sequence while keeping the raw source
    immutable. Bit 7 continues a group; bit 6 of the first group is the sign.
    """
    if cell_bytes not in (2, 4, 8):
        raise ValueError(f"unsupported compact cell width: {cell_bytes}")
    mask = (1 << (cell_bytes * 8)) - 1
    max_groups = math.ceil(cell_bytes * 8 / 7)
    cells: list[int] = []
    cursor = 0
    while cursor < len(blob):
        first = blob[cursor]
        cursor += 1
        negative = bool(first & 0x40)
        value = first & 0x7F
        groups = 1
        while first & 0x80:
            if cursor >= len(blob):
                raise ValueError("truncated compact cell continuation")
            first = blob[cursor]
            cursor += 1
            value = (value << 7) | (first & 0x7F)
            groups += 1
            if groups > max_groups:
                raise ValueError(f"compact cell exceeds cell width ({cell_bytes} bytes)")
        if negative:
            value |= -1 << (groups * 7)
        cells.append(value & mask)
        if expected_count is not None and len(cells) > expected_count:
            raise ValueError("compact stream decodes to more cells than the AMX header permits")
    if expected_count is not None and len(cells) != expected_count:
        raise ValueError(
            f"compact cell count mismatch: decoded {len(cells)}, expected {expected_count}"
        )
    return cells


def _signed_cell(value: int) -> int:
    return value - (1 << 64) if value & (1 << 63) else value


def _verify_exact_game_main(root: Path) -> str:
    main = source_dirs(root)["exefs"] / "main"
    if not main.is_file():
        raise FileNotFoundError(f"exact LGPE 1.0.2 AMX validator requires ExeFS main: {main}")
    digest = sha256(main)
    if digest != GAME_MAIN_SHA256:
        raise ValueError(
            "AMX opcode rules are pinned to LGPE 1.0.2 main SHA-256 "
            f"{GAME_MAIN_SHA256}; local main has {digest}"
        )
    return digest


def validate_game_code(cells: list[int], fields: dict) -> dict:
    """Mirror the bounded opcode/operand checks in LGPE 1.0.2 main."""
    cod = int(fields["cod"])
    dat = int(fields["dat"])
    hea = int(fields["hea"])
    stp = int(fields["stp"])
    file_version = int(fields["file_version"])
    code_bytes = dat - cod
    data_bytes = hea - dat
    stack_bytes = stp - hea
    if min(code_bytes, data_bytes, stack_bytes) < 0:
        return _reject("invalid code/data/heap/stack boundaries", "0x04", 0, [])

    global_data_ops = {0x01, 0x02, 0x05, 0x06, 0x0F, 0x10, 0x13, 0x14, 0x6D, 0x72}
    stack_ops = {0x03, 0x04, 0x07, 0x08, 0x11, 0x12, 0x15, 0x16, 0x6E, 0x73}
    branch_ops = {0x31, 0x33, *range(0x35, 0x41), 0x81}
    two_cell_ops = {
        0x0A, 0x0B, 0x0C, 0x0D, 0x0E, 0x18, 0x1A, 0x1C, 0x1D, 0x1E, 0x1F,
        0x20, 0x26, 0x27, 0x28, 0x29, 0x2C, 0x2D, 0x34, 0x44, 0x45, 0x46,
        0x47, 0x57, 0x58, 0x5B, 0x5C, 0x69, 0x6A, 0x75, 0x76, 0x77, 0x78,
        0x79, 0x7B, 0x85,
    }
    invalid_ops = {0x32, 0x7C, 0x7D, 0x7E, 0x7F, 0x80, 0x88}
    data_span_ops = {0xA2, 0xA3, 0xA6, 0xA7, 0xAF, 0xB0, 0xB3, 0xB4, 0xCB, 0xCD}
    stack_span_ops = {0xA4, 0xA5, 0xA8, 0xA9, 0xB1, 0xB2, 0xB5, 0xB6, 0xCC, 0xCE}
    code_cells = (code_bytes + 7) // 8
    pc = 0
    instructions: list[dict] = []

    def operand_at(index: int, what: str) -> tuple[int | None, dict | None]:
        if index >= len(cells):
            return None, _reject(f"truncated {what} operand at cell {pc}", "0x04", pc, instructions)
        return _signed_cell(cells[index]), None

    while pc * 8 < code_bytes:
        if pc >= len(cells):
            return _reject(f"truncated opcode at cell {pc}", "0x04", pc, instructions)
        opcode = cells[pc] & 0xFFFFFFFF
        if not 1 <= opcode <= 0xD4:
            return _reject(f"invalid opcode {opcode:#x} at cell {pc}", "0x06", pc, instructions)
        if opcode in invalid_ops:
            return _reject(f"unsupported opcode {opcode:#x} at cell {pc}", "0x06", pc, instructions)

        next_pc = pc + 1
        if opcode in global_data_ops:
            operand, error = operand_at(pc + 1, "global")
            if error:
                return error
            if not 0 <= operand < data_bytes:
                return _reject(f"global operand {operand} out of range at cell {pc}", "0x04", pc, instructions)
            next_pc = pc + 2
        elif opcode in stack_ops:
            operand, error = operand_at(pc + 1, "stack")
            if error:
                return error
            if not -stack_bytes <= operand <= stack_bytes:
                return _reject(f"stack operand {operand} out of range at cell {pc}", "0x04", pc, instructions)
            next_pc = pc + 2
        elif opcode in branch_ops:
            operand, error = operand_at(pc + 1, "branch")
            if error:
                return error
            relative = operand if file_version >= 10 else operand - pc * 8
            target = pc * 8 + relative
            if not 0 <= target <= code_bytes:
                return _reject(f"branch target {target} out of range at cell {pc}", "0x04", pc, instructions)
            next_pc = pc + 2
        elif opcode in (0x9A, 0x9B):
            lower, upper = (0, data_bytes) if opcode == 0x9A else (-stack_bytes, stack_bytes)
            for index in (pc + 1, pc + 2):
                operand, error = operand_at(index, "paired")
                if error:
                    return error
                if not lower <= operand < upper:
                    return _reject(f"paired operand {operand} out of range at cell {pc}", "0x04", pc, instructions)
            next_pc = pc + 3
        elif opcode == 0x82:
            count, error = operand_at(pc + 1, "switch count")
            if error:
                return error
            if count < 0 or count > len(cells):
                return _reject(f"invalid switch count {count} at cell {pc}", "0x04", pc, instructions)
            for index in range(count + 1):
                target_cell = pc + 2 + 2 * index
                if target_cell >= len(cells):
                    return _reject(f"truncated switch table at cell {pc}", "0x04", pc, instructions)
                operand = _signed_cell(cells[target_cell])
                target_offset = target_cell * 8
                target = operand if file_version < 10 else target_offset + operand - 8
                if not 0 <= target <= code_bytes:
                    return _reject(f"switch target {target} out of range at cell {pc}", "0x04", pc, instructions)
            next_pc = pc + 3 + 2 * count
        elif opcode == 0xA0:
            operand, error = operand_at(pc + 1, "branch")
            if error:
                return error
            target = pc * 8 + operand
            if not 0 <= target <= code_bytes:
                return _reject(f"branch target {target} out of range at cell {pc}", "0x04", pc, instructions)
            next_pc = pc + 2
        elif opcode in (0x9E, 0x9F, 0xA1):
            return _reject(
                f"opcode {opcode:#x} requires a callback that is null in the exact loader path",
                "0x1c", pc, instructions,
            )
        elif opcode in two_cell_ops:
            next_pc = pc + 2
        elif opcode == 0x87:
            next_pc = pc + 3
        elif 0x8A <= opcode <= 0x8D or opcode in (0x9C, 0x9D):
            next_pc = pc + 3
        elif 0x8E <= opcode <= 0x91:
            next_pc = pc + 4
        elif 0x92 <= opcode <= 0x95:
            next_pc = pc + 5
        elif 0x96 <= opcode <= 0x99:
            next_pc = pc + 6
        elif opcode in data_span_ops and data_bytes < 1:
            return _reject(f"opcode {opcode:#x} requires a nonempty data span", "0x04", pc, instructions)
        elif opcode in stack_span_ops and stack_bytes < 0:
            return _reject(f"opcode {opcode:#x} requires a valid stack span", "0x04", pc, instructions)

        if next_pc > len(cells):
            return _reject(f"instruction overruns decoded cells at cell {pc}", "0x04", pc, instructions)
        instructions.append({
            "cell_offset": pc,
            "byte_offset": pc * 8,
            "opcode": opcode,
            "opcode_hex": f"0x{opcode:02x}",
            "cells_consumed": next_pc - pc,
        })
        pc = next_pc
    return {"status": "PASS", "instruction_count": len(instructions), "instructions": instructions}


def _reject(error: str, error_code: str, pc: int, instructions: list[dict]) -> dict:
    return {
        "status": "REJECT", "error": error, "error_code": error_code,
        "cell_offset": pc, "instruction_count": len(instructions), "instructions": instructions,
    }


def _safe_relative(value: str) -> PurePosixPath:
    relative = PurePosixPath(value.replace("\\", "/"))
    if relative.is_absolute() or not relative.parts or ".." in relative.parts or ":" in relative.parts[0]:
        raise ValueError(f"unsafe AMX source path: {value}")
    return relative


def _source_for_row(row: dict, root: Path, project: Path) -> tuple[Path, Path | None]:
    relative = _safe_relative(str(row["source"]))
    if row.get("source_kind") == "gfpak_member":
        source_root = ensure_inside(project / "decoded" / VERSION / "romfs", project / "decoded")
        source = ensure_inside(source_root.joinpath(*relative.parts), source_root)
        container_rel = _safe_relative(str(row["container_source"]))
        container = ensure_inside(
            source_dirs(root)["romfs"].joinpath(*container_rel.parts), source_dirs(root)["romfs"],
        )
        return source, container
    source_root = source_dirs(root)["romfs"]
    source = ensure_inside(source_root.joinpath(*relative.parts), source_root)
    return source, None


def _output_for_row(row: dict, project: Path) -> tuple[Path, str | None]:
    relative = _safe_relative(str(row["source"]))
    output_relative = relative.with_suffix(".json")
    output = ensure_inside(
        project / "decoded" / VERSION / "romfs" / Path(*output_relative.parts),
        project / "decoded",
    )
    return output, output_relative.as_posix() if row.get("source_kind") == "gfpak_member" else None


def _output_payload(data: bytes, row: dict, source_hash: str, fields: dict, cells: list[int], verifier: dict) -> dict:
    code_count = (int(fields["dat"]) - int(fields["cod"])) // 8
    compact = data[int(fields["cod"]):int(fields["size"])]
    return {
        "schema": "lgpe-research/amx-compact-cells/v1",
        "format": "LGPE 1.0.2 AMX compact 64-bit cells",
        "source_version": "Pokemon Let's Go Pikachu 1.0.2",
        "source": row["source"],
        "source_kind": row.get("source_kind", "romfs_file"),
        "source_bytes": len(data),
        "source_sha256": source_hash,
        "container_source": row.get("container_source"),
        "container_sha256": row.get("container_sha256"),
        "container_index": row.get("container_index"),
        "internal_path": row.get("internal_path"),
        "header": fields,
        "compact_stream": {
            "offset": int(fields["cod"]),
            "physical_bytes": len(compact),
            "sha256": hashlib.sha256(compact).hexdigest(),
            "decoded_cells": len(cells),
            "cell_bytes": 8,
        },
        "code_cells_hex": [f"{value:016x}" for value in cells[:code_count]],
        "initialized_data_cells_hex": [f"{value:016x}" for value in cells[code_count:]],
        "instruction_index": verifier["instructions"],
        "game_verifier": {
            "status": verifier["status"],
            "main_sha256": GAME_MAIN_SHA256,
            "parser_function": GAME_PARSER_FUNCTION,
            "validator_function": GAME_VALIDATOR_FUNCTION,
        },
    }


def _receipt(row: dict, source: Path, output: Path, source_hash: str, output_hash: str, output_bytes: int,
             project: Path, container: Path | None) -> dict:
    receipt = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "version": VERSION,
        "source_version": "Pokemon Let's Go Pikachu 1.0.2",
        "nca_folder": NCA,
        "partition": "romfs",
        "relative_source": row.get("container_source") if row.get("source_kind") == "gfpak_member" else row["source"],
        "source_file": str(Path(os.path.abspath(os.fspath(source)))),
        "source_sha256": source_hash,
        "output_file": str(output),
        "output_sha256": output_hash,
        "output_size": output_bytes,
        "method": DECODER_METHOD,
        "tool_version": {"lgpe_research": DECODER_VERSION, "main_sha256": GAME_MAIN_SHA256},
        "status": "DECODED",
        "command": "uv run lgpe decode-amx --execute",
    }
    if row.get("source_kind") == "gfpak_member":
        output_internal = _safe_relative(row["internal_path"]).with_suffix(".json")
        receipt.update({
            "internal_path": output_internal.as_posix(),
            "source_internal_path": _safe_relative(row["internal_path"]).as_posix(),
            "container_index": int(row["container_index"]),
            "container_source_file": str(container),
            "container_source_sha256": row["container_sha256"],
        })
    return receipt


def _write_payload(output: Path, payload: dict, previous_output_sha256: str | None = None) -> tuple[str, int]:
    encoded = (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    output.parent.mkdir(parents=True, exist_ok=True)
    output_hash = hashlib.sha256(encoded).hexdigest()
    if output.exists():
        current_hash = sha256(output)
        if current_hash == output_hash:
            return output_hash, len(encoded)
        if not previous_output_sha256 or current_hash != previous_output_sha256:
            raise FileExistsError(f"conflicting AMX JSON output: {output}")
        temporary = output.with_name(output.name + ".lgpe.partial")
        if temporary.exists():
            raise FileExistsError(f"stale partial AMX output: {temporary}")
        with temporary.open("xb") as stream:
            stream.write(encoded)
        temporary.replace(output)
    else:
        temporary = output.with_name(output.name + ".lgpe.partial")
        if temporary.exists():
            raise FileExistsError(f"stale partial AMX output: {temporary}")
        with temporary.open("xb") as stream:
            stream.write(encoded)
        temporary.replace(output)
    return output_hash, len(encoded)


def _old_output_path(row: dict, project: Path) -> Path | None:
    value = row.get("output")
    if not value:
        return None
    relative = Path(str(value).replace("\\", os.sep).replace("/", os.sep))
    if relative.is_absolute() or ".." in relative.parts:
        return None
    try:
        return ensure_inside(project / relative, project / "decoded")
    except ValueError:
        return None


def decode_amx(root: Path = PROJECT.parent, project: Path = PROJECT, limit: int = 0,
                execute: bool = False, only_sources: set[str] | None = None) -> dict:
    """Decode only streams that pass the exact 1.0.2 header and opcode checks."""
    if limit < 0:
        raise ValueError("limit must be zero or positive")
    manifest_path = project / "manifests" / MANIFEST
    if not manifest_path.is_file():
        catalog_amx_headers(root, project)
    rows = _read_jsonl(manifest_path)
    rows.sort(key=lambda row: (str(row.get("source", "")).casefold(), str(row.get("container_index", ""))))
    if only_sources is not None:
        selected_names = {str(source).replace("\\", "/").casefold() for source in only_sources}
        selected = [row for row in rows if str(row.get("source", "")).casefold() in selected_names]
    else:
        selected = rows
    if limit:
        selected = selected[:limit]
    if not execute:
        return {
            "scanned": 0, "selected": len(selected), "decoded": 0, "failed": 0,
            "unknown": sum(row.get("status") == "UNKNOWN" for row in selected),
            "dry_run": True, "sources": [row.get("source") for row in selected],
            "manifest": str(manifest_path),
        }

    verified_main_sha256 = _verify_exact_game_main(root)
    container_cache: dict[Path, str] = {}
    output_owners: dict[str, list[dict]] = {}
    for row in selected:
        output, _ = _output_for_row(row, project)
        key = os.path.normcase(os.path.abspath(os.fspath(output)))
        output_owners.setdefault(key, []).append(row)
    for key, owners in output_owners.items():
        if len(owners) > 1:
            for row in owners:
                row["_output_collision"] = key

    receipts = []
    failures = []
    resolved = [{"domain": "amx", "source": row.get("source")} for row in selected]
    stale_receipts: set[Path] = set()
    updated = {_manifest_identity(row): row for row in rows}
    for row in selected:
        item = dict(row)
        source: Path | None = None
        container: Path | None = None
        attempted_output: Path | None = None
        attempted_output_hash: str | None = None
        try:
            if item.get("_output_collision"):
                raise ValueError(f"duplicate internal path collides at mirrored output: {item['_output_collision']}")
            if item.get("header_status") != "AMX_HEADER_CANDIDATE":
                raise ValueError("AMX header is not a bounded candidate")
            if item.get("lgpe_runtime_header_check", {}).get("status") != "STATIC_PASS":
                raise ValueError("exact LGPE 1.0.2 AMX header gate rejected this sample")
            source, container = _source_for_row(item, root, project)
            data = source.read_bytes()
            source_hash = hashlib.sha256(data).hexdigest()
            if source_hash != item.get("source_sha256"):
                raise ValueError("AMX source SHA-256 differs from catalog receipt")
            if item.get("source_kind") == "gfpak_member":
                expected_size = int(item["expected_member_bytes"])
                expected_hash = str(item["expected_member_sha256"])
                if len(data) != expected_size or source_hash != expected_hash:
                    raise ValueError("extracted AMX member differs from GFPAK size/SHA-256 receipt")
                assert container is not None
                if container not in container_cache:
                    container_cache[container] = sha256(container)
                if container_cache[container] != item.get("container_sha256"):
                    raise ValueError("GFPAK source SHA-256 differs from catalog receipt")

            fields = item["fields"]
            if int(fields["magic"]) != 0xF1E1 or not int(fields["flags"]) & 0x04:
                raise ValueError("AMX compact 64-bit magic/flag is not present")
            cod, dat, hea = (int(fields[name]) for name in ("cod", "dat", "hea"))
            if not (0 <= cod <= dat <= hea <= 0x7FFFFFFF) or (hea - cod) % 8:
                raise ValueError("AMX compact region boundaries are invalid or not 8-byte aligned")
            size = int(fields["size"])
            if size != len(data) or cod > size:
                raise ValueError("AMX physical size/cod offset differs from source length")
            compact = data[cod:size]
            cells = decode_compact_cells(compact, 8, expected_count=(hea - cod) // 8)
            verifier = validate_game_code(cells, fields)
            if verifier["status"] != "PASS":
                raise ValueError(
                    f"LGPE 1.0.2 opcode verifier {verifier['error_code']} rejected candidate cells: "
                    f"{verifier['error']}"
                )

            output, output_internal = _output_for_row(item, project)
            attempted_output = output
            payload = _output_payload(data, item, source_hash, fields, cells, verifier)
            prior_hash = item.get("output_sha256") if item.get("status") == "DECODED" else None
            output_hash, output_bytes = _write_payload(output, payload, prior_hash)
            attempted_output_hash = output_hash
            if sha256(source) != source_hash:
                raise ValueError("AMX source changed during conversion")
            if container is not None and sha256(container) != container_cache[container]:
                raise ValueError("GFPAK source changed during AMX conversion")

            item.update({
                "status": "DECODED",
                "decoder_status": "COMPACT_CELLS_AND_EXACT_BUILD_OPCODE_STREAM_VALIDATED",
                "body_status": "DECODED",
                "decoded_cell_count": len(cells),
                "instruction_count": verifier["instruction_count"],
                "output": str(output.relative_to(project)),
                "output_sha256": output_hash,
                "output_bytes": output_bytes,
                "error": None,
                "analysis_tool": DECODER_METHOD,
                "analysis_tool_version": DECODER_VERSION,
            })
            receipts.append(_receipt(
                item, source, output, source_hash, output_hash, output_bytes,
                project, container,
            ))
        except (OSError, ValueError, KeyError, TypeError, OverflowError) as exc:
            old_output = _old_output_path(item, project)
            stale_output = attempted_output or old_output
            old_hash = attempted_output_hash or item.get("output_sha256")
            if stale_output is not None:
                try:
                    if stale_output.is_file() and old_hash and sha256(stale_output) == old_hash:
                        stale_output.unlink()
                        stale_receipts.add(stale_output)
                    elif stale_output.is_file():
                        stale_receipts.add(stale_output)
                        item["orphan_output_preserved"] = str(stale_output)
                except OSError as cleanup_error:
                    item["orphan_output_preserved"] = str(stale_output)
                    item["cleanup_error"] = f"{type(cleanup_error).__name__}: {cleanup_error}"
            item.update({
                "status": "FAILED",
                "decoder_status": "DECODE_OR_EXACT_GAME_VALIDATION_FAILED",
                "body_status": "UNKNOWN",
                "error": f"{type(exc).__name__}: {exc}",
                "analysis_tool": DECODER_METHOD,
                "analysis_tool_version": DECODER_VERSION,
            })
            for key in ("output", "output_sha256", "output_bytes", "decoded_cell_count", "instruction_count"):
                item.pop(key, None)
            item.pop("_output_collision", None)
            failures.append({
                "domain": "amx", "source": item.get("source"),
                "status": "FAILED", "error": item["error"],
            })
        updated[_manifest_identity(item)] = item

    # Recheck each container once after all members have been processed.
    for container, digest in container_cache.items():
        if sha256(container) != digest:
            raise ValueError(f"GFPAK source changed during AMX batch: {container}")
    _write_jsonl(manifest_path, sorted(
        updated.values(),
        key=lambda item: (str(item.get("source", "")).casefold(), str(item.get("container_index", ""))),
    ))
    if receipts:
        add_receipts(project, receipts, trusted_outputs=True)
    if stale_receipts:
        remove_receipts(project, stale_receipts, method=DECODER_METHOD)
    merge_failures(project, failures, resolved=resolved)
    final_rows = [updated[_manifest_identity(row)] for row in selected]
    return {
        "scanned": len(selected),
        "selected": len(selected),
        "decoded": sum(row.get("status") == "DECODED" for row in final_rows),
        "failed": sum(row.get("status") == "FAILED" for row in final_rows),
        "unknown": sum(row.get("status") == "UNKNOWN" for row in final_rows),
        "loose_scanned": sum(row.get("source_kind") == "romfs_file" for row in final_rows),
        "archive_member_scanned": sum(row.get("source_kind") == "gfpak_member" for row in final_rows),
        "manifest_rows": len(updated),
        "manifest": str(manifest_path),
        "outputs_registered": len(receipts),
        "game_main_sha256": verified_main_sha256,
        "execute": True,
    }
