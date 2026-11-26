"""Minimal source-backed parser for Wwise 128 DIDX/DATA media entries."""
from __future__ import annotations

import struct
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path, PurePosixPath

from . import assets_decode
from .batch import _receipt, merge_failures, write_jsonl
from .core import PROJECT, VERSION, add_receipts, ensure_inside, sha256, source_dirs


SUPPORTED_BNK_VERSION = 128


def parse_bnk_media(data: bytes) -> dict:
    """Read a Wwise v128 bank chunk table and return bounded DIDX/DATA slices."""
    chunks: dict[str, bytes] = {}
    chunk_rows = []
    offset = 0
    while offset + 8 <= len(data):
        try:
            tag = data[offset:offset + 4].decode("ascii")
        except UnicodeDecodeError as exc:
            raise ValueError(f"non-ASCII BNK chunk tag at 0x{offset:x}") from exc
        if not tag.isprintable():
            raise ValueError(f"non-printable BNK chunk tag at 0x{offset:x}")
        size = struct.unpack_from("<I", data, offset + 4)[0]
        payload_start = offset + 8
        payload_end = payload_start + size
        if payload_end > len(data):
            raise ValueError(f"{tag} chunk exceeds BNK bounds")
        chunk_rows.append({"tag": tag, "offset": offset, "size": size})
        if tag in {"BKHD", "DIDX", "DATA"}:
            if tag in chunks:
                raise ValueError(f"duplicate {tag} chunk")
            chunks[tag] = data[payload_start:payload_end]
        offset = payload_end

    if offset != len(data):
        raise ValueError(f"{len(data) - offset} trailing bytes after BNK chunks")
    if not chunk_rows or chunk_rows[0]["tag"] != "BKHD":
        raise ValueError("BNK must start with BKHD")
    header = chunks.get("BKHD")
    if header is None or len(header) < 8:
        raise ValueError("BKHD lacks version and SoundBank ID")
    version, bank_id = struct.unpack_from("<II", header, 0)
    if version != SUPPORTED_BNK_VERSION:
        raise NotImplementedError(f"Wwise bank version {version} is not verified; expected 128")

    has_didx = "DIDX" in chunks
    has_data = "DATA" in chunks
    if has_didx != has_data:
        raise ValueError("DIDX and DATA chunks must appear together")
    members = []
    if has_didx:
        didx = chunks["DIDX"]
        if len(didx) % 12:
            raise ValueError("DIDX payload size is not a multiple of 12 bytes")
        data_payload = chunks["DATA"]
        for index, record_offset in enumerate(range(0, len(didx), 12)):
            media_id, data_offset, size = struct.unpack_from("<III", didx, record_offset)
            end = data_offset + size
            if end > len(data_payload):
                raise ValueError(f"DIDX media {media_id} exceeds DATA bounds")
            members.append({
                "index": index,
                "media_id": media_id,
                "offset": data_offset,
                "size": size,
                "index_record_hex": didx[record_offset:record_offset + 12].hex(),
                "data": data_payload[data_offset:end],
            })
    return {
        "bank_version": version,
        "bank_id": bank_id,
        "chunks": chunk_rows,
        "data_bytes": len(chunks.get("DATA", b"")),
        "members": members,
    }


def bnk_member_output_path(
    project: Path, relative_source: str, media_id: int, extension: str = ".wem",
) -> Path:
    """Return `<bank>.bnk.contents/<media-id><extension>` under decoded RomFS."""
    relative = PurePosixPath(relative_source.replace("\\", "/"))
    if relative.is_absolute() or ".." in relative.parts or not relative.parts:
        raise ValueError(f"unsafe BNK source path: {relative_source}")
    if relative.suffix.lower() != ".bnk":
        raise ValueError(f"expected a .bnk source path: {relative_source}")
    if not 0 <= media_id <= 0xFFFFFFFF:
        raise ValueError(f"invalid Wwise media ID: {media_id}")
    if not extension.startswith(".") or "/" in extension or "\\" in extension:
        raise ValueError(f"invalid child extension: {extension}")
    destination = (
        project / "decoded" / VERSION / "romfs"
        / Path(*relative.parent.parts)
        / f"{relative.name}.contents"
        / f"{media_id}{extension}"
    )
    return ensure_inside(destination, project / "decoded")


def _read_jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _external_path(path: Path, tool: Path) -> str:
    """Translate WSL paths for Windows tools; leave native tools untouched."""
    if os.name == "nt" or tool.suffix.lower() != ".exe":
        return str(path)
    wslpath = shutil.which("wslpath")
    if not wslpath:
        raise FileNotFoundError("wslpath is required to pass WSL files to Windows vgmstream")
    result = subprocess.run(
        [wslpath, "-w", str(path)], capture_output=True, text=True,
        encoding="utf-8", errors="replace", check=False,
    )
    if result.returncode:
        raise RuntimeError(f"wslpath failed for {path}: {result.stderr[-300:]}")
    return result.stdout.strip()


def _validate_wem(data: bytes) -> dict:
    if len(data) < 12 or data[:4] != b"RIFF" or data[8:12] != b"WAVE":
        raise NotImplementedError("DIDX member is not a validated RIFF/WAVE WEM")
    declared_end = struct.unpack_from("<I", data, 4)[0] + 8
    if declared_end > len(data):
        raise ValueError("WEM RIFF length exceeds indexed payload")
    return {
        "format": "RIFF/WAVE",
        "riff_declared_bytes": declared_end,
        "indexed_bytes": len(data),
        "trailing_bytes": len(data) - declared_end,
    }


def _preserve_unplayable_member(
    project: Path,
    root: Path,
    record: dict,
    source_path: Path,
    source_hash: str,
    payload: bytes,
    output_receipts: dict[str, dict],
    receipts: list[dict],
    error: str,
) -> dict:
    """Keep an indexed non-standalone member as exact .bin evidence, never a fake WEM."""
    raw_sha256 = hashlib.sha256(payload).hexdigest()
    external_wem = source_path.with_name(f"{record['media_id']}.wem")
    external_wem_source = None
    external_wem_sha256 = None
    prefix_matches = False
    if external_wem.is_file():
        external_bytes = external_wem.read_bytes()
        external_wem_sha256 = hashlib.sha256(external_bytes).hexdigest()
        prefix_matches = len(external_bytes) >= len(payload) and external_bytes[:len(payload)] == payload
        external_wem_source = external_wem.relative_to(source_dirs(root)["romfs"]).as_posix()

    extension = ".prefetch.bin" if prefix_matches else ".unsupported.bin"
    internal_path = f"{record['media_id']}{extension}"
    output = bnk_member_output_path(project, record["source"], record["media_id"], extension)
    temporary = output.with_name(output.name + ".lgpe.partial")
    if output.exists():
        if output.read_bytes() != payload:
            raise FileExistsError(f"conflicting raw BNK member output exists: {output}")
    else:
        if temporary.exists():
            raise FileExistsError(f"stale partial output exists: {temporary}")
        output.parent.mkdir(parents=True, exist_ok=True)
        with temporary.open("xb") as stream:
            stream.write(payload)
        temporary.replace(output)

    if sha256(source_path) != source_hash:
        raise ValueError("BNK source changed before raw member receipt")
    output_sha256 = sha256(output)
    output_key = os.path.normcase(os.path.abspath(output)).casefold()
    prior_receipt = output_receipts.get(output_key)
    if prior_receipt and (
        prior_receipt.get("source_sha256") != source_hash
        or prior_receipt.get("output_sha256") != output_sha256
    ):
        raise ValueError("existing raw member receipt conflicts with exact source/output hashes")

    declared_end = struct.unpack_from("<I", payload, 4)[0] + 8 if len(payload) >= 8 and payload[:4] == b"RIFF" else None
    reason = error
    if declared_end is not None and declared_end > len(payload):
        reason = f"RIFF declares {declared_end} bytes but DIDX indexes only {len(payload)} bytes"
        if prefix_matches and external_wem_source:
            reason += f"; exact prefix of {external_wem_source}"

    record.update({
        "status": "UNSUPPORTED",
        "unsupported_reason": reason,
        "payload_class": "PREFETCH_FRAGMENT" if prefix_matches else "UNSUPPORTED_BINARY_FRAGMENT",
        "extract_status": "EXACT_BINARY_EXTRACTED",
        "output": output.relative_to(project).as_posix(),
        "internal_path": internal_path,
        "output_sha256": output_sha256,
        "output_bytes": output.stat().st_size,
        "wav_status": "UNSUPPORTED",
        "wav_error": "indexed bytes are not a complete independently decodable WEM",
        "external_wem_source": external_wem_source,
        "external_wem_sha256": external_wem_sha256,
        "external_wem_prefix_matches": prefix_matches if external_wem_source else None,
        "payload_sha256": raw_sha256,
    })
    receipt = _receipt(
        project, root, record["source"], source_path, output,
        "Wwise v128 DIDX/DATA exact non-standalone member extraction",
        record["tool_versions"], source_sha256=source_hash,
        output_sha256=output_sha256, status="DECODED",
        internal_path=internal_path,
        container_index=record["container_index"],
        container_source_file=str(source_path),
        container_source_sha256=source_hash,
        wwise_bank_id=record["bank_id"], wwise_bank_version=record["bank_version"],
        media_id=record["media_id"], data_offset=record["data_offset"],
        indexed_size_bytes=record["size_bytes"], index_record_hex=record["index_record_hex"],
        payload_sha256=raw_sha256,
        external_wem_source=external_wem_source,
        external_wem_sha256=external_wem_sha256,
        external_wem_prefix_matches=prefix_matches if external_wem_source else None,
    )
    receipts.append(receipt)
    output_receipts[output_key] = receipt
    return record


def _output_receipts(project: Path) -> dict[str, dict]:
    rows = _read_jsonl(project / "manifests" / "outputs.jsonl")
    return {
        os.path.normcase(os.path.abspath(row["output_file"])).casefold(): row
        for row in rows if row.get("output_file")
    }


def run_bnk_media_batch(
    root: Path = PROJECT.parent,
    project: Path = PROJECT,
    limit: int = 20,
    execute: bool = False,
    tool: Path | None = None,
    timeout: int = 240,
    only_sources: set[str] | None = None,
) -> dict:
    """Extract indexed internal WEMs and decode them to path-mirrored WAVs.

    ``limit`` bounds the number of DIDX members, after source-list filtering.
    Bank chunk parsing remains bounded to the successful BNK manifest rows so
    the CLI can report the complete candidate count before choosing members.
    """
    if limit < 0:
        raise ValueError("limit must be zero (all) or a positive member count")
    romfs = source_dirs(root)["romfs"]
    tool = Path(tool or (project / "tools" / "bin" / "vgmstream-r2168" / "vgmstream-cli.exe"))
    bnk_manifest = project / "manifests" / "bnk.jsonl"
    if not bnk_manifest.is_file():
        raise FileNotFoundError("run `uv run lgpe decode-banks` before internal media extraction")

    success = {"DECODED", "DECODED_EXISTING_VERIFIED"}
    input_rows = [row for row in _read_jsonl(bnk_manifest) if row.get("status") in success]
    selected_names = {item.replace("\\", "/").casefold() for item in only_sources} if only_sources is not None else None
    old_bank_rows = _read_jsonl(project / "manifests" / "bnk_media_banks.jsonl")
    bank_results = []
    members = []
    bank_sources: dict[str, tuple[Path, str, dict]] = {}

    for row in sorted(input_rows, key=lambda item: str(item.get("source", "")).casefold()):
        relative = PurePosixPath(str(row.get("source", "")).replace("\\", "/"))
        if relative.is_absolute() or ".." in relative.parts or not relative.parts or relative.suffix.lower() != ".bnk":
            if selected_names is not None and str(row.get("source", "")).replace("\\", "/").casefold() not in selected_names:
                continue
            bank_results.append({"source": row.get("source"), "status": "FAILED", "error": "unsafe or non-BNK source path"})
            continue
        source_rel = relative.as_posix()
        if selected_names is not None and source_rel.casefold() not in selected_names:
            continue
        source_path = ensure_inside(romfs.joinpath(*relative.parts), romfs)
        base = {
            "schema": "lgpe-wwise-internal-bank-v1",
            "source": source_rel,
            "source_bytes": row.get("source_bytes"),
            "wwiser_commit": "08e937b649bc7007c234bbd59e34a41d5eef3b38",
        }
        try:
            raw = source_path.read_bytes()
            bank_sha256 = hashlib.sha256(raw).hexdigest()
            if row.get("source_sha256") and bank_sha256 != row["source_sha256"]:
                raise ValueError("BNK source hash differs from bnk.jsonl")
            parsed = parse_bnk_media(raw)
            entry_count = len(parsed["members"])
            bank_result = {
                **base,
                "status": "INDEXED" if entry_count else "NO_INTERNAL_MEDIA",
                "bank_version": parsed["bank_version"],
                "bank_id": parsed["bank_id"],
                "chunk_tags": [chunk["tag"] for chunk in parsed["chunks"]],
                "data_bytes": parsed["data_bytes"],
                "member_count": entry_count,
                "member_bytes": sum(member["size"] for member in parsed["members"]),
                "source_sha256": bank_sha256,
            }
            bank_results.append(bank_result)
            bank_sources[source_rel] = (source_path, bank_sha256, parsed)
            duplicate_ids = {
                member["media_id"] for member in parsed["members"]
                if sum(other["media_id"] == member["media_id"] for other in parsed["members"]) > 1
            }
            for member in parsed["members"]:
                internal_path = f"{member['media_id']}.wem"
                wem_output = bnk_member_output_path(project, source_rel, member["media_id"])
                wav_output = bnk_member_output_path(project, source_rel, member["media_id"], ".wav")
                record = {
                    "schema": "lgpe-wwise-internal-media-v1",
                    "domain": "bnk-media",
                    "source": source_rel,
                    "source_sha256": bank_sha256,
                    "container_source_sha256": bank_sha256,
                    "bank_id": parsed["bank_id"],
                    "bank_version": parsed["bank_version"],
                    "container_index": member["index"],
                    "media_id": member["media_id"],
                    "index_record_hex": member["index_record_hex"],
                    "data_offset": member["offset"],
                    "size_bytes": member["size"],
                    "internal_path": internal_path,
                    "output": wem_output.relative_to(project).as_posix(),
                    "wav_internal_path": f"{member['media_id']}.wav",
                    "wav_output": wav_output.relative_to(project).as_posix(),
                    "method": "Wwise v128 DIDX index into DATA exact byte slice",
                    "tool_versions": {
                        "wwiser_version": "20260808",
                        "wwiser_commit": "08e937b649bc7007c234bbd59e34a41d5eef3b38",
                    },
                    "_payload": member["data"],
                }
                if member["media_id"] in duplicate_ids:
                    record.update({"status": "UNKNOWN", "error": "duplicate media ID would collide in mirrored path"})
                members.append(record)
        except NotImplementedError as exc:
            bank_results.append({**base, "status": "UNSUPPORTED", "error": str(exc)})
        except Exception as exc:
            bank_results.append({**base, "status": "FAILED", "error": f"{type(exc).__name__}: {exc}"})

    old_media_rows = _read_jsonl(project / "manifests" / "bnk_media.jsonl")
    old_by_key = {
        (str(item.get("source", "")).casefold(), str(item.get("container_index", ""))): item
        for item in old_media_rows
    }
    eligible_members = [
        item for item in members
        if item.get("status") != "UNKNOWN"
        and (selected_names is None or item["source"].casefold() in selected_names)
    ]
    if limit:
        by_source: dict[str, list[dict]] = {}
        for item in eligible_members:
            by_source.setdefault(item["source"].casefold(), []).append(item)
        source_order = sorted(by_source)
        cursors = dict.fromkeys(source_order, 0)
        selected_members = []
        while len(selected_members) < limit:
            advanced = False
            for source in source_order:
                index = cursors[source]
                if index >= len(by_source[source]):
                    continue
                selected_members.append(by_source[source][index])
                cursors[source] = index + 1
                advanced = True
                if len(selected_members) >= limit:
                    break
            if not advanced:
                break
    else:
        selected_members = eligible_members
    selected_keys = {
        (item["source"].casefold(), str(item["container_index"]))
        for item in selected_members
    }
    output_receipts = _output_receipts(project)
    if execute and selected_members and not tool.is_file():
        raise FileNotFoundError(f"vgmstream-cli missing: {tool}")
    tool_sha256 = sha256(tool) if execute and selected_members else None
    tool_version = {"name": "vgmstream-cli", "release": "r2168", "sha256": tool_sha256}

    results = []
    receipts = []
    failures = []
    for member in members:
        record = {key: value for key, value in member.items() if key != "_payload"}
        key = (record["source"].casefold(), str(record["container_index"]))
        old = old_by_key.get(key)
        if record.get("status") == "UNKNOWN":
            results.append(record)
            continue
        if key not in selected_keys:
            if old and old.get("status") in {"DECODED", "DECODED_EXISTING_VERIFIED", "FAILED", "UNSUPPORTED", "UNKNOWN"}:
                results.append(old)
            else:
                results.append({**record, "status": "PENDING"})
            continue
        if not execute:
            if old and old.get("status") in {
                "DECODED", "DECODED_EXISTING_VERIFIED", "FAILED", "UNSUPPORTED", "UNKNOWN",
            }:
                results.append(old)
            else:
                results.append({**record, "status": "DRY_RUN"})
            continue

        source_path, source_hash, _ = bank_sources[record["source"]]
        payload = member["_payload"]
        raw_sha256 = hashlib.sha256(payload).hexdigest()
        wem_output = project / record["output"]
        wav_output = project / record["wav_output"]
        wem_created = False
        wav_created = False
        wem_temp = wem_output.with_name(wem_output.name + ".lgpe.partial")
        wav_temp = wav_output.with_name(wav_output.stem + ".lgpe.partial.wav")
        try:
            try:
                validation = _validate_wem(payload)
            except NotImplementedError as exc:
                record = _preserve_unplayable_member(
                    project, root, record, source_path, source_hash, payload,
                    output_receipts, receipts, f"{type(exc).__name__}: {exc}",
                )
                failures.append({
                    "domain": "bnk-media", "source": record["source"],
                    "status": "UNSUPPORTED",
                    "error": f"member {record['container_index']} ({record['media_id']}): {record['unsupported_reason']}",
                })
                results.append(record)
                continue
            except ValueError as exc:
                if str(exc) != "WEM RIFF length exceeds indexed payload":
                    raise
                record = _preserve_unplayable_member(
                    project, root, record, source_path, source_hash, payload,
                    output_receipts, receipts, f"{type(exc).__name__}: {exc}",
                )
                failures.append({
                    "domain": "bnk-media", "source": record["source"],
                    "status": "UNSUPPORTED",
                    "error": f"member {record['container_index']} ({record['media_id']}): {record['unsupported_reason']}",
                })
                results.append(record)
                continue
            if wem_output.exists():
                if wem_output.read_bytes() != payload:
                    raise FileExistsError(f"conflicting BNK member output exists: {wem_output}")
            else:
                if wem_temp.exists():
                    raise FileExistsError(f"stale partial output exists: {wem_temp}")
                wem_output.parent.mkdir(parents=True, exist_ok=True)
                with wem_temp.open("xb") as stream:
                    stream.write(payload)
                wem_temp.replace(wem_output)
                wem_created = True
            output_receipt = output_receipts.get(os.path.normcase(os.path.abspath(wem_output)).casefold())
            if output_receipt and output_receipt.get("source_sha256") != source_hash:
                raise ValueError("existing WEM receipt belongs to a different BNK source hash")
            if output_receipt and output_receipt.get("output_sha256") != raw_sha256:
                raise ValueError("existing WEM receipt differs from the exact indexed media bytes")

            if sha256(source_path) != source_hash:
                raise ValueError("BNK source changed before internal media receipt")
            receipts.append(_receipt(
                project, root, record["source"], source_path, wem_output,
                "Wwise v128 DIDX/DATA exact media extraction",
                record["tool_versions"], source_sha256=source_hash,
                output_sha256=raw_sha256, status="DECODED",
                internal_path=record["internal_path"],
                container_index=record["container_index"],
                container_source_file=str(source_path),
                container_source_sha256=source_hash,
                wwise_bank_id=record["bank_id"], wwise_bank_version=record["bank_version"],
                media_id=record["media_id"], data_offset=record["data_offset"],
                indexed_size_bytes=record["size_bytes"], index_record_hex=record["index_record_hex"],
                payload_sha256=raw_sha256,
            ))

            if wav_output.exists():
                wav_receipt = output_receipts.get(os.path.normcase(os.path.abspath(wav_output)).casefold())
                if not wav_receipt or wav_receipt.get("source_sha256") != source_hash:
                    raise FileExistsError(f"unattributed/conflicting WAV output exists: {wav_output}")
                wav_sha256 = sha256(wav_output)
                if wav_sha256 != wav_receipt.get("output_sha256"):
                    raise ValueError("existing WAV output differs from its receipt")
                wav_validation = assets_decode.validate_output(wav_output)
                wav_status = "DECODED_EXISTING_VERIFIED"
            else:
                if wav_temp.exists():
                    raise FileExistsError(f"stale partial WAV exists: {wav_temp}")
                command = [
                    str(tool), "-i", "-o", _external_path(wav_temp, tool),
                    _external_path(wem_output, tool),
                ]
                try:
                    completed = subprocess.run(
                        command, capture_output=True, text=True, encoding="utf-8",
                        errors="replace", timeout=timeout, check=False,
                    )
                except subprocess.TimeoutExpired as exc:
                    raise TimeoutError(f"vgmstream timed out after {timeout}s: {exc}") from exc
                if completed.returncode or not wav_temp.is_file():
                    raise RuntimeError(
                        f"vgmstream exit {completed.returncode}: {completed.stderr[-500:]}"
                    )
                wav_validation = assets_decode.validate_output(wav_temp)
                if wav_output.exists():
                    raise FileExistsError(f"WAV output appeared during decode: {wav_output}")
                wav_temp.replace(wav_output)
                wav_created = True
                wav_sha256 = sha256(wav_output)
                wav_status = "DECODED"

            if sha256(source_path) != source_hash:
                raise ValueError("BNK source changed during internal media extraction")
            wem_sha256 = sha256(wem_output)
            record.update({
                "status": wav_status,
                "extract_status": "DECODED" if wem_sha256 == raw_sha256 else "FAILED",
                "extract_validation": validation,
                "output_sha256": wem_sha256,
                "output_bytes": wem_output.stat().st_size,
                "wav_status": wav_status,
                "wav_output_sha256": wav_sha256,
                "wav_output_bytes": wav_output.stat().st_size,
                "wav_validation": wav_validation,
                "vgmstream": tool_version,
            })
            receipts.append(_receipt(
                project, root, record["source"], source_path, wav_output,
                "vgmstream r2168 decode of indexed BNK media",
                tool_version, source_sha256=source_hash,
                output_sha256=wav_sha256, status="DECODED",
                internal_path=record["wav_internal_path"],
                container_index=record["container_index"],
                container_source_file=str(source_path),
                container_source_sha256=source_hash,
                input_internal_path=record["internal_path"],
                input_internal_sha256=raw_sha256,
                media_id=record["media_id"], data_offset=record["data_offset"],
            ))
        except NotImplementedError as exc:
            record.update({"status": "UNSUPPORTED", "error": f"{type(exc).__name__}: {exc}"})
            failures.append({"domain": "bnk-media", "source": record["source"], "status": "UNSUPPORTED", "error": f"member {record['container_index']} ({record['media_id']}): {exc}"})
        except Exception as exc:
            record.update({"status": "FAILED", "error": f"{type(exc).__name__}: {exc}"})
            failures.append({"domain": "bnk-media", "source": record["source"], "status": "FAILED", "error": f"member {record['container_index']} ({record['media_id']}): {type(exc).__name__}: {exc}"})
        finally:
            if wem_temp.exists():
                wem_temp.unlink()
            if wav_temp.exists():
                wav_temp.unlink()
        results.append(record)

    media_manifest = project / "manifests" / "bnk_media.jsonl"
    final_by_key = {
        (str(item.get("source", "")).casefold(), str(item.get("container_index", ""))): item
        for item in old_media_rows
    }
    for record in results:
        final_by_key[(record["source"].casefold(), str(record["container_index"]))] = record
    write_jsonl(media_manifest, sorted(final_by_key.values(), key=lambda item: (item["source"].casefold(), int(item["container_index"]))))
    final_bank_rows = {
        str(row.get("source", "")).casefold(): row
        for row in old_bank_rows
        if selected_names is None or str(row.get("source", "")).replace("\\", "/").casefold() not in selected_names
    }
    for row in bank_results:
        final_bank_rows[str(row.get("source", "")).casefold()] = row
    write_jsonl(
        project / "manifests" / "bnk_media_banks.jsonl",
        sorted(final_bank_rows.values(), key=lambda item: str(item.get("source", "")).casefold()),
    )
    if receipts:
        add_receipts(project, receipts, trusted_outputs=True)

    bank_failures = [row for row in bank_results if row.get("status") in {"FAILED", "UNSUPPORTED"}]
    failure_rows = failures + [
        {"domain": "bnk-media", "source": row.get("source"), "status": row.get("status"), "error": row.get("error")}
        for row in bank_failures
    ]
    selected_sources = {item["source"].casefold() for item in selected_members}
    resolved = []
    for source_rel in selected_sources:
        current = [row for row in final_by_key.values() if row["source"].casefold() == source_rel]
        if current and all(row.get("status") != "FAILED" for row in current):
            resolved.append({"domain": "bnk-media", "source": current[0]["source"]})
    merge_failures(project, failure_rows, resolved=resolved)

    statuses = [row.get("status") for row in final_by_key.values()]
    return {
        "banks_scanned": len(bank_results),
        "banks_with_internal_media": sum(row.get("status") == "INDEXED" for row in bank_results),
        "banks_without_internal_media": sum(row.get("status") == "NO_INTERNAL_MEDIA" for row in bank_results),
        "banks_failed": len(bank_failures),
        "candidate_members": len(members),
        "selected_members": len(selected_members),
        "decoded_members": sum(status in success for status in statuses),
        "failed_members": sum(status == "FAILED" for status in statuses),
        "unknown_members": sum(status == "UNKNOWN" for status in statuses),
        "unsupported_members": sum(status == "UNSUPPORTED" for status in statuses),
        "pending_members": sum(status == "PENDING" for status in statuses),
        "execute": execute,
        "banks_manifest": str(project / "manifests" / "bnk_media_banks.jsonl"),
        "manifest": str(media_manifest),
    }
