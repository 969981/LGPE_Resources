#!/usr/bin/env python3
"""Cross-reference literal AHTB asset labels against the scanned LGPE RomFS."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path, PurePosixPath

from lgpe_research.asset_tbl_xref import cross_reference_asset_paths
from lgpe_research.core import NCA, PROJECT, VERSION
from lgpe_research.gamedata_decode import tbl_labels

SOURCE_RELATIVE = "bin/message/asset.tbl"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def run(project: Path = PROJECT, game_root: Path = PROJECT.parent) -> dict:
    project = project.expanduser().resolve()
    game_root = game_root.expanduser().resolve()
    source_root = game_root / VERSION / NCA / "1"
    source = source_root.joinpath(*PurePosixPath(SOURCE_RELATIVE).parts)
    raw = source.read_bytes()
    source_hash = sha256(raw)
    table = tbl_labels(raw)

    inventory_path = project / "manifests" / "files.csv"
    with inventory_path.open("r", encoding="utf-8-sig", newline="") as stream:
        inventory = list(csv.DictReader(stream))
    romfs_paths = {
        row["relative_path"] for row in inventory
        if row["partition"].casefold() == "romfs"
    }
    matches = cross_reference_asset_paths(table["entries"], romfs_paths)

    game_data_rows = []
    for line in (project / "manifests" / "gamedata.jsonl").open(encoding="utf-8"):
        if line.strip():
            row = json.loads(line)
            if row.get("source") == SOURCE_RELATIVE:
                game_data_rows.append(row)
    if len(game_data_rows) != 1:
        raise ValueError(f"expected one game-data row for {SOURCE_RELATIVE}, found {len(game_data_rows)}")
    game_data = game_data_rows[0]
    output = project / game_data["output"]
    output_bytes = output.read_bytes()
    output_hash = sha256(output_bytes)
    expected_output = (json.dumps(table, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    if game_data.get("status") != "DECODED":
        raise ValueError(f"existing game-data row is not DECODED: {game_data.get('status')}")
    if game_data.get("source_sha256") != source_hash or game_data.get("output_sha256") != output_hash:
        raise ValueError("source/output hashes differ from the game-data manifest")
    if output_bytes != expected_output:
        raise ValueError("existing JSON does not reproduce from the exact source AHTB bytes")

    status_counts = Counter(row["path_status"] for row in matches)
    paired_table_count = sum(row["same_stem_tbl_present"] for row in matches)
    by_language: dict[str, dict[str, int]] = {}
    by_folder: dict[str, dict[str, int]] = {}
    for row in matches:
        parts = PurePosixPath(row["relative_source_candidate"] or "").parts
        language = parts[2] if len(parts) > 2 else "INVALID"
        folder = parts[3] if len(parts) > 3 else "INVALID"
        for aggregate, key in ((by_language, language), (by_folder, folder)):
            counts = aggregate.setdefault(key, {"entries": 0, "exact": 0, "casefold": 0, "unmatched": 0, "invalid": 0, "ambiguous": 0})
            counts["entries"] += 1
            status = row["path_status"]
            if status == "MATCH_EXACT":
                counts["exact"] += 1
            elif status == "MATCH_CASEFOLD":
                counts["casefold"] += 1
            elif status == "NO_MATCH":
                counts["unmatched"] += 1
            elif status == "INVALID_LABEL_PATH":
                counts["invalid"] += 1
            elif status == "AMBIGUOUS_CASEFOLD_MATCH":
                counts["ambiguous"] += 1

    return {
        "source_version": "Pokemon Let's Go Pikachu 1.0.2",
        "method": "literal bin/message/<AHTB label> string match against manifests/files.csv RomFS paths",
        "interpretation_limit": "path matches only; no AHTB hash algorithm, loader behavior, or grammar meaning is assigned",
        "source": {
            "relative_path": SOURCE_RELATIVE,
            "bytes": len(raw),
            "sha256": source_hash,
            "unchanged_after_check": sha256(source.read_bytes()) == source_hash,
        },
        "inventory": {
            "path": "manifests/files.csv",
            "sha256": sha256((project / "manifests" / "files.csv").read_bytes()),
            "romfs_paths": len(romfs_paths),
        },
        "decoded_output": {
            "path": game_data["output"],
            "bytes": len(output_bytes),
            "sha256": output_hash,
            "exact_reproduction": output_bytes == expected_output,
        },
        "entry_count": table["entry_count"],
        "unique_labels": len({row["label"] for row in matches}),
        "path_status_counts": dict(sorted(status_counts.items())),
        "exact_same_stem_tbl_paths": paired_table_count,
        "by_language": by_language,
        "by_folder": by_folder,
        "entries": matches,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=PROJECT.parent, help="parent of the 1.0.2 game folder")
    parser.add_argument("--output", type=Path, default=PROJECT / "work" / "asset-tbl-path-xref.json")
    args = parser.parse_args()
    report = run(PROJECT, args.root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    args.output.write_text(encoded, encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "entries"}, ensure_ascii=False, sort_keys=True))
    print(f"full_report={args.output}")


if __name__ == "__main__":
    main()
