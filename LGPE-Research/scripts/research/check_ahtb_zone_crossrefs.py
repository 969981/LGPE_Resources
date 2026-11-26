#!/usr/bin/env python3
"""Verify unpaired AHTB decodes and exact-build encounter hash cross-references."""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path, PurePosixPath
import sys


SOURCE_ROOT = Path("1.0.2/2b7730a9e56498bbafac2002d4908c6b_NCA")
MAIN_SHA256 = "1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8"
ZONE_TABLE = "bin/field/param/placement/table/ZoneNameHashTable.tbl"
ZONE_SHA256 = "2c314dec7348010523a6f695319d83a136b4f4b7c058666bf3f09c91a82912fe"
EXPECTED_HASH_LABELS = {
    0x97DEB1F2D0A83282: (134, "t005r0305"),
    0x194D955FBF0A7685: (255, "gogo_park01"),
    0xD8652AB502B422C7: (256, "gogo_play01"),
}
FNV64_OFFSET = 0xCBF29CE484222645
FNV64_PRIME = 0x100000001B3


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    source_root = root.parent / SOURCE_ROOT / "1"
    main_path = root.parent / SOURCE_ROOT / "0/main"
    main_hash = sha256(main_path.read_bytes())
    if main_hash != MAIN_SHA256:
        raise SystemExit(f"wrong ExeFS main build: {main_hash}")

    sys.path.insert(0, str(root / "src"))
    try:
        from lgpe_research.gamedata_decode import tbl_labels
    finally:
        sys.path.pop(0)

    with (root / "manifests/files.csv").open(encoding="utf-8-sig", newline="") as stream:
        scan_rows = list(csv.DictReader(stream))
    romfs_names = {
        row["relative_path"].casefold()
        for row in scan_rows if row["partition"].casefold() == "romfs"
    }
    ahtb_sources = []
    for row in scan_rows:
        if row["partition"].casefold() != "romfs" or row["suffix"].lower() != ".tbl":
            continue
        if row["signature"] != "AHTB":
            continue
        paired_dat = PurePosixPath(row["relative_path"]).with_suffix(".dat").as_posix()
        if paired_dat.casefold() not in romfs_names:
            ahtb_sources.append(row["relative_path"])
    ahtb_sources.sort(key=str.casefold)
    if len(ahtb_sources) != 15:
        raise SystemExit(f"unpaired AHTB inventory changed: {len(ahtb_sources)}")

    game_records = {}
    for line in (root / "manifests/gamedata.jsonl").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        if record.get("source") in ahtb_sources:
            source = record["source"]
            if source in game_records:
                raise SystemExit(f"duplicate game-data record: {source}")
            game_records[source] = record
    output_receipts = {}
    for line in (root / "manifests/outputs.jsonl").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        receipt = json.loads(line)
        if receipt.get("relative_source") in ahtb_sources and receipt.get("version") == "1.0.2":
            output_receipts[receipt["relative_source"]] = receipt

    for relative in ahtb_sources:
        record = game_records.get(relative)
        receipt = output_receipts.get(relative)
        if not record or record.get("status") != "DECODED":
            raise SystemExit(f"missing DECODED game-data record: {relative}")
        if record.get("method") != "lgpe_research.gamedata_decode/tbl_labels":
            raise SystemExit(f"unexpected method for {relative}: {record.get('method')}")
        source = source_root.joinpath(*PurePosixPath(relative).parts)
        source_bytes = source.read_bytes()
        source_hash = sha256(source_bytes)
        value = tbl_labels(source_bytes)
        output_relative = PurePosixPath("decoded/1.0.2/romfs") / PurePosixPath(relative).with_suffix(".json")
        output = root.joinpath(*output_relative.parts)
        expected_payload = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        output_bytes = output.read_bytes()
        output_hash = sha256(output_bytes)
        if output_bytes != expected_payload:
            raise SystemExit(f"fresh parse differs from mirrored output: {relative}")
        if record.get("source_sha256") != source_hash or record.get("output_sha256") != output_hash:
            raise SystemExit(f"game-data hash mismatch: {relative}")
        if record.get("count") != value["entry_count"] or record.get("record_format") != value["format"]:
            raise SystemExit(f"game-data shape receipt mismatch: {relative}")
        if record.get("output") != output_relative.as_posix():
            raise SystemExit(f"path mapping mismatch: {relative} -> {record.get('output')}")
        if not receipt:
            raise SystemExit(f"missing 1.0.2 output receipt: {relative}")
        if receipt.get("status") != "DECODED" or receipt.get("method") != record["method"]:
            raise SystemExit(f"output receipt method/status mismatch: {relative}")
        if Path(receipt.get("output_file", "")).resolve() != output.resolve():
            raise SystemExit(f"output receipt path mismatch: {relative}")
        for key, expected in (("source_sha256", source_hash), ("output_sha256", output_hash)):
            if receipt.get(key) != expected:
                raise SystemExit(f"receipt {key} mismatch: {relative}")

    zone_bytes = (source_root / ZONE_TABLE).read_bytes()
    if sha256(zone_bytes) != ZONE_SHA256:
        raise SystemExit("ZoneNameHashTable source SHA-256 mismatch")
    zone_output = root / "decoded/1.0.2/romfs/bin/field/param/placement/table/ZoneNameHashTable.json"
    zone = json.loads(zone_output.read_text(encoding="utf-8"))
    entries = zone.get("entries", [])
    if len(entries) != 257 or zone.get("entry_count") != 257:
        raise SystemExit(f"unexpected ZoneNameHashTable entry count: {len(entries)}")
    fnv_by_table = []
    asset_table = "bin/message/asset.tbl"
    for relative in ahtb_sources:
        source_bytes = source_root.joinpath(*PurePosixPath(relative).parts).read_bytes()
        table = tbl_labels(source_bytes)
        matched = 0
        for entry in table["entries"]:
            label = bytes.fromhex(entry["raw_label_hex"]).rstrip(b"\0")
            value = FNV64_OFFSET
            for byte in label:
                value = ((value ^ byte) * FNV64_PRIME) & 0xFFFFFFFFFFFFFFFF
            if value == int(entry["hash"], 16):
                matched += 1
        expected_matches = 0 if relative == asset_table else table["entry_count"]
        if matched != expected_matches:
            raise SystemExit(
                f"unexpected FNV-1a result for {relative}: "
                f"{matched}/{table['entry_count']} (expected {expected_matches})"
            )
        fnv_by_table.append({
            "source": relative,
            "entries": table["entry_count"],
            "fnv1a_matches": matched,
            "fnv1a_nonmatches": table["entry_count"] - matched,
        })

    crossrefs = []
    by_hash = {int(entry["hash"], 16): entry for entry in entries}
    for value, (index, label) in EXPECTED_HASH_LABELS.items():
        entry = by_hash.get(value)
        if not entry or (entry["index"], entry["label"]) != (index, label):
            raise SystemExit(f"hash cross-reference mismatch for {value:016x}: {entry}")
        crossrefs.append({"hash": f"{value:016x}", "index": index, "label": label})

    print(json.dumps({
        "main_sha256": main_hash,
        "zone_source_sha256": ZONE_SHA256,
        "unpaired_ahtb_decoded": len(ahtb_sources),
        "zone_table_entries": len(entries),
        "fnv1a_verified_rows": sum(row["fnv1a_matches"] for row in fnv_by_table),
        "fnv1a_nonmatches": sum(row["fnv1a_nonmatches"] for row in fnv_by_table),
        "fnv1a_by_table": fnv_by_table,
        "hash_crossrefs": crossrefs,
        "runtime_semantics": "unverified; label/hash and exact-build static references only",
    }, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
