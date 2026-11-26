#!/usr/bin/env python3
"""Hash and summarize schema-free GFBCol root slot 3 candidates."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path, PurePosixPath

from lgpe_research.core import PROJECT, VERSION, ensure_inside, source_dirs
from lgpe_research.gfbcol_slot3_probe import inspect_slot3_words


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def run(project: Path = PROJECT, root: Path | None = None) -> dict:
    project = project.expanduser().resolve()
    game_root = (root or project.parent).expanduser().resolve()
    romfs = source_dirs(game_root)["romfs"]
    inventory = project / "manifests" / "files.csv"
    inventory_bytes = inventory.read_bytes()
    with inventory.open("r", encoding="utf-8-sig", newline="") as stream:
        sources = [
            row for row in csv.DictReader(stream)
            if row["partition"].casefold() == "romfs"
            and row["suffix"].casefold() == ".gfbcol"
        ]

    entries = []
    errors = []
    word_values = [Counter() for _ in range(8)]
    word_zero_counts = Counter()
    first_target_aliases = Counter()
    target_lengths = Counter()
    distinct_vectors = Counter()
    target_in_bounds = extent_in_bounds = 0
    for item in sorted(sources, key=lambda row: row["relative_path"].casefold()):
        relative = PurePosixPath(item["relative_path"].replace("\\", "/"))
        if relative.is_absolute() or ".." in relative.parts or not relative.parts:
            errors.append({"source": str(relative), "error": "unsafe inventory path"})
            continue
        expected = romfs.joinpath(*relative.parts)
        try:
            source = ensure_inside(expected, romfs)
            if source != expected:
                raise ValueError("source path resolves through a symlink")
            raw = source.read_bytes()
            digest = _sha256(raw)
            if len(raw) != int(item["bytes"]):
                raise ValueError("source byte count differs from inventory")
            if digest != item["sha256"]:
                raise ValueError("source SHA256 differs from inventory")
            probe = inspect_slot3_words(raw)
        except (OSError, ValueError, KeyError) as exc:
            errors.append({"source": relative.as_posix(), "error": f"{type(exc).__name__}: {exc}"})
            continue

        values = [word["u32"] for word in probe["words"]]
        for index, value in enumerate(values):
            word_values[index][value] += 1
            word_zero_counts[index] += value == 0
        vector = tuple(values)
        distinct_vectors[vector] += 1
        candidate = probe["first_word_relative_target_candidate"]
        if candidate["target_in_bounds"]:
            target_in_bounds += 1
            target_lengths[candidate["target_u32_candidate"]] += 1
        if candidate["extent_in_bounds"]:
            extent_in_bounds += 1
        if candidate["target_aliases_slot3_word_index"] is not None:
            first_target_aliases[candidate["target_aliases_slot3_word_index"]] += 1
        entries.append({
            "source": relative.as_posix(),
            "source_bytes": len(raw),
            "source_sha256": digest,
            **probe,
        })

    return {
        "source_version": "Pokemon Let's Go Pikachu 1.0.2",
        "analysis_status": "HYPOTHESIS_ONLY",
        "semantic_status": "UNKNOWN",
        "interpretation_limit": (
            "Slot 3 entries and first-word relative targets are recorded as raw candidate values. "
            "Bounds and alignment checks do not establish field types or meanings."
        ),
        "inventory": {
            "path": "manifests/files.csv",
            "sha256": _sha256(inventory_bytes),
            "gfbcol_sources": len(sources),
        },
        "sources_read": len(entries),
        "source_failures": errors,
        "slot3_word_position_summary": {
            str(index): {
                "distinct_u32_values": len(word_values[index]),
                "zero_count": word_zero_counts[index],
                "most_common_u32_values": [
                    {"u32": value, "count": count}
                    for value, count in word_values[index].most_common(12)
                ],
            }
            for index in range(8)
        },
        "distinct_eight_word_vectors": len(distinct_vectors),
        "first_word_target_candidate": {
            "in_bounds_sources": target_in_bounds,
            "extent_in_bounds_sources": extent_in_bounds,
            "target_aliases_slot3_word_index_counts": dict(sorted(first_target_aliases.items())),
            "target_u32_candidate_counts": {
                str(value): count for value, count in sorted(target_lengths.items())
            },
        },
        "field_names_assigned": False,
        "field_types_assigned": False,
        "entries": entries,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, default=PROJECT)
    parser.add_argument("--root", type=Path, default=PROJECT.parent,
                        help="parent of the 1.0.2 game folder")
    parser.add_argument("--output", type=Path,
                        default=PROJECT / "work" / "gfbcol-slot3-candidate-probe.json")
    args = parser.parse_args()
    report = run(args.project, args.root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    summary = {key: value for key, value in report.items() if key != "entries"}
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    print(f"full_report={args.output}")
    return 0 if not report["source_failures"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
