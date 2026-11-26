"""Read-only candidate profiling for localized sort_string DAT files."""
from __future__ import annotations

import hashlib
from pathlib import Path
from .core import NCA, VERSION


SORT_STRING_RELATIVE = Path("bin/app/sort_string")
_CANDIDATE_SUFFIXES = (
    "_initial_index.dat",
    "_initial_to_sort.dat",
    "_sort_table.dat",
)


def _candidate_kind(name: str) -> str | None:
    for suffix in _CANDIDATE_SUFFIXES:
        if name.endswith(suffix):
            return suffix.removesuffix(".dat").removeprefix("_")
    return None


def _profile_file(path: Path, romfs_root: Path) -> dict:
    raw = path.read_bytes()
    size = len(raw)
    kind = _candidate_kind(path.name)
    even_length = size % 2 == 0
    values = (
        [
            int.from_bytes(raw[offset:offset + 2], "little")
            for offset in range(0, size, 2)
        ]
        if even_length
        else None
    )
    permutation = None
    if kind == "sort_table" and values is not None:
        permutation = (
            bool(values)
            and set(values) == set(range(1, len(values) + 1))
            and len(values) == len(set(values))
        )

    return {
        "partition": "romfs",
        "source": path.relative_to(romfs_root).as_posix(),
        "source_version": VERSION,
        "nca_folder": NCA,
        "bytes": size,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "format_status": "UNKNOWN",
        "profile_method": "read-only byte profile; no decoder applied",
        "candidate_representation": "u16le hypothesis" if even_length else None,
        "u16le_candidate_count": len(values) if values is not None else None,
        "sort_table_permutation_1_based": permutation,
    }


def profile_sort_string(romfs_root: Path) -> dict:
    """Report byte-level candidates without decoding or naming table semantics."""
    romfs_root = Path(romfs_root).expanduser().resolve()
    directory = romfs_root / SORT_STRING_RELATIVE
    if not directory.is_dir():
        raise FileNotFoundError(f"sort_string directory is missing: {directory}")

    files = []
    for locale in sorted(directory.iterdir(), key=lambda path: path.name.casefold()):
        if locale.is_symlink() or not locale.is_dir():
            continue
        for source in sorted(locale.iterdir(), key=lambda path: path.name.casefold()):
            if source.is_symlink() or not source.is_file() or _candidate_kind(source.name) is None:
                continue
            files.append(_profile_file(source, romfs_root))

    summary = {
        "scanned": len(files),
        "decoded": 0,
        "failed": 0,
        "unknown": len(files),
        "u16le_even_length_candidates": sum(
            row["candidate_representation"] == "u16le hypothesis" for row in files
        ),
        "sort_table_permutation_tested": sum(
            row["sort_table_permutation_1_based"] is not None for row in files
        ),
        "sort_table_permutation_passed": sum(
            row["sort_table_permutation_1_based"] is True for row in files
        ),
    }
    return {"summary": summary, "files": files}
