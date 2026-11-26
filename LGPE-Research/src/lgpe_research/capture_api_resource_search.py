"""Search likely LGPE script/text resources for exact capture API name literals."""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from .core import iter_regular_files


MAIN_SHA256 = "1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8"
API_NAMES = ("CaptureCall", "GetCaptureResult")
ENCODINGS = ("ascii", "utf-16le", "utf-16be")


def _matching_files(directory: Path, suffixes: set[str] | None) -> list[Path]:
    if not directory.is_dir():
        raise FileNotFoundError(f"expected local search directory missing: {directory}")
    paths = iter_regular_files(directory)
    if suffixes is not None:
        paths = [path for path in paths if path.suffix.casefold() in suffixes]
    return paths


def _needles() -> list[tuple[str, str, bytes]]:
    return [
        (name, encoding, name.encode(encoding).lower())
        for name in API_NAMES
        for encoding in ENCODINGS
    ]


def _find_occurrences(data: bytes, pattern: bytes) -> list[int]:
    lowered = data.lower()
    offsets: list[int] = []
    cursor = 0
    while True:
        offset = lowered.find(pattern, cursor)
        if offset < 0:
            return offsets
        offsets.append(offset)
        cursor = offset + 1


def _scope_files(project: Path, romfs: Path) -> list[tuple[str, Path, str]]:
    scopes: list[tuple[str, Path, str]] = []
    for relative, suffixes, label in (
        ("bin/message", {".dat", ".tbl"}, "romfs/bin/message"),
        ("bin/battle/ai_script", {".amx"}, "romfs/bin/battle/ai_script"),
    ):
        root = romfs / relative
        for path in _matching_files(root, suffixes):
            scopes.append((label, path, path.relative_to(romfs).as_posix()))

    archive_root = (
        project
        / "decoded"
        / "1.0.2"
        / "romfs"
        / "bin"
        / "archive"
        / "script_amx.gfpak.contents"
    )
    for path in _matching_files(archive_root, None):
        # The .json files beside extracted members are decoder views, not source member bytes.
        if path.suffix.casefold() == ".json":
            continue
        rel = path.relative_to(archive_root).as_posix()
        scopes.append(("script_amx.gfpak.contents", path, rel))
    return sorted(scopes, key=lambda item: (item[0], item[2].casefold()))


def build_capture_api_resource_search(
    project: Path,
    romfs: Path,
    *,
    main_sha256: str,
) -> dict[str, Any]:
    """Search selected 1.0.2 resources; a string hit is a candidate, not a call proof."""
    if main_sha256 != MAIN_SHA256:
        raise ValueError("source is not bound to the expected LGPE Pikachu 1.0.2 main")
    project = project.resolve()
    romfs = romfs.resolve()
    scopes = _scope_files(project, romfs)
    scope_counts: dict[str, dict[str, int]] = {}
    matches: list[dict[str, Any]] = []
    source_files: list[dict[str, Any]] = []
    needles = _needles()

    for label, path, relative in scopes:
        data = path.read_bytes()
        source_sha256 = hashlib.sha256(data).hexdigest()
        stats = scope_counts.setdefault(label, {"files": 0, "bytes": 0})
        stats["files"] += 1
        stats["bytes"] += len(data)
        source_files.append({
            "scope": label,
            "relative_path": relative,
            "source_size": len(data),
            "source_sha256": source_sha256,
        })
        file_matches = []
        for name, encoding, needle in needles:
            for offset in _find_occurrences(data, needle):
                file_matches.append({
                    "api_name": name,
                    "encoding": encoding,
                    "byte_offset": offset,
                })
        if file_matches:
            matches.append({
                "scope": label,
                "relative_path": relative,
                "source_sha256": source_sha256,
                "source_size": len(data),
                "literal_occurrences": file_matches,
            })

    searched_files = sum(value["files"] for value in scope_counts.values())
    searched_bytes = sum(value["bytes"] for value in scope_counts.values())
    return {
        "schema": "lgpe-research.capture-api-resource-string-search.v1",
        "status": "NO_LITERAL_REFERENCE" if not matches else "LITERAL_REFERENCE_CANDIDATE",
        "build": {
            "game": "Pokemon: Let's Go, Pikachu!",
            "version": "1.0.2",
            "nca_id": "2b7730a9e56498bbafac2002d4908c6b",
            "main_sha256": MAIN_SHA256,
        },
        "search": {
            "api_names": list(API_NAMES),
            "encodings": list(ENCODINGS),
            "case_sensitive": False,
            "files_scanned": searched_files,
            "bytes_scanned": searched_bytes,
            "scope_counts": scope_counts,
            "source_files": source_files,
            "scopes": [
                "actual RomFS bin/message .dat and .tbl files",
                "actual RomFS bin/battle/ai_script .amx files",
                "raw extracted members under decoded/1.0.2/romfs/bin/archive/script_amx.gfpak.contents (JSON sidecars excluded)",
            ],
        },
        "matches": matches,
        "limitations": [
            "No literal match does not exclude hashed or numeric API identifiers, compressed or unsearched resources, generic registry dispatch, or runtime-generated calls.",
            "A literal match is only a string observation; it does not establish a call, registration, or gameplay meaning.",
        ],
    }
