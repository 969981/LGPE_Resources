#!/usr/bin/env python3
"""Inspect GFBCol slot-0 child fields as bounded string candidates only."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path, PurePosixPath

from lgpe_research.core import PROJECT, ensure_inside, source_dirs
from lgpe_research.gfbcol_slot0_probe import inspect_slot0_string_candidates


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read_source_list(path: Path) -> set[str]:
    return {
        line.strip().replace("\\", "/")
        for line in path.read_text(encoding="utf-8-sig").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }


def run(
    project: Path = PROJECT,
    root: Path | None = None,
    limit: int = 5,
    sources_file: Path | None = None,
) -> dict:
    project = project.expanduser().resolve()
    game_root = (root or project.parent).expanduser().resolve()
    romfs = source_dirs(game_root)["romfs"]
    inventory = project / "manifests" / "files.csv"
    inventory_bytes = inventory.read_bytes()
    with inventory.open("r", encoding="utf-8-sig", newline="") as stream:
        catalog = [
            row for row in csv.DictReader(stream)
            if row["partition"].casefold() == "romfs"
            and row["suffix"].casefold() == ".gfbcol"
        ]

    requested = _read_source_list(sources_file) if sources_file else None
    ordered = sorted(catalog, key=lambda row: row["relative_path"].casefold())
    selected = [
        row for row in ordered
        if requested is None or row["relative_path"].replace("\\", "/").casefold()
        in {name.casefold() for name in requested}
    ]
    if requested is not None:
        found = {row["relative_path"].replace("\\", "/").casefold() for row in selected}
        missing = sorted(name for name in requested if name.casefold() not in found)
    else:
        missing = []
        if limit:
            selected = selected[:limit]

    entries = []
    errors = [{"source": name, "error": "requested source is absent from inventory"} for name in missing]
    candidate_strings = Counter()
    unresolved_fields = 0
    child_tables = 0
    for item in selected:
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
            probe = inspect_slot0_string_candidates(raw)
        except (OSError, ValueError, KeyError) as exc:
            errors.append({"source": relative.as_posix(), "error": f"{type(exc).__name__}: {exc}"})
            continue

        child_tables += probe["child_element_count"]
        for element in probe["elements"]:
            candidate = element["string_candidate"]
            if candidate["classification"] == "UTF8_NUL_TERMINATED_LENGTH_PREFIX_CANDIDATE":
                candidate_strings[candidate["decoded_text"]] += 1
            else:
                unresolved_fields += 1
        entries.append({
            "source": relative.as_posix(),
            "source_bytes": len(raw),
            "source_sha256": digest,
            **probe,
        })

    return {
        "source_version": "Pokemon Let's Go Pikachu 1.0.2",
        "analysis_status": "HYPOTHESIS_ONLY",
        "schema_status": "UNKNOWN",
        "interpretation_limit": (
            "UTF-8 decoding is reported only after a child field interpreted as a forward uoffset "
            "reaches a bounded length-prefixed byte sequence followed by NUL. This does not prove "
            "the field type, label meaning, or full GFBCol schema."
        ),
        "inventory": {
            "path": "manifests/files.csv",
            "sha256": _sha256(inventory_bytes),
            "gfbcol_sources": len(catalog),
        },
        "selection": {
            "sources_file": sources_file.as_posix() if sources_file else None,
            "limit": limit if requested is None else None,
            "selected_sources": len(selected),
        },
        "sources_read": len(entries),
        "source_failures": errors,
        "slot0_child_table_count": child_tables,
        "valid_string_shape_candidates": sum(candidate_strings.values()),
        "unresolved_child_fields": unresolved_fields,
        "candidate_text_counts": dict(sorted(candidate_strings.items())),
        "field_names_assigned": False,
        "field_types_assigned": False,
        "entries": entries,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, default=PROJECT)
    parser.add_argument("--root", type=Path, default=PROJECT.parent,
                        help="parent of the 1.0.2 game folder")
    parser.add_argument("--limit", type=int, default=5,
                        help="maximum sources; 0 means all (ignored with --sources-file)")
    parser.add_argument("--sources-file", type=Path,
                        help="read only listed RomFS-relative .gfbcol paths")
    parser.add_argument("--output", type=Path,
                        default=PROJECT / "work" / "gfbcol-slot0-string-candidates.json")
    args = parser.parse_args()
    report = run(args.project, args.root, args.limit, args.sources_file)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    summary = {key: value for key, value in report.items() if key != "entries"}
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    print(f"full_report={args.output}")
    return 0 if not report["source_failures"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
