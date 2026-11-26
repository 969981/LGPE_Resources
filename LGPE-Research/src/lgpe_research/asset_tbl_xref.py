"""Literal path cross-references for AHTB asset labels."""
from __future__ import annotations

from pathlib import PurePosixPath
from typing import Iterable


def cross_reference_asset_paths(
    entries: Iterable[dict], romfs_paths: Iterable[str],
) -> list[dict]:
    """Compare ``bin/message/<label>`` literally with a scanned ROMFS path set.

    This reports string/path matches only. It does not assign a hash algorithm,
    loader behavior, or semantic meaning to an AHTB record.
    """
    exact_paths = {str(path) for path in romfs_paths}
    folded_paths: dict[str, list[str]] = {}
    for path in exact_paths:
        folded_paths.setdefault(path.casefold(), []).append(path)
    for matches in folded_paths.values():
        matches.sort(key=str.casefold)

    results = []
    message_root = PurePosixPath("bin/message")
    for entry in entries:
        label = str(entry.get("label", ""))
        relative_label = PurePosixPath(label)
        row = {
            "index": entry.get("index"),
            "hash": entry.get("hash"),
            "label": label,
            "raw_label_hex": entry.get("raw_label_hex"),
            "relative_source_candidate": None,
            "path_status": "INVALID_LABEL_PATH",
            "matched_source_paths": [],
            "same_stem_tbl_candidate": None,
            "same_stem_tbl_present": False,
        }
        if relative_label.is_absolute() or ".." in relative_label.parts or not relative_label.parts:
            results.append(row)
            continue

        candidate = (message_root / relative_label).as_posix()
        row["relative_source_candidate"] = candidate
        if relative_label.suffix.casefold() == ".dat":
            table_candidate = PurePosixPath(candidate).with_suffix(".tbl").as_posix()
            row["same_stem_tbl_candidate"] = table_candidate
            row["same_stem_tbl_present"] = table_candidate in exact_paths
        matches = folded_paths.get(candidate.casefold(), [])
        row["matched_source_paths"] = matches
        if len(matches) > 1:
            row["path_status"] = "AMBIGUOUS_CASEFOLD_MATCH"
        elif candidate in exact_paths:
            row["path_status"] = "MATCH_EXACT"
        elif matches:
            row["path_status"] = "MATCH_CASEFOLD"
        else:
            row["path_status"] = "NO_MATCH"
        results.append(row)
    return results
