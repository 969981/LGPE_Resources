#!/usr/bin/env python3
"""Verify the LGPE 1.0.2 parser lookup's English item-name cross-reference."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

SOURCE_ROOT_REL = Path("1.0.2/2b7730a9e56498bbafac2002d4908c6b_NCA/1")
SOURCE_REL = Path("bin/message/English/common/itemname.dat")
COMPANION_REL = Path("bin/message/English/common/itemname.tbl")
OUTPUT_REL = Path("decoded/1.0.2/romfs/bin/message/English/common/itemname.json")
EXPECTED_SOURCE_SHA256 = "9df661cc9c203e42a24f03d61d34067278fa23f4c7f2a9a2435cb05d57326f01"
EXPECTED_COMPANION_SHA256 = "a1d590c0b6a04d881d0265a229857b830e8531e3a6637460518da5e36cc79250"
EXPECTED_OUTPUT_SHA256 = "c0491b5a9cfb2b0676bb2b697bfeb65e72f4891e07ad40fa9b00d6dc7ab04376"
LOOKUP_VALUE = 0x36A
EXPECTED_LABEL = "Silph Scope"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    source_root = root.parent / SOURCE_ROOT_REL
    source = source_root / SOURCE_REL
    companion = source_root / COMPANION_REL
    output = root / OUTPUT_REL

    source_bytes = source.read_bytes()
    companion_bytes = companion.read_bytes()
    source_hash = sha256(source_bytes)
    companion_hash = sha256(companion_bytes)
    if source_hash != EXPECTED_SOURCE_SHA256:
        raise SystemExit(f"source hash mismatch: {source_hash}")
    if companion_hash != EXPECTED_COMPANION_SHA256:
        raise SystemExit(f"companion hash mismatch: {companion_hash}")

    sys.path.insert(0, str(root / "src"))
    try:
        from lgpe_research.gamedata_decode import message

        decoded = message(source_bytes, companion_bytes, root / "tools/src/pokedat")
    finally:
        sys.path.pop(0)
    decoded_bytes = (json.dumps(decoded, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    output_bytes = output.read_bytes()
    output_hash = sha256(output_bytes)
    if output_hash != EXPECTED_OUTPUT_SHA256:
        raise SystemExit(f"decoded output hash mismatch: {output_hash}")
    if decoded_bytes != output_bytes:
        raise SystemExit("fresh decode differs from the mirrored JSON output")

    lines = decoded.get("lines", [])
    if len(lines) <= LOOKUP_VALUE:
        raise SystemExit(f"decoded item-name table is too short: {len(lines)}")
    row = lines[LOOKUP_VALUE]
    if row.get("index") != LOOKUP_VALUE or row.get("id") != "ITEMNAME_874":
        raise SystemExit(f"unexpected item-name row identity: {row}")
    if row.get("text") != EXPECTED_LABEL:
        raise SystemExit(f"unexpected English label at 0x{LOOKUP_VALUE:x}: {row.get('text')!r}")

    receipt = None
    for line in (root / "manifests/outputs.jsonl").open(encoding="utf-8"):
        record = json.loads(line)
        if record.get("relative_source") == SOURCE_REL.as_posix() and record.get("version") == "1.0.2":
            if record.get("source_version") == "Pokemon Let's Go Pikachu 1.0.2":
                receipt = record
                break
    if receipt is None:
        raise SystemExit("missing LGPE 1.0.2 output receipt for itemname.dat")
    expected_receipt = {
        "status": "DECODED",
        "companion": COMPANION_REL.as_posix(),
        "source_sha256": source_hash,
        "companion_sha256": companion_hash,
        "output_sha256": output_hash,
    }
    for key, expected in expected_receipt.items():
        if receipt.get(key) != expected:
            raise SystemExit(f"manifest receipt {key} mismatch: {receipt.get(key)!r}")
    normalized_output = str(receipt.get("output_file", "")).replace("\\", "/")
    if not normalized_output.endswith("/" + OUTPUT_REL.as_posix()):
        raise SystemExit(f"manifest output path mismatch: {receipt.get('output_file')!r}")

    if sha256(source.read_bytes()) != source_hash or sha256(companion.read_bytes()) != companion_hash:
        raise SystemExit("original message files changed during verification")
    print(
        f"LGPE 1.0.2 lookup 0x{LOOKUP_VALUE:x} -> {row['id']} / {row['text']}; "
        "fresh DAT/TBL decode is byte-identical to mirrored JSON; source, companion, "
        "output hashes and manifest receipt verified. Gameplay semantics remain unproven."
    )
    print(
        f"DAT={source_hash} TBL={companion_hash} JSON={output_hash} "
        f"method={receipt.get('method')} count={receipt.get('count')}"
    )


if __name__ == "__main__":
    main()
