"""Auditable local cross-checks for loose Wwise media IDs without HIRC matches."""
from __future__ import annotations

import hashlib
import json
import re
import struct
from collections import defaultdict
from pathlib import Path, PurePosixPath, PureWindowsPath

from .bnk_media import parse_bnk_media
from .core import PROJECT, VERSION, ensure_inside, source_dirs


SCHEMA = "lgpe-research.wwise-unreferenced-wem-id-audit.v1"
METHOD = "STATIC_HIRC_DIDX_AND_BSEQ_RAW_BYTE_CROSSCHECK"
SUCCESS = {"DECODED", "DECODED_EXISTING_VERIFIED"}
WEM_OUTPUT = "manifests/wwise_unreferenced_wem_id_audit.json"


def _id_patterns(source_id: int) -> dict[str, bytes]:
    if isinstance(source_id, bool) or not isinstance(source_id, int) or not 0 <= source_id <= 0xFFFFFFFF:
        raise ValueError("Wwise source ID must be an unsigned 32-bit integer")
    hexadecimal = f"{source_id:08x}"
    return {
        "u32le": struct.pack("<I", source_id),
        "u32be": struct.pack(">I", source_id),
        "u64le": struct.pack("<Q", source_id),
        "u64be": struct.pack(">Q", source_id),
        "decimal_ascii": str(source_id).encode("ascii"),
        "hex8_lower_ascii": hexadecimal.encode("ascii"),
        "hex8_upper_ascii": hexadecimal.upper().encode("ascii"),
        "hex0x_lower_ascii": ("0x" + hexadecimal).encode("ascii"),
        "hex0x_upper_ascii": ("0x" + hexadecimal.upper()).encode("ascii"),
        "hex0X_lower_ascii": ("0X" + hexadecimal).encode("ascii"),
        "hex0X_upper_ascii": ("0X" + hexadecimal.upper()).encode("ascii"),
    }


def scan_id_occurrences(data: bytes, source_id: int) -> dict:
    """Find overlapping occurrences of one u32 ID in documented binary/text forms."""
    patterns = _id_patterns(source_id)
    counts = {}
    matches = []
    for encoding, needle in patterns.items():
        offsets = []
        start = 0
        while True:
            offset = data.find(needle, start)
            if offset < 0:
                break
            offsets.append(offset)
            matches.append({"encoding": encoding, "offset": offset})
            start = offset + 1
        counts[encoding] = len(offsets)
    matches.sort(key=lambda item: (item["offset"], item["encoding"]))
    return {"countsByEncoding": counts, "matches": matches}


def _read_jsonl(path: Path) -> tuple[list[dict], bytes]:
    raw = path.read_bytes()
    rows = []
    for line_number, line in enumerate(raw.decode("utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSONL at {path.name}:{line_number}: {exc}") from exc
        if not isinstance(row, dict):
            raise ValueError(f"manifest row is not an object: {path.name}:{line_number}")
        rows.append(row)
    return rows, raw


def _manifest_record(name: str, rows: list[dict], raw: bytes) -> dict:
    return {
        "path": f"manifests/{name}",
        "rows": len(rows),
        "bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def _safe_relative(value: object, label: str) -> PurePosixPath:
    text = str(value or "").replace("\\", "/")
    path = PurePosixPath(text)
    windows = PureWindowsPath(str(value or ""))
    if (
        not path.parts
        or path.is_absolute()
        or windows.is_absolute()
        or windows.drive
        or ".." in path.parts
    ):
        raise ValueError(f"unsafe {label} path: {value}")
    return path


def _safe_source_path(base: Path, value: object, label: str) -> tuple[PurePosixPath, Path]:
    relative = _safe_relative(value, label)
    path = ensure_inside(base.joinpath(*relative.parts), base)
    if not path.is_file():
        raise FileNotFoundError(f"missing {label}: {relative.as_posix()}")
    return relative, path


def _safe_output_path(project: Path, value: object, label: str) -> tuple[PurePosixPath, Path]:
    relative = _safe_relative(value, label)
    if relative.parts[0] != "decoded":
        raise ValueError(f"{label} must be under decoded/: {value}")
    path = ensure_inside(project.joinpath(*relative.parts), project / "decoded")
    if not path.is_file():
        raise FileNotFoundError(f"missing {label}: {relative.as_posix()}")
    return relative, path


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _expected_sha256(value: object, label: str) -> str:
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ValueError(f"{label} is not a lowercase SHA-256")
    return value


def _verify_hash(path: Path, expected: object, label: str) -> tuple[str, int]:
    raw = path.read_bytes()
    actual = _sha256(raw)
    expected_hash = _expected_sha256(expected, f"{label} hash")
    if actual != expected_hash:
        raise ValueError(f"{label} hash mismatch: {path}")
    return actual, len(raw)


def _source_key(value: object, label: str) -> str:
    return _safe_relative(value, label).as_posix()


def _index_unique(rows: list[dict], key_fn, label: str) -> dict:
    result = {}
    for row in rows:
        key = key_fn(row)
        if key in result:
            raise ValueError(f"duplicate {label}: {key}")
        result[key] = row
    return result


def _validate_bnk_didx(root: Path, project: Path) -> tuple[dict, dict[str, dict], dict[int, list[dict]]]:
    romfs = source_dirs(root)["romfs"].resolve()
    bnk_rows, bnk_raw = _read_jsonl(project / "manifests" / "bnk.jsonl")
    bank_index_rows, bank_index_raw = _read_jsonl(project / "manifests" / "bnk_media_banks.jsonl")
    media_rows, media_raw = _read_jsonl(project / "manifests" / "bnk_media.jsonl")

    if not bnk_rows or any(row.get("status") not in SUCCESS for row in bnk_rows):
        raise ValueError("BNK manifest is empty or contains unverified bank rows")
    bnk_by_source = _index_unique(
        bnk_rows, lambda row: _source_key(row.get("source"), "BNK source"), "BNK source",
    )
    bank_index_by_source = _index_unique(
        bank_index_rows,
        lambda row: _source_key(row.get("source"), "BNK media-bank source"),
        "BNK media-bank source",
    )
    media_by_key = _index_unique(
        media_rows,
        lambda row: (
            _source_key(row.get("source"), "DIDX bank source"),
            int(row.get("container_index", -1)),
        ),
        "DIDX source/index",
    )
    if set(bank_index_by_source) != set(bnk_by_source):
        raise ValueError("BNK media-bank manifest does not cover the verified BNK manifest")

    verified_banks = {}
    didx_by_id: dict[int, list[dict]] = defaultdict(list)
    expected_media = {}
    bank_inventory = []
    for source in sorted(bnk_by_source):
        row = bnk_by_source[source]
        relative, path = _safe_source_path(romfs, source, "BNK source")
        raw = path.read_bytes()
        source_hash = _sha256(raw)
        if source_hash != _expected_sha256(row.get("source_sha256"), "BNK source hash"):
            raise ValueError(f"BNK source hash mismatch: {source}")
        if row.get("source_bytes") != len(raw):
            raise ValueError(f"BNK source size mismatch: {source}")

        parsed = parse_bnk_media(raw)
        summary_row = bank_index_by_source[source]
        member_count = len(parsed["members"])
        expected_status = "INDEXED" if member_count else "NO_INTERNAL_MEDIA"
        expected_summary = {
            "status": expected_status,
            "source_sha256": source_hash,
            "source_bytes": len(raw),
            "bank_version": parsed["bank_version"],
            "bank_id": parsed["bank_id"],
            "chunk_tags": [chunk["tag"] for chunk in parsed["chunks"]],
            "data_bytes": parsed["data_bytes"],
            "member_count": member_count,
            "member_bytes": sum(member["size"] for member in parsed["members"]),
        }
        if any(summary_row.get(key) != value for key, value in expected_summary.items()):
            raise ValueError(f"BNK media-bank summary differs from parsed source: {source}")

        expected_xml = PurePosixPath("decoded") / VERSION / "romfs" / relative.with_suffix(".xml")
        output_rel, output_path = _safe_output_path(project, row.get("output"), "BNK XML output")
        if output_rel != expected_xml:
            raise ValueError(f"BNK XML output path is not mirrored: {source}")
        xml_hash, xml_bytes = _verify_hash(output_path, row.get("output_sha256"), "BNK XML output")
        verified_banks[source] = {
            "sourceSha256": source_hash,
            "xml": output_rel.as_posix(),
            "xmlSha256": xml_hash,
        }
        bank_inventory.append({
            "source": source,
            "sourceSha256": source_hash,
            "sourceBytes": len(raw),
            "bankId": parsed["bank_id"],
            "bankVersion": parsed["bank_version"],
            "didxMemberCount": member_count,
            "xml": output_rel.as_posix(),
            "xmlBytes": xml_bytes,
            "xmlSha256": xml_hash,
        })

        for member in parsed["members"]:
            key = (source, member["index"])
            # The stored output suffix can be .wem, .prefetch.bin, or
            # .unsupported.bin; it is not part of the DIDX identity itself.
            expected = {
                "source": source,
                "source_sha256": source_hash,
                "container_index": member["index"],
                "media_id": member["media_id"],
                "index_record_hex": member["index_record_hex"],
                "data_offset": member["offset"],
                "size_bytes": member["size"],
            }
            expected_media[key] = expected
            didx_by_id[member["media_id"]].append({
                "bankSource": source,
                "bankSourceSha256": source_hash,
                "containerIndex": member["index"],
                "internalPath": f"{member['media_id']}.wem",
                "indexRecordHex": member["index_record_hex"],
                "dataOffset": member["offset"],
                "sizeBytes": member["size"],
            })

    if set(media_by_key) != set(expected_media):
        raise ValueError("DIDX media manifest differs from parsed BNK sources")
    for key, expected in expected_media.items():
        row = media_by_key[key]
        if any(row.get(field) != value for field, value in expected.items()):
            raise ValueError(f"DIDX media manifest differs from parsed BNK sources: {key[0]} index {key[1]}")
    for entries in didx_by_id.values():
        entries.sort(key=lambda item: (item["bankSource"], item["containerIndex"]))

    inputs = {
        "bnk": _manifest_record("bnk.jsonl", bnk_rows, bnk_raw),
        "bnkMediaBanks": _manifest_record("bnk_media_banks.jsonl", bank_index_rows, bank_index_raw),
        "bnkMedia": _manifest_record("bnk_media.jsonl", media_rows, media_raw),
    }
    return {
        "inputs": inputs,
        "banks": bank_inventory,
        "didxRows": len(expected_media),
    }, verified_banks, didx_by_id


def _validate_unreferenced_wems(root: Path, project: Path, banks: dict[str, dict]) -> tuple[list[dict], dict]:
    romfs = source_dirs(root)["romfs"].resolve()
    audio_rows, audio_raw = _read_jsonl(project / "manifests" / "audio.jsonl")
    orphan_rows, orphan_raw = _read_jsonl(project / "manifests" / "wwise_unreferenced_wem.jsonl")
    audio_by_source = _index_unique(
        audio_rows, lambda row: _source_key(row.get("source"), "WEM source"), "WEM source",
    )
    if not orphan_rows:
        raise ValueError("Wwise unreferenced-WEM manifest is empty")
    outputs = []
    seen_ids = set()
    for row in orphan_rows:
        if row.get("sourceVersion") != "Let's Go Pikachu 1.0.2":
            raise ValueError("unreferenced WEM row does not identify Let's Go Pikachu 1.0.2")
        source_id_text = row.get("sourceId")
        if not isinstance(source_id_text, str) or not source_id_text.isdecimal():
            raise ValueError("unreferenced WEM sourceId is not decimal")
        source_id = int(source_id_text)
        if not 0 <= source_id <= 0xFFFFFFFF:
            raise ValueError("unreferenced WEM sourceId is outside u32 range")
        if source_id in seen_ids:
            raise ValueError(f"duplicate unreferenced WEM sourceId: {source_id}")
        seen_ids.add(source_id)

        wem_relative, wem_path = _safe_source_path(romfs, row.get("wemSource"), "loose WEM source")
        if wem_relative.suffix.lower() != ".wem" or wem_relative.stem != source_id_text:
            raise ValueError(f"unreferenced WEM path does not match sourceId {source_id_text}")
        audio_row = audio_by_source.get(wem_relative.as_posix())
        if audio_row is None or audio_row.get("status") not in SUCCESS:
            raise ValueError(f"unreferenced WEM lacks a successful audio manifest row: {wem_relative}")
        wem_hash, wem_bytes = _verify_hash(wem_path, row.get("wemSourceSha256"), "loose WEM source")
        if row.get("wemSourceBytes") != wem_bytes:
            raise ValueError(f"unreferenced WEM size mismatch: {wem_relative}")
        if audio_row.get("source_sha256") != wem_hash or audio_row.get("source_bytes") != wem_bytes:
            raise ValueError(f"WEM source differs from audio manifest: {wem_relative}")
        if row.get("audioReceiptStatus") != audio_row.get("status"):
            raise ValueError(f"WEM audio status differs from audio manifest: {wem_relative}")

        wav_relative, wav_path = _safe_output_path(project, row.get("wav"), "WEM WAV output")
        audio_output_relative, audio_output_path = _safe_output_path(project, audio_row.get("output"), "audio manifest output")
        if wav_relative != audio_output_relative or wav_path != audio_output_path:
            raise ValueError(f"unreferenced WEM WAV path differs from audio manifest: {wem_relative}")
        wav_hash, wav_bytes = _verify_hash(wav_path, row.get("wavSha256"), "WEM WAV output")
        if audio_row.get("output_sha256") != wav_hash or audio_row.get("output_bytes") != wav_bytes:
            raise ValueError(f"WEM WAV output differs from audio manifest: {wem_relative}")

        hirc_matches = row.get("hircMatches")
        if not isinstance(hirc_matches, list) or row.get("hircMatchCount") != len(hirc_matches):
            raise ValueError(f"unreferenced WEM HIRC match list is malformed: {source_id_text}")
        if row.get("hircSearchBankCount") != len(banks) or row.get("hircSearchBankFailures") != 0:
            raise ValueError(f"unreferenced WEM HIRC search did not cover the verified bank set: {source_id_text}")
        for match in hirc_matches:
            bank_source = _source_key(match.get("bankSource"), "HIRC bank source")
            bank = banks.get(bank_source)
            if (
                bank is None
                or match.get("bankSourceSha256") != bank["sourceSha256"]
                or match.get("bankXml") != bank["xml"]
                or match.get("bankXmlSha256") != bank["xmlSha256"]
                or str(match.get("sourceId")) != source_id_text
            ):
                raise ValueError(f"unreferenced WEM HIRC match has stale bank provenance: {source_id_text}")

        outputs.append({
            "sourceId": source_id_text,
            "wemSource": wem_relative.as_posix(),
            "wemSourceBytes": wem_bytes,
            "wemSourceSha256": wem_hash,
            "audioReceiptStatus": audio_row["status"],
            "wav": wav_relative.as_posix(),
            "wavBytes": wav_bytes,
            "wavSha256": wav_hash,
            "hirc": {
                "searchBankCount": len(banks),
                "searchBankFailures": 0,
                "matchCount": len(hirc_matches),
                "matches": hirc_matches,
            },
        })
    outputs.sort(key=lambda item: int(item["sourceId"]))
    inputs = {
        "audio": _manifest_record("audio.jsonl", audio_rows, audio_raw),
        "wwiseUnreferencedWem": _manifest_record("wwise_unreferenced_wem.jsonl", orphan_rows, orphan_raw),
    }
    return outputs, inputs


def _scan_bseq_sources(root: Path, project: Path, targets: list[dict]) -> tuple[list[dict], dict]:
    romfs = source_dirs(root)["romfs"].resolve()
    rows, raw_manifest = _read_jsonl(project / "manifests" / "bseq.jsonl")
    if not rows:
        raise ValueError("BSEQ manifest is empty")
    source_rows = _index_unique(
        rows, lambda row: _source_key(row.get("source"), "BSEQ source"), "BSEQ source",
    )
    for target in targets:
        target["bseq"] = {
            "searchedSources": 0,
            "countsByEncoding": {name: 0 for name in _id_patterns(int(target["sourceId"]))},
            "matches": [],
        }

    source_inventory = []
    source_bytes_total = 0
    for source in sorted(source_rows):
        row = source_rows[source]
        relative, path = _safe_source_path(romfs, source, "BSEQ source")
        data = path.read_bytes()
        source_hash = _sha256(data)
        expected_hash = _expected_sha256(row.get("source_sha256"), "BSEQ source hash")
        if source_hash != expected_hash:
            raise ValueError(f"BSEQ source hash mismatch: {source}")
        if row.get("source_bytes") != len(data):
            raise ValueError(f"BSEQ source size mismatch: {source}")
        source_bytes_total += len(data)
        source_inventory.append({
            "source": relative.as_posix(),
            "bytes": len(data),
            "sha256": source_hash,
            "manifestStatus": row.get("status"),
        })
        for target in targets:
            result = scan_id_occurrences(data, int(target["sourceId"]))
            target["bseq"]["searchedSources"] += 1
            for encoding, count in result["countsByEncoding"].items():
                target["bseq"]["countsByEncoding"][encoding] += count
            target["bseq"]["matches"].extend({
                "source": relative.as_posix(), **match,
            } for match in result["matches"])

    for target in targets:
        target["bseq"]["matches"].sort(
            key=lambda item: (item["source"], item["offset"], item["encoding"]),
        )
        target["bseq"]["occurrenceCount"] = len(target["bseq"]["matches"])
    return source_inventory, {
        "manifest": _manifest_record("bseq.jsonl", rows, raw_manifest),
        "verifiedSources": len(source_inventory),
        "sourceBytes": source_bytes_total,
    }


def write_unreferenced_wem_id_audit(root: Path = PROJECT.parent, project: Path = PROJECT) -> dict:
    """Verify local HIRC/DIDX receipts and scan every indexed BSEQ source for loose WEM IDs."""
    root = Path(root)
    project = Path(project)
    bank_evidence, verified_banks, didx_by_id = _validate_bnk_didx(root, project)
    targets, orphan_inputs = _validate_unreferenced_wems(root, project, verified_banks)
    for target in targets:
        matches = didx_by_id.get(int(target["sourceId"]), [])
        target["didx"] = {"matchCount": len(matches), "matches": matches}
    source_inventory, bseq_evidence = _scan_bseq_sources(root, project, targets)

    bseq_inputs = bseq_evidence.pop("manifest")
    report = {
        "schema": SCHEMA,
        "method": METHOD,
        "sourceVersion": "Let's Go Pikachu 1.0.2",
        "status": "ANALYZED",
        "semantics": (
            "Static identifier search only. No finding establishes whether a loose WEM is loaded, invoked, "
            "selected, or played at runtime."
        ),
        "searchEncodings": list(next(iter(targets))["bseq"]["countsByEncoding"]),
        "coverage": {
            "unreferencedWemTargets": len(targets),
            "verifiedBnkSources": len(bank_evidence["banks"]),
            "verifiedDidxRows": bank_evidence["didxRows"],
            "verifiedBseqSources": bseq_evidence["verifiedSources"],
            "bseqSourceBytes": bseq_evidence["sourceBytes"],
        },
        "inputs": {
            **bank_evidence["inputs"],
            **orphan_inputs,
            "bseq": bseq_inputs,
        },
        "banks": bank_evidence["banks"],
        "bseqSources": source_inventory,
        "targets": targets,
        "limits": [
            "The BSEQ check searches only the listed raw-byte encodings; other encodings, indirect IDs, and generated runtime IDs are outside its scope.",
            "HIRC results are taken from the hash-linked wwise_unreferenced_wem.jsonl map and its validated BNK/XML receipts.",
            "A local HIRC or DIDX match is static evidence and does not prove runtime loading or playback.",
        ],
    }
    output = project / WEM_OUTPUT
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    temporary = output.with_name(output.name + ".partial")
    temporary.write_bytes(payload)
    temporary.replace(output)

    return {
        "status": report["status"],
        "schema": SCHEMA,
        "report": WEM_OUTPUT,
        "reportBytes": len(payload),
        "reportSha256": _sha256(payload),
        "targets": len(targets),
        "targetsWithoutHircMatches": sum(target["hirc"]["matchCount"] == 0 for target in targets),
        "targetsWithoutDidxMatches": sum(target["didx"]["matchCount"] == 0 for target in targets),
        "targetsWithoutBseqByteOccurrences": sum(target["bseq"]["occurrenceCount"] == 0 for target in targets),
        "verifiedBnkSources": report["coverage"]["verifiedBnkSources"],
        "verifiedDidxRows": report["coverage"]["verifiedDidxRows"],
        "verifiedBseqSources": report["coverage"]["verifiedBseqSources"],
        "bseqSourceBytes": report["coverage"]["bseqSourceBytes"],
    }
