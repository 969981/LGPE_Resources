"""Refresh only BSEQ header metadata in manifests/files.csv from local bytes."""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from lgpe_research.core import PROJECT, ensure_inside, probe, source_dirs


def refresh(root: Path = PROJECT.parent, project: Path = PROJECT) -> dict:
    path = project / "manifests" / "files.csv"
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        fields = list(reader.fieldnames or [])
        rows = list(reader)
    bases = source_dirs(root)
    refreshed = 0
    signatures = Counter()
    for row in rows:
        if row.get("suffix", "").casefold() != ".bseq":
            continue
        partition = row["partition"]
        base = bases[partition]
        source = ensure_inside(base / Path(row["relative_path"]), base)
        details = probe(source)
        if int(row["bytes"]) != details["size"]:
            raise ValueError(f"BSEQ source size differs from scan catalog: {row['relative_path']}")
        row["signature"] = details["signature"]
        row["header_hex"] = details["header_hex"]
        refreshed += 1
        signatures[details["signature"]] += 1
    if refreshed != 381 or signatures != Counter({"SESD": 381}):
        raise ValueError(f"unexpected BSEQ header scan result: count={refreshed}, signatures={dict(signatures)}")

    temporary = path.with_name(path.name + ".partial")
    with temporary.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)

    summary_path = path.with_suffix(".summary.json")
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    refresh_record = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "suffix": ".bseq",
        "refreshed": refreshed,
        "signatures": dict(sorted(signatures.items())),
        "method": "local 64-byte probe; existing source hashes and non-BSEQ rows retained",
    }
    summary.setdefault("targeted_signature_refreshes", []).append(refresh_record)
    summary_temp = summary_path.with_name(summary_path.name + ".partial")
    summary_temp.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary_temp.replace(summary_path)
    return refresh_record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=PROJECT.parent)
    args = parser.parse_args()
    print(json.dumps(refresh(args.root), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
