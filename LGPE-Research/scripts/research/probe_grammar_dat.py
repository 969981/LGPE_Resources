#!/usr/bin/env python3
"""Record read-only parser probes for the LGPE grammar DAT resources."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import sys
from pathlib import Path

from lgpe_research import gamedata_decode
from lgpe_research.core import NCA, PROJECT, VERSION

POKEDAT_COMMIT = "bd423b2cad9aa852fddb796bbba3c5e7b381289b"
GRAMMAR_PATH = Path("bin/message/grammar")
MESSAGE_CONTROL = Path("bin/message/English/common/itemname.dat")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _pokedat_commit(source: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(source), "rev-parse", "HEAD"],
        check=True, capture_output=True, text=True,
    )
    return result.stdout.strip()


def _snapshot_grammar_names(snapshot: Path) -> list[str]:
    lines = snapshot.read_text(encoding="utf-16").splitlines()
    start = next(
        (index for index, line in enumerate(lines) if line.rstrip().endswith("├─grammar")),
        None,
    )
    if start is None:
        raise ValueError("grammar directory is absent from the source snapshot")
    names = []
    for line in lines[start + 1:]:
        if "├─" in line or "└─" in line:
            break
        parts = line.split()
        if parts and parts[-1].lower().endswith(".dat"):
            names.append(parts[-1])
    return names


def _probe_text_file(data: bytes, pokedat: Path) -> tuple[str | None, int | None]:
    sys.path.insert(0, str(pokedat))
    try:
        from text_config import TextConfig
        from text_file import TextFile

        text = TextFile(data, TextConfig("LGPE"))
        return None, len(text.lines)
    except Exception as exc:
        return f"{type(exc).__name__}: {exc}", None
    finally:
        sys.path.pop(0)


def probe(root: Path = PROJECT.parent) -> dict:
    source_root = root.expanduser().resolve() / VERSION / NCA / "1"
    grammar_root = source_root / GRAMMAR_PATH
    pokedat = PROJECT / "tools" / "src" / "pokedat"
    commit = _pokedat_commit(pokedat)
    if commit != POKEDAT_COMMIT:
        raise ValueError(f"pokedat commit mismatch: expected {POKEDAT_COMMIT}, got {commit}")

    rows = []
    paths = sorted(grammar_root.glob("*.dat"))
    for path in paths:
        raw = path.read_bytes()
        before_hash = _sha256(raw)
        try:
            gamedata_decode.message(raw, b"", pokedat)
            lgpe_error = None
        except Exception as exc:
            lgpe_error = f"{type(exc).__name__}: {exc}"
        pokedat_error, line_count = _probe_text_file(raw, pokedat)
        rows.append({
            "source": (GRAMMAR_PATH / path.name).as_posix(),
            "bytes": len(raw),
            "sha256": before_hash,
            "prefix_hex": raw[:20].hex(),
            "paired_tbl_present": path.with_suffix(".tbl").is_file(),
            "classification": "UNKNOWN",
            "lgpe_message_reader_error": lgpe_error,
            "pokedat_text_file_error": pokedat_error,
            "pokedat_line_count": line_count,
            "source_unchanged": _sha256(path.read_bytes()) == before_hash,
        })

    scan_path = PROJECT / "manifests" / "files.csv"
    with scan_path.open("r", encoding="utf-8-sig", newline="") as stream:
        scan_rows = list(csv.DictReader(stream))
    scan_sizes = {
        Path(row["relative_path"]).name: int(row["bytes"])
        for row in scan_rows
        if row["partition"] == "romfs"
        and row["relative_path"].startswith(GRAMMAR_PATH.as_posix() + "/")
        and row["suffix"].lower() == ".dat"
    }
    actual_sizes = {path.name: path.stat().st_size for path in paths}
    snapshot_names = _snapshot_grammar_names(
        PROJECT / "docs" / "source_snapshot" / "pikachu.1.0.2.txt",
    )
    grammar_inventory = {
        "tree_snapshot_names": sorted(snapshot_names, key=str.casefold),
        "scan_catalog_names": sorted(scan_sizes, key=str.casefold),
        "actual_source_names": sorted(actual_sizes, key=str.casefold),
        "all_name_sets_equal": set(snapshot_names) == set(scan_sizes) == set(actual_sizes),
        "all_scan_sizes_match_sources": actual_sizes == scan_sizes,
        "snapshot_contains_sizes_or_hashes": False,
    }

    control_path = source_root / MESSAGE_CONTROL
    control_data = control_path.read_bytes()
    control_error, control_line_count = _probe_text_file(control_data, pokedat)
    return {
        "source_version": "Pokemon Let's Go Pikachu 1.0.2",
        "pokedat_commit": commit,
        "grammar_source_count": len(rows),
        "grammar_accepted": sum(row["pokedat_line_count"] is not None for row in rows),
        "grammar_unknown": sum(row["classification"] == "UNKNOWN" for row in rows),
        "grammar_inventory_crosscheck": grammar_inventory,
        "grammar": rows,
        "positive_control": {
            "source": MESSAGE_CONTROL.as_posix(),
            "bytes": len(control_data),
            "sha256": _sha256(control_data),
            "pokedat_error": control_error,
            "pokedat_line_count": control_line_count,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=PROJECT.parent)
    parser.add_argument(
        "--output", type=Path, default=PROJECT / "work" / "grammar-probe.json",
    )
    args = parser.parse_args()
    report = probe(args.root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
