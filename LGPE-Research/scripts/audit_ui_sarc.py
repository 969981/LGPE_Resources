"""Audit loose SARC UI containers and their byte-exact mirrored outputs."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from lgpe_research.archive_reader import read_sarc, extract

PROJECT = Path(__file__).resolve().parents[1]
SOURCE = PROJECT.parent / "1.0.2/2b7730a9e56498bbafac2002d4908c6b_NCA/1"
OUTPUT = PROJECT / "decoded/1.0.2/romfs"


def audit(source_root: Path, output_root: Path, restore_missing: bool = False):
    source_root = source_root.resolve(strict=True)
    output_root = output_root.resolve()
    if output_root.is_relative_to(source_root) or source_root.is_relative_to(output_root):
        raise ValueError("source and output roots must be disjoint")
    files = sorted((source_root / "bin/app").rglob("*.arc"))
    if not files:
        raise ValueError("no UI ARC candidates found")
    for source in files:
        relative = source.relative_to(source_root).as_posix()
        row = {"source": relative, "members": []}
        try:
            source.resolve(strict=True).relative_to(source_root)
            data = source.read_bytes()
            row["source_sha256"] = hashlib.sha256(data).hexdigest()
            members = list(read_sarc(data))
            if len({m["internal_path"].casefold() for m, _ in members}) != len(members):
                raise ValueError("duplicate member path")
            target = (output_root / (relative + ".contents")).resolve()
            if not target.is_relative_to(output_root):
                raise ValueError("target escapes output root")
            if restore_missing:
                # Existing extractor refuses conflicts and never overwrites.
                extract(source, source_root, output_root, execute=True)
            for meta, payload in members:
                path = target / meta["internal_path"]
                if not path.resolve().is_relative_to(target):
                    raise ValueError("member escapes container")
                state = ("MATCH" if path.read_bytes() == payload else "DIFFERENT") if path.is_file() else "MISSING"
                row["members"].append({**meta, "magic_hex": payload[:8].hex(),
                    "is_bntx": payload.startswith(b"BNTX"), "state": state})
            row["status"] = "MATCH" if all(m["state"] == "MATCH" for m in row["members"]) else "INCOMPLETE"
        except (OSError, ValueError, NotImplementedError) as error:
            row.update(status="FAILED", error=f"{type(error).__name__}: {error}")
        yield row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=SOURCE)
    parser.add_argument("--output-root", type=Path, default=OUTPUT)
    parser.add_argument("--restore-missing", action="store_true")
    args = parser.parse_args()
    # Keep report outside immutable input and production receipt files.
    report = PROJECT / "work/ui-sarc-audit.jsonl"
    report.parent.mkdir(parents=True, exist_ok=True)
    rows = list(audit(args.source_root, args.output_root, args.restore_missing))
    with report.open("w", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")
    members = [m for row in rows for m in row["members"]]
    summary = {"archives": len(rows), "matched_archives": sum(r["status"] == "MATCH" for r in rows),
               "members": len(members), "matched_members": sum(m["state"] == "MATCH" for m in members),
               "nested_bntx": sum(m["is_bntx"] for m in members), "report": str(report)}
    print(json.dumps(summary, ensure_ascii=False))
    return int(any(r["status"] != "MATCH" for r in rows))


if __name__ == "__main__":
    raise SystemExit(main())
