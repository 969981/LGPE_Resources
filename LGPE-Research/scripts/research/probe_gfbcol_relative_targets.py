#!/usr/bin/env python3
"""Probe GFBCol root slots as untyped forward-relative targets."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path, PurePosixPath

from lgpe_research.core import NCA, PROJECT, VERSION, ensure_inside
from lgpe_research.flatbuffer_probe import probe_relative_targets


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def run(project: Path = PROJECT, game_root: Path = PROJECT.parent) -> dict:
    project = project.expanduser().resolve()
    game_root = game_root.expanduser().resolve()
    romfs = game_root / VERSION / NCA / "1"
    inventory = project / "manifests" / "files.csv"
    catalog_bytes = inventory.read_bytes()
    with inventory.open("r", encoding="utf-8-sig", newline="") as stream:
        candidates = [
            row for row in csv.DictReader(stream)
            if row["partition"].casefold() == "romfs"
            and row["suffix"].casefold() == ".gfbcol"
        ]

    entries = []
    slot_counts: dict[int, Counter] = {}
    for item in sorted(candidates, key=lambda row: row["relative_path"].casefold()):
        relative = PurePosixPath(item["relative_path"])
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"unsafe catalog path: {relative}")
        expected = romfs.joinpath(*relative.parts)
        source = ensure_inside(expected, romfs)
        if source != expected:
            raise ValueError(f"source path resolves through a symlink: {expected}")
        raw = source.read_bytes()
        if len(raw) != int(item["bytes"]):
            raise ValueError(f"catalog size mismatch for {relative}")
        probe = probe_relative_targets(raw)
        for slot in probe["slots"]:
            if slot["present"]:
                slot_counts.setdefault(slot["slot_index"], Counter())[
                    slot.get("candidate_u32_at_target", "OUT_OF_BOUNDS")
                ] += 1
        entries.append({
            "source": relative.as_posix(),
            "source_bytes": len(raw),
            "source_sha256": sha256_bytes(raw),
            **probe,
        })

    slot_summary = {}
    slot_total = max((len(row["slots"]) for row in entries), default=0)
    for index in range(slot_total):
        selected = [
            row["slots"][index] for row in entries
            if index < len(row["slots"]) and row["slots"][index]["present"]
        ]
        slot_summary[str(index)] = {
            "present": len(selected),
            "targets_in_bounds": sum(row["target_in_bounds"] for row in selected),
            "targets_4_byte_aligned": sum(row["target_is_4_byte_aligned"] for row in selected),
            "minimum_byte_extent_fits": sum(row["minimum_byte_extent_fits"] for row in selected),
            "candidate_u32_at_target_counts": {
                str(value): count
                for value, count in sorted(slot_counts.get(index, {}).items(), key=lambda pair: str(pair[0]))
            },
        }

    return {
        "source_version": "Pokemon Let's Go Pikachu 1.0.2",
        "analysis_status": "HYPOTHESIS_ONLY",
        "classification": "UNKNOWN",
        "inventory": {
            "path": "manifests/files.csv",
            "sha256": sha256_bytes(catalog_bytes),
            "gfbcol_sources": len(candidates),
        },
        "source_root": str(romfs),
        "interpretation_limit": (
            "Relative targets, alignment, and the first target u32 are candidate "
            "observations only. They do not prove uoffset/vector types, element "
            "strides, field names, or collision semantics."
        ),
        "slot_summary": slot_summary,
        "entries": entries,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=PROJECT.parent,
                        help="parent of the 1.0.2 game folder")
    parser.add_argument("--output", type=Path,
                        default=PROJECT / "work" / "gfbcol-relative-target-probe.json")
    args = parser.parse_args()
    report = run(PROJECT, args.root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary = {key: value for key, value in report.items() if key != "entries"}
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    print(f"full_report={args.output}")


if __name__ == "__main__":
    main()
