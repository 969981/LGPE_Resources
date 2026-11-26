"""Cross-reference exact-build main targets against NSO RELATIVE/RELR addends."""

from __future__ import annotations

import hashlib
import importlib.util
import os
import shutil
import subprocess
from pathlib import Path
from typing import Iterable

from .core import source_dirs


EXPECTED_MAIN_SHA256 = "1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8"
EXPECTED_POKELDN_COMMIT = "0afe6f61f25464767e55b909eef6b260a372bb34"
EXPECTED_POKELDN_NSO_SHA256 = "f80e274130a5c055789815604d456271d715cdfc4f1c0528df7ce02460b3c87d"
EXPECTED_SEGMENT_IMAGE_SHA256 = "32ff708cc634829aeb2e39a5f39eb156d20e16237c5996f5e1299a905ffe68e9"
EXPECTED_SEGMENT_IMAGE_SIZE = 23_117_872
EXPECTED_MEMORY_IMAGE_SHA256 = "5d598a5d3bf2c645050231b87d4b4814a31798148ab2e4dc6bae35a2aa8f9ba1"
EXPECTED_MEMORY_IMAGE_SIZE = 32_376_568
EXPECTED_RELATIVE_COUNT = 71_687


def matching_relative_relocations(
    relocations: Iterable[tuple[int, int]], target_start: int, target_end: int
) -> list[dict[str, int]]:
    """Return relocation slots whose addends fall in [target_start, target_end)."""
    if target_start < 0 or target_end <= target_start:
        raise ValueError("target range must have a non-negative start and a greater end")
    matches = [
        {"slot": slot, "addend": addend}
        for slot, addend in relocations
        if target_start <= addend < target_end
    ]
    return sorted(matches, key=lambda row: (row["slot"], row["addend"]))


def build_nso_relocation_crossref_report(project: Path, game_root: Path) -> dict:
    """Parse the actual pinned 1.0.2 NSO without writing to ExeFS or expanded output."""
    project = project.resolve()
    main_path = source_dirs(game_root)["exefs"] / "main"
    main_bytes = main_path.read_bytes()
    main_sha256 = hashlib.sha256(main_bytes).hexdigest()
    if main_sha256 != EXPECTED_MAIN_SHA256:
        raise ValueError(f"unexpected main SHA-256: {main_sha256}")

    pokeldn_root = project / "tools/src/pokeldn"
    parser_path = pokeldn_root / "pokeldn/switch/nso.py"
    parser_sha256 = hashlib.sha256(parser_path.read_bytes()).hexdigest()
    if parser_sha256 != EXPECTED_POKELDN_NSO_SHA256:
        raise ValueError(f"unexpected PokeLDN nso.py SHA-256: {parser_sha256}")
    git = shutil.which("git")
    if not git:
        raise FileNotFoundError("git is required to verify the pinned PokeLDN checkout")
    revision = subprocess.run(
        [git, "-C", str(pokeldn_root), "-c", "safe.directory=*", "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if revision != EXPECTED_POKELDN_COMMIT:
        raise ValueError(f"unexpected PokeLDN commit: {revision}")

    spec = importlib.util.spec_from_file_location("lgpe_pokeldn_nso", parser_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load pinned PokeLDN parser from {parser_path}")
    parser = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(parser)

    segments = parser.segments(main_bytes)
    segment_extent = max(offset + len(data) for offset, data in segments.values())
    segment_image = bytearray(segment_extent)
    for offset, data in segments.values():
        segment_image[offset : offset + len(data)] = data
    segment_image = bytes(segment_image)
    segment_sha256 = hashlib.sha256(segment_image).hexdigest()
    if len(segment_image) != EXPECTED_SEGMENT_IMAGE_SIZE or segment_sha256 != EXPECTED_SEGMENT_IMAGE_SHA256:
        raise ValueError(
            "PokeLDN decompressed segments do not match the verified 1.0.2 image: "
            f"size={len(segment_image)} sha256={segment_sha256}"
        )
    memory_image = parser.layout(main_bytes)
    memory_sha256 = hashlib.sha256(memory_image).hexdigest()
    if len(memory_image) != EXPECTED_MEMORY_IMAGE_SIZE or memory_sha256 != EXPECTED_MEMORY_IMAGE_SHA256:
        raise ValueError(
            "PokeLDN zero-filled memory image does not match the verified 1.0.2 layout: "
            f"size={len(memory_image)} sha256={memory_sha256}"
        )
    relocations = parser.relatives(memory_image)
    if len(relocations) != EXPECTED_RELATIVE_COUNT:
        raise ValueError(f"unexpected RELATIVE/RELR relocation count: {len(relocations)}")
    if hashlib.sha256(main_path.read_bytes()).hexdigest() != main_sha256:
        raise ValueError("ExeFS main changed while the read-only report was being built")

    query_specs = [
        {
            "id": "spawn_dispatcher_body",
            "ranges": [(0x2F8A50, 0x2F8E6C)],
            "evidence": "Ghidra 12.2 exact-build function boundary; end address is exclusive.",
        },
        {"id": "spawn_rng_candidate_entry", "ranges": [(0x2FDF90, 0x2FDF91)]},
        {"id": "spawn_rng_next_handler_entry", "ranges": [(0x300E40, 0x300E41)]},
        {"id": "encounter_rate_helper_entry", "ranges": [(0x3154A0, 0x3154A1)]},
        {
            "id": "capture_api_table_targets",
            "ranges": [(0x1A5E80, 0x1A5E81), (0x1A61E0, 0x1A61E1), (0x1A64C0, 0x1A64C1)],
            "observed_local_labels": ["MapChangeCore_", "CaptureCall", "GetCaptureResult"],
            "evidence": "Labels are from a separate exact-build Ghidra table trace; this query only checks relocation addends.",
        },
    ]
    queries = []
    for query in query_specs:
        query_ranges = query["ranges"]
        matches = []
        for start, end in query_ranges:
            matches.extend(matching_relative_relocations(relocations, start, end))
        matches.sort(key=lambda row: (row["slot"], row["addend"]))
        rendered = {
            "id": query["id"],
            "matches": [
                {"slot": f"main+0x{row['slot']:x}", "addend": f"main+0x{row['addend']:x}"}
                for row in matches
            ],
            "match_count": len(matches),
        }
        if len(query_ranges) == 1:
            start, end = query_ranges[0]
            rendered["range"] = {
                "start": f"main+0x{start:x}",
                "end_exclusive": f"main+0x{end:x}",
            }
        else:
            rendered["ranges"] = [
                {"start": f"main+0x{start:x}", "end_exclusive": f"main+0x{end:x}"}
                for start, end in query_ranges
            ]
        if "evidence" in query:
            rendered["evidence"] = query["evidence"]
        if "observed_local_labels" in query:
            rendered["observed_local_labels"] = query["observed_local_labels"]
        queries.append(rendered)

    source_path = Path(os.path.relpath(main_path.resolve(), project)).as_posix()
    return {
        "schema": "lgpe-nso-relative-relocation-crossref-v1",
        "status": "STATIC_RELOCATION_CROSSREF_ONLY",
        "game": "Pokemon Let's Go Pikachu 1.0.2",
        "main": {
            "source_path": source_path,
            "sha256": main_sha256,
            "size_bytes": len(main_bytes),
            "image_base": "0x7100000000",
        },
        "parser": {
            "name": "PokeLDN",
            "repository": "https://github.com/Decryptu/pokeldn",
            "commit": revision,
            "license": "AGPL-3.0",
            "source_path": "tools/src/pokeldn/pokeldn/switch/nso.py",
            "source_sha256": parser_sha256,
            "methods": ["segments", "layout", "relatives (RELA R_AARCH64_RELATIVE and RELR)"],
        },
        "decompressed_segments_image": {
            "size_bytes": len(segment_image),
            "sha256": segment_sha256,
            "segments": [
                {"name": name, "memory_offset": f"0x{offset:x}", "size_bytes": len(data)}
                for name, (offset, data) in segments.items()
            ],
            "written_to_disk": False,
        },
        "zero_filled_memory_image": {
            "size_bytes": len(memory_image),
            "sha256": memory_sha256,
            "includes_bss": True,
            "written_to_disk": False,
        },
        "relocations": {
            "kind": "RELA R_AARCH64_RELATIVE plus RELR",
            "relative_count": len(relocations),
        },
        "queries": queries,
        "ghidra_evidence": {
            "version": "Ghidra 12.2",
            "read_only": True,
            "main_sha256": EXPECTED_MAIN_SHA256,
            "script": "scripts/ghidra/ScanSpawnDispatcherIncomingEdges.java",
            "script_sha256": hashlib.sha256(
                (project / "scripts/ghidra/ScanSpawnDispatcherIncomingEdges.java").read_bytes()
            ).hexdigest(),
            "wrapper": "scripts/ghidra/Run-ScanSpawnDispatcherIncomingEdges.ps1",
            "wrapper_sha256": hashlib.sha256(
                (project / "scripts/ghidra/Run-ScanSpawnDispatcherIncomingEdges.ps1").read_bytes()
            ).hexdigest(),
            "details": "docs/research/T10-notes.md",
        },
        "interpretation": {
            "runtime_dispatch": "UNVERIFIED",
            "rng_seed_initialization": "UNKNOWN",
            "limitations": [
                "A missing RELATIVE/RELR addend is not proof that no code can reach a target; computed or unrelocated references remain possible.",
                "A matching relocation identifies a slot and addend only; it does not assign the slot's runtime type or dispatch role.",
                "The RELATIVE/RELR scan does not enumerate every AArch64 absolute, GOT, instruction-materialized, or runtime-generated reference.",
                "Function labels and boundaries are carried from the exact-build Ghidra trace; the parser does not infer function semantics.",
            ],
        },
    }
