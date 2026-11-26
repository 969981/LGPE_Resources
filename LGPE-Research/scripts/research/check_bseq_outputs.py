"""Audit every BSEQ JSON against its exact LGPE 1.0.2 source and receipt."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path, PurePosixPath

from lgpe_research.bseq_decode import PBSEQTOOL_COMMIT, SCHEMA
from lgpe_research.core import PROJECT, VERSION, source_dirs


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def audit(root: Path = PROJECT.parent, project: Path = PROJECT) -> dict:
    manifest = project / "manifests" / "bseq.jsonl"
    rows = [json.loads(line) for line in manifest.read_text(encoding="utf-8").splitlines() if line.strip()]
    expected_file = project / "docs/research/source_lists/t09-bseq-381.txt"
    expected = {
        line.strip().replace("\\", "/").casefold()
        for line in expected_file.read_text(encoding="utf-8-sig").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    indexed = {str(row.get("source", "")).replace("\\", "/").casefold(): row for row in rows}
    if set(indexed) != expected:
        raise ValueError(f"manifest/source-list mismatch: missing={len(expected - set(indexed))}, extra={len(set(indexed) - expected)}")
    with (project / "manifests" / "files.csv").open(encoding="utf-8-sig", newline="") as stream:
        scan_rows = {
            row["relative_path"].replace("\\", "/").casefold(): row
            for row in csv.DictReader(stream)
            if row["partition"].casefold() == "romfs" and row["suffix"].casefold() == ".bseq"
        }
    if set(scan_rows) != expected:
        raise ValueError("BSEQ source list and files.csv scan catalog differ")

    romfs = source_dirs(root)["romfs"]
    exactness = Counter()
    commands = groups = decoded_source_bytes = all_source_bytes = total_json_bytes = 0
    unsupported = []
    for rel_key, row in indexed.items():
        rel = PurePosixPath(row["source"].replace("\\", "/"))
        source = romfs.joinpath(*rel.parts)
        source_bytes = source.read_bytes()
        source_hash = hashlib.sha256(source_bytes).hexdigest()
        if source_bytes[:4] != b"SESD" or int.from_bytes(source_bytes[4:8], "little") != 3:
            raise ValueError(f"source failed the SESD v3 signature/version gate: {rel}")
        scan_row = scan_rows[rel_key]
        if scan_row["signature"] != "SESD" or scan_row["header_hex"] != source_bytes[:16].hex():
            raise ValueError(f"files.csv signature/header differs from source: {rel}")
        if len(source_bytes) != int(row.get("source_bytes", -1)):
            raise ValueError(f"source size differs from BSEQ manifest: {rel}")
        if source_hash != row.get("source_sha256"):
            raise ValueError(f"source hash differs from BSEQ manifest: {rel}")
        all_source_bytes += len(source_bytes)
        if row["status"] == "UNSUPPORTED":
            if not rel.as_posix().casefold().startswith("bin/demo/sequence/"):
                raise ValueError(f"unexpected unsupported BSEQ path: {rel}")
            output = project / row.get("output", "")
            if not row.get("parser_error") or output.is_file():
                raise ValueError(f"unsupported row lacks parser error or emitted an output: {rel}")
            unsupported.append(row)
            continue
        if row["status"] not in {"DECODED", "DECODED_EXISTING_VERIFIED"}:
            raise ValueError(f"unexpected final BSEQ status for {rel}: {row['status']}")
        output = project / row["output"]
        expected_output = project / "decoded" / VERSION / "romfs" / Path(*rel.with_suffix(".json").parts)
        if output != expected_output:
            raise ValueError(f"decoded output path does not mirror the source: {rel}")
        if sha256(output) != row.get("output_sha256"):
            raise ValueError(f"output hash differs from BSEQ manifest: {rel}")
        payload = json.loads(output.read_text(encoding="utf-8"))
        if payload.get("schema") != SCHEMA or payload.get("decoder", {}).get("commit") != PBSEQTOOL_COMMIT:
            raise ValueError(f"decoder schema/revision mismatch: {rel}")
        source_doc = payload.get("source", {})
        if source_doc.get("raw_hex") != source_bytes.hex():
            raise ValueError(f"embedded raw bytes differ from source: {rel}")
        if source_doc.get("sha256") != source_hash or source_doc.get("size") != len(source_bytes):
            raise ValueError(f"embedded source metadata mismatch: {rel}")
        validation = payload.get("validation", {})
        if validation.get("semantic_roundtrip_equal") is not True:
            raise ValueError(f"semantic serialize/reparse check did not pass: {rel}")
        exactness["byte_exact" if validation.get("byte_roundtrip_exact") else "normalized"] += 1
        groups += int(validation.get("group_count", 0))
        commands += int(validation.get("command_count", 0))
        decoded_source_bytes += len(source_bytes)
        total_json_bytes += output.stat().st_size

    if len(rows) != len(expected):
        raise ValueError(f"duplicate source rows: {len(rows)} rows for {len(expected)} paths")
    return {
        "source_count": len(expected),
        "scan_catalog_signature": "SESD" if all(row["signature"] == "SESD" for row in scan_rows.values()) else "MIXED",
        "decoded": sum(exactness.values()),
        "unsupported": len(unsupported),
        "failed": sum(row.get("status") == "FAILED" for row in rows),
        "byte_exact_roundtrips": exactness["byte_exact"],
        "normalized_byte_roundtrips": exactness["normalized"],
        "semantic_roundtrips_equal": exactness["byte_exact"] + exactness["normalized"],
        "groups": groups,
        "commands": commands,
        "all_source_bytes": all_source_bytes,
        "decoded_source_bytes": decoded_source_bytes,
        "json_bytes": total_json_bytes,
        "unsupported_parser_errors": dict(sorted(Counter(row["parser_error"] for row in unsupported).items())),
        "manifest": str(manifest),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=PROJECT.parent)
    args = parser.parse_args()
    print(json.dumps(audit(args.root), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
