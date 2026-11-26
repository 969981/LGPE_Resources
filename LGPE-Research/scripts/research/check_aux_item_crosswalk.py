#!/usr/bin/env python3
"""Verify the local LGPE 1.0.2 encounter-aux item/name evidence crosswalk."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


EXPECTED_ITEM_NAMES = {
    76: ("Super Repel", "43808a54fbe3a9996495c10ed3fe73c2446f5185e3b6f741a0a66fe90348dac0"),
    77: ("Max Repel", "e1edc249a0c259a3ea4d574a97069ca3a356939a31c604b166d1cc305d9ca0ac"),
    79: ("Repel", "f796b2727039de4dba5aff90b5df88f703550fe24352b2a493bd0c2c7cd0e613"),
    900: ("Lure", "ab2b4b29537940b5848aad63d430a9875a237db2d54870a3f2f82fdd5bc176ec"),
    901: ("Super Lure", "8b0349a4e6c4498b73eeabb5586e06e9ae38da3f0cac5904ea4f6e914b510d2d"),
    902: ("Max Lure", "06bf3b5ae3838b76805bf4d3e36abcabf5b30cdd3359a62acd24cca0fd8a965e"),
}
MESSAGE_HASHES = {
    "bin/message/English/common/itemname.dat": "9df661cc9c203e42a24f03d61d34067278fa23f4c7f2a9a2435cb05d57326f01",
    "bin/message/English/common/itemname.tbl": "a1d590c0b6a04d881d0265a229857b830e8531e3a6637460518da5e36cc79250",
}
MESSAGE_OUTPUT_SHA256 = "c0491b5a9cfb2b0676bb2b697bfeb65e72f4891e07ad40fa9b00d6dc7ab04376"
PKNX_COMMIT = "d191cd0e5c05f2af81d9a41c1f1d82e6621b351a"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def output_path(root: Path, manifest_path: str) -> Path:
    relative = Path(manifest_path.replace("\\", "/"))
    if relative.is_absolute() or ".." in relative.parts:
        raise SystemExit(f"unsafe decoded output path in manifest: {manifest_path}")
    return root / relative


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    source_root = (
        root.parent / "1.0.2/2b7730a9e56498bbafac2002d4908c6b_NCA/1"
    )
    records: dict[str, dict[str, object]] = {}
    for line in (root / "manifests/gamedata.jsonl").read_text(encoding="utf-8").splitlines():
        record = json.loads(line)
        source = record.get("source")
        if source in ("bin/message/English/common/itemname.dat", *(
            f"bin/pokelib/item/item{item_id:03}.dat" for item_id in EXPECTED_ITEM_NAMES
        )):
            if source in records:
                raise SystemExit(f"duplicate gamedata manifest source: {source}")
            records[source] = record

    for item_id, (label, expected_source_hash) in EXPECTED_ITEM_NAMES.items():
        relative_source = f"bin/pokelib/item/item{item_id:03}.dat"
        record = records.get(relative_source)
        if record is None:
            raise SystemExit(f"missing gamedata manifest row: {relative_source}")
        source = source_root / relative_source
        decoded = output_path(root, str(record.get("output", "")))
        source_hash = sha256(source)
        decoded_hash = sha256(decoded)
        payload = json.loads(decoded.read_text(encoding="utf-8"))
        if record.get("status") != "DECODED":
            raise SystemExit(f"item is not decoded: {relative_source}")
        if record.get("method") != "lgpe_research.gamedata_decode/items":
            raise SystemExit(f"unexpected item decoder: {relative_source}")
        if record.get("tool_versions", {}).get("pkNX") != PKNX_COMMIT:
            raise SystemExit(f"unexpected pkNX commit: {relative_source}")
        if source_hash != expected_source_hash or record.get("source_sha256") != source_hash:
            raise SystemExit(f"item source hash mismatch: {relative_source} ({source_hash})")
        if record.get("output_sha256") != decoded_hash:
            raise SystemExit(f"item output hash mismatch: {relative_source} ({decoded_hash})")
        if payload.get("format") != "LGPE Item" or payload.get("record_size") != 36:
            raise SystemExit(f"unexpected decoded item shape: {relative_source}")
        if bytes.fromhex(payload.get("raw_hex", "")) != source.read_bytes():
            raise SystemExit(f"decoded raw_hex differs from source bytes: {relative_source}")
        print(f"item {item_id}: {label}; source, output, raw_hex, and receipt verified")

    message_source = "bin/message/English/common/itemname.dat"
    message_record = records.get(message_source)
    if message_record is None:
        raise SystemExit(f"missing gamedata manifest row: {message_source}")
    for relative, expected_hash in MESSAGE_HASHES.items():
        actual_hash = sha256(source_root / relative)
        if actual_hash != expected_hash:
            raise SystemExit(f"message source hash mismatch: {relative} ({actual_hash})")
    if message_record.get("source_sha256") != MESSAGE_HASHES[message_source]:
        raise SystemExit("itemname.dat manifest hash mismatch")
    if message_record.get("companion") != "bin/message/English/common/itemname.tbl":
        raise SystemExit("itemname companion path mismatch")
    if message_record.get("companion_sha256") != MESSAGE_HASHES["bin/message/English/common/itemname.tbl"]:
        raise SystemExit("itemname.tbl manifest hash mismatch")
    if message_record.get("tool_versions", {}).get("pkNX") != PKNX_COMMIT:
        raise SystemExit("unexpected message pkNX commit")
    message_output = output_path(root, str(message_record.get("output", "")))
    message_output_hash = sha256(message_output)
    if message_output_hash != MESSAGE_OUTPUT_SHA256 or message_record.get("output_sha256") != message_output_hash:
        raise SystemExit(f"itemname JSON hash mismatch: {message_output_hash}")
    message = json.loads(message_output.read_text(encoding="utf-8"))
    lines = message.get("lines", [])
    if message_record.get("status") != "DECODED" or len(lines) != 1058:
        raise SystemExit("itemname decoded line count/status mismatch")
    for item_id, (label, _) in EXPECTED_ITEM_NAMES.items():
        line = lines[item_id]
        if line.get("index") != item_id or line.get("id") != f"ITEMNAME_{item_id:03}":
            raise SystemExit(f"itemname index/id mismatch: {item_id}")
        if line.get("text") != label:
            raise SystemExit(f"itemname text mismatch: {item_id} ({line.get('text')!r})")
    print(
        "itemname DAT/TBL, decoded JSON, all six indices, and manifest receipts verified; "
        f"lines={len(lines)} unpaired_labels={len(message.get('unpaired_labels', []))} "
        f"json_sha256={message_output_hash} pkNX={PKNX_COMMIT}"
    )


if __name__ == "__main__":
    main()
