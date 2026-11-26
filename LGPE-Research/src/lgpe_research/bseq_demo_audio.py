"""Bounded raw demo BSEQ literal candidates joined to verified Wwise v128 events.

This does not parse demo command records or change any decoder receipts.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
import struct

from .bseq_wwise_map import _jsonl, _safe_decoded, _safe_source, fnv1_32
from .core import PROJECT, VERSION, sha256, source_dirs

SCHEMA = "lgpe-research.demo-bseq-audio-candidates.v1"
SEMANTICS = (
    "UNKNOWN: raw literal/FNV-1/HIRC ID correspondence only. Demo command boundaries, "
    "command meanings, adjacent numeric fields, bank loading, event invocation, timing, "
    "runtime selection and audible playback remain unverified."
)
# Only standalone ASCII identifier candidates terminated within a 32-byte window.
# The zero padding is retained as evidence, not interpreted as a command schema.
LITERAL = re.compile(rb"(?<![\x20-\x7e])(?:Play_|Stop_)[A-Za-z0-9_]{1,26}\x00")


def extract_candidates(data: bytes) -> list[dict]:
    if len(data) < 20 or data[:8] != b"SESD\x03\0\0\0":
        raise ValueError("demo input is not SESD version 3")
    if data[-4:] != b"\xff" * 4:
        raise ValueError("demo input lacks final FFFFFFFF marker")
    result = []
    for match in LITERAL.finditer(data, 16):
        offset = match.start()
        literal = match.group()[:-1].decode("ascii")
        window = data[offset:offset + 32]
        # Do not accept a truncated or nonzero-padded candidate window.
        if len(window) != 32 or window[len(literal):] != bytes(32 - len(literal)):
            continue
        result.append({
            "literalOffset": offset, "literalBytes": len(literal),
            "literal": literal, "nulOffset": offset + len(literal),
            "window32Hex": window.hex(),
            "preceding16Offset": offset - 16,
            "preceding16Hex": data[offset - 16:offset].hex(),
            "preceding2Hex": data[offset - 2:offset].hex(),
            "eventIdFNV1_32": fnv1_32(literal),
        })
    return result


def parse_hirc_events(data: bytes) -> dict:
    """Bound Wwise v128 chunks/objects and read type-4 event action IDs directly."""
    chunks = {}
    offset = 0
    while offset < len(data):
        if offset + 8 > len(data):
            raise ValueError("truncated BNK chunk header")
        tag = data[offset:offset + 4]
        size = struct.unpack_from("<I", data, offset + 4)[0]
        end = offset + 8 + size
        if end > len(data) or tag in chunks:
            raise ValueError("out-of-bounds or duplicate BNK chunk")
        chunks[tag] = (offset + 8, end)
        offset = end
    if not data.startswith(b"BKHD") or b"BKHD" not in chunks:
        raise ValueError("BNK does not start with BKHD")
    start, end = chunks[b"BKHD"]
    if end - start < 8:
        raise ValueError("short BKHD")
    version, bank_id = struct.unpack_from("<II", data, start)
    if version != 128:
        raise ValueError(f"unverified Wwise version: {version}")
    events = {}
    if b"HIRC" not in chunks:
        return {"bankId": bank_id, "events": events, "chunks": chunks}
    start, end = chunks[b"HIRC"]
    if end - start < 4:
        raise ValueError("short HIRC count")
    count = struct.unpack_from("<I", data, start)[0]
    cursor = start + 4
    seen = set()
    for ordinal in range(count):
        if cursor + 9 > end:
            raise ValueError("truncated HIRC object")
        kind = data[cursor]
        size, object_id = struct.unpack_from("<II", data, cursor + 1)
        object_end = cursor + 5 + size
        if size < 4 or object_end > end or object_id in seen:
            raise ValueError("invalid HIRC object bounds or duplicate ID")
        seen.add(object_id)
        if kind == 4:
            if size < 5:
                raise ValueError("short type-4 event")
            action_count = data[cursor + 9]
            if size != 5 + 4 * action_count:
                raise ValueError("unverified v128 event action layout")
            events[object_id] = {
                "hircType": 4, "hircObjectIndex": ordinal,
                "hircObjectOffset": cursor, "hircObjectSize": 5 + size,
                "eventIdOffset": cursor + 5, "eventId": object_id,
                "actions": [{"offset": cursor + 10 + 4 * i,
                             "id": struct.unpack_from("<I", data, cursor + 10 + 4 * i)[0]}
                            for i in range(action_count)],
            }
        cursor = object_end
    if cursor != end:
        raise ValueError("HIRC object count does not consume chunk")
    return {"bankId": bank_id, "events": events, "chunks": chunks}


def _raw_id(data: bytes, field: dict, expected: str) -> None:
    offset = field.get("offset")
    if not isinstance(offset, int) or offset < 0 or offset + 4 > len(data):
        raise ValueError("unbounded Wwise map ID field")
    if struct.unpack_from("<I", data, offset)[0] != int(expected):
        raise ValueError(f"Wwise map ID field mismatch at {offset:#x}")


def analyze_demo_audio(root: Path = PROJECT.parent, project: Path = PROJECT) -> dict:
    romfs = source_dirs(root)["romfs"]
    source_manifest = project / "manifests/bseq.jsonl"
    bank_manifest = project / "manifests/bnk.jsonl"
    map_manifest = project / "manifests/wwise_event_media.jsonl"
    inputs = _jsonl(source_manifest)
    selected = [x for x in inputs if x.get("status") == "UNSUPPORTED"
                and str(x.get("source", "")).replace("\\", "/").startswith("bin/demo/sequence/")]
    if not selected:
        raise ValueError("no UNSUPPORTED demo BSEQ source receipts")
    banks, by_id = {}, defaultdict(list)
    for row in _jsonl(bank_manifest):
        if row.get("status") not in {"DECODED", "DECODED_EXISTING_VERIFIED"}:
            continue
        source = _safe_source(row["source"]).as_posix()
        if source in banks:
            raise ValueError(f"duplicate bank receipt: {source}")
        data = (romfs / source).read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        if digest != row["source_sha256"]:
            raise ValueError(f"BNK source hash mismatch: {source}")
        parsed = parse_hirc_events(data)
        bank = {"bankSource": source, "bankSourceSha256": digest,
                "bankId": parsed["bankId"], "bankXml": row["output"].replace("\\", "/"),
                "bankXmlSha256": row["output_sha256"]}
        banks[source] = bank
        for event_id, event in parsed["events"].items():
            by_id[event_id].append({**bank, **event})
    if not banks:
        raise ValueError("no verified local banks")
    action_rows = defaultdict(list)
    for row in _jsonl(map_manifest):
        action_rows[(row["bankSource"], int(row["eventId"]))].append(row)
    verified_banks, verified_media, bank_cache = set(), set(), {}

    def read_bank(source):
        if source not in bank_cache:
            data = (romfs / source).read_bytes()
            if hashlib.sha256(data).hexdigest() != banks[source]["bankSourceSha256"]:
                raise ValueError(f"BNK changed during mapping: {source}")
            bank_cache[source] = (data, parse_hirc_events(data))
        return bank_cache[source]

    def verify_links(candidate):
        source = candidate["bankSource"]
        bank = banks[source]
        data, _ = read_bank(source)
        if source not in verified_banks:
            if sha256(_safe_decoded(project, bank["bankXml"])) != bank["bankXmlSha256"]:
                raise ValueError(f"BNK XML hash mismatch: {source}")
            verified_banks.add(source)
        links = action_rows[(source, candidate["eventId"])]
        expected_actions = {(x["offset"], str(x["id"])) for x in candidate["actions"]}
        if {(x.get("eventActionOffset"), x.get("actionId")) for x in links
            if x.get("actionId") is not None} != expected_actions:
            raise ValueError("raw HIRC event/action IDs disagree with Wwise map")
        for row in links:
            if (row["bankSourceSha256"] != bank["bankSourceSha256"]
                    or row["bankXmlSha256"] != bank["bankXmlSha256"]):
                raise ValueError("stale Wwise map hashes")
            if row.get("actionId") is not None:
                _raw_id(data, row["eventActionRef"]["field"], row["actionId"])
            if row.get("actionTargetRef") and row.get("actionBankId") == str(bank["bankId"]):
                _raw_id(data, row["actionTargetRef"]["field"], row["actionTargetRef"]["targetId"])
            for media in row.get("mediaReferences", []):
                # Cross-bank graph links remain attributed to the existing static map.
                if media.get("sourceBankId") == str(bank["bankId"]):
                    _raw_id(data, media["sourceIdField"], media["sourceId"])
                internal = media.get("bankMedia")
                loose = media.get("wem")
                if internal:
                    key = (internal["bankSource"], internal["output"])
                    if key not in verified_media:
                        owner = banks.get(internal["bankSource"])
                        if not owner or owner["bankSourceSha256"] != internal["bankSourceSha256"]:
                            raise ValueError("internal media bank hash mismatch")
                        owner_data, parsed = read_bank(internal["bankSource"])
                        ds, de = parsed["chunks"][b"DATA"]
                        ix, ie = parsed["chunks"][b"DIDX"]
                        record = ix + 12 * internal["containerIndex"]
                        if record + 12 > ie:
                            raise ValueError("internal media index exceeds DIDX")
                        mid, off, size = struct.unpack_from("<III", owner_data, record)
                        if (mid, off, size) != (int(media["sourceId"]), internal["dataOffset"], internal["sizeBytes"]) or ds + off + size > de:
                            raise ValueError("internal media DIDX mismatch")
                        payload = owner_data[ds + off:ds + off + size]
                        if hashlib.sha256(payload).hexdigest() != internal["outputSha256"]:
                            raise ValueError("internal media DATA hash mismatch")
                        if sha256(_safe_decoded(project, internal["output"])) != internal["outputSha256"]:
                            raise ValueError("internal WEM output hash mismatch")
                        if internal.get("wavOutput") and sha256(_safe_decoded(project, internal["wavOutput"])) != internal["wavOutputSha256"]:
                            raise ValueError("internal WAV hash mismatch")
                        verified_media.add(key)
                if loose:
                    key = ("loose", loose["source"])
                    if key not in verified_media:
                        if sha256(romfs / _safe_source(loose["source"])) != loose["sourceSha256"]:
                            raise ValueError("loose WEM hash mismatch")
                        if sha256(_safe_decoded(project, loose["wav"])) != loose["wavSha256"]:
                            raise ValueError("loose WAV hash mismatch")
                        verified_media.add(key)
        return links

    sources, occurrences, prefixes, unique = [], Counter(), Counter(), set()
    seen_sources, link_cache = set(), {}
    for row in sorted(selected, key=lambda x: x["source"]):
        source = _safe_source(row["source"]).as_posix()
        if source in seen_sources:
            raise ValueError(f"duplicate demo source: {source}")
        seen_sources.add(source)
        data = (romfs / source).read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        if digest != row["source_sha256"]:
            raise ValueError(f"BSEQ source hash mismatch: {source}")
        literals = extract_candidates(data)
        for literal in literals:
            candidates = []
            for event in by_id[literal["eventIdFNV1_32"]]:
                key = (event["bankSource"], event["eventId"])
                if key not in link_cache:
                    link_cache[key] = verify_links(event)
                candidates.append({**event, "eventActionRows": link_cache[key]})
            literal["bankCandidates"] = candidates
            literal["status"] = "STATIC_ID_CANDIDATE" if candidates else "NO_LOCAL_TYPE4_ID_MATCH"
            occurrences[literal["status"]] += 1
            prefixes[literal["preceding2Hex"]] += 1
            unique.add(literal["literal"])
        sources.append({"source": source, "sourceBytes": len(data), "sourceSha256": digest,
                        "sourceDecoderStatus": "UNSUPPORTED", "parserError": row.get("parser_error"),
                        "status": "RAW_LITERAL_CANDIDATES" if literals else "NO_PREFIX_LITERAL_CANDIDATE",
                        "candidateCount": len(literals), "candidates": literals})
    return {
        "schema": SCHEMA, "sourceVersion": VERSION, "semanticsStatus": "UNKNOWN",
        "semantics": SEMANTICS, "method": "BOUNDED_RAW_LITERAL_FNV1_TO_RAW_HIRC_TYPE4",
        "candidateRule": "standalone ASCII Play_/Stop_ identifier, NUL terminated and zero padded within 32 bytes; no demo command parser",
        "hashAlgorithm": "lowercase UTF-8 FNV-1 32-bit (pinned wwiser method)",
        "inputManifestSha256": {f.name: sha256(f) for f in (source_manifest, bank_manifest, map_manifest)},
        "summary": {"sources": len(sources), "sourceBytes": sum(x["sourceBytes"] for x in sources),
                    "sourcesWithoutCandidates": sum(not x["candidates"] for x in sources),
                    "literalOccurrences": sum(occurrences.values()), "distinctLiterals": len(unique),
                    "statuses": dict(occurrences), "preceding2HexCounts": dict(prefixes),
                    "rawBanksVerified": len(banks), "linkedBankXmlsVerified": len(verified_banks),
                    "mediaReceiptsVerified": len(verified_media)},
        "sources": sources,
    }


def write_demo_audio_report(root: Path = PROJECT.parent, project: Path = PROJECT,
                            dry_run: bool = False) -> dict:
    report = analyze_demo_audio(root, project)
    output = project / "manifests/bseq_demo_audio_candidates.json"
    payload = (json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    if not dry_run:
        output.parent.mkdir(parents=True, exist_ok=True)
        temporary = output.with_suffix(".json.partial")
        if temporary.exists():
            raise FileExistsError(f"stale partial report: {temporary}")
        temporary.write_bytes(payload)
        temporary.replace(output)
    return {"status": "DRY_RUN" if dry_run else "ANALYZED", **report["summary"],
            "output": str(output), "outputBytes": len(payload),
            "outputSha256": hashlib.sha256(payload).hexdigest(), "semanticsStatus": "UNKNOWN"}
