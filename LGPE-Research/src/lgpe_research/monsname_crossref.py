"""Cross-check unlabeled personal text against the decoded Japanese message list."""
from __future__ import annotations

import json
from pathlib import Path

from .core import NCA, PROJECT, VERSION, ensure_inside, sha256, source_dirs

PERSONAL_SOURCE = "bin/pokelib/personal/monsname.dat"
REFERENCE_SOURCE = "bin/message/JPN/common/monsname.dat"


def compare_text_lists(source: list[str], reference: list[str]) -> dict:
    mismatch_indices = [
        index for index, (left, right) in enumerate(zip(source, reference))
        if left != right
    ]
    return {
        "source_entries": len(source),
        "reference_entries": len(reference),
        "same_index_matches": min(len(source), len(reference)) - len(mismatch_indices),
        "mismatch_indices": mismatch_indices,
        "same_ordered_prefix": len(source) <= len(reference) and not mismatch_indices,
        "reference_tail_entries": max(0, len(reference) - len(source)),
    }


def _manifest_record(project: Path, relative_source: str) -> dict:
    manifest = project / "manifests/gamedata.jsonl"
    if not manifest.is_file():
        raise FileNotFoundError(manifest)
    matches = []
    for line in manifest.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("source") == relative_source:
            matches.append(row)
    if len(matches) != 1:
        raise ValueError(f"expected one game-data manifest row for {relative_source}; found {len(matches)}")
    record = matches[0]
    if record.get("status") != "DECODED":
        raise ValueError(f"{relative_source} is not DECODED in the game-data manifest")
    return record


def _verified_output(project: Path, root: Path, relative_source: str) -> tuple[dict, Path, Path]:
    record = _manifest_record(project, relative_source)
    romfs = source_dirs(root)["romfs"]
    source = ensure_inside(romfs / relative_source, romfs)
    output_relative = Path(str(record["output"]).replace("\\", "/"))
    if output_relative.is_absolute() or ".." in output_relative.parts or not output_relative.parts:
        raise ValueError(f"unsafe output path in game-data manifest: {record['output']}")
    output = ensure_inside(project / output_relative, project / "decoded")
    if sha256(source) != record.get("source_sha256"):
        raise ValueError(f"source hash differs from game-data manifest: {relative_source}")
    if sha256(output) != record.get("output_sha256"):
        raise ValueError(f"output hash differs from game-data manifest: {relative_source}")
    return record, source, output


def _texts(payload: dict, key: str, source: str) -> list[str]:
    rows = payload.get(key)
    if not isinstance(rows, list):
        raise ValueError(f"{source} decoded JSON has no {key} list")
    texts = []
    for index, row in enumerate(rows):
        value = row.get("text") if isinstance(row, dict) else None
        if not isinstance(value, str):
            raise ValueError(f"{source} decoded entry {index} has no text string")
        texts.append(value)
    return texts


def build_personal_monsname_crossref(
    project: Path = PROJECT, root: Path = PROJECT.parent,
) -> dict:
    """Rehash both decoded sources and compare only ordered text values."""
    project = Path(project).expanduser().resolve()
    root = Path(root).expanduser().resolve()
    primary, primary_source, primary_output = _verified_output(project, root, PERSONAL_SOURCE)
    reference, reference_source, reference_output = _verified_output(project, root, REFERENCE_SOURCE)
    primary_json = json.loads(primary_output.read_text(encoding="utf-8"))
    reference_json = json.loads(reference_output.read_text(encoding="utf-8"))
    primary_texts = _texts(primary_json, "entries", PERSONAL_SOURCE)
    reference_texts = _texts(reference_json, "lines", REFERENCE_SOURCE)
    if primary.get("count") is None or int(primary["count"]) != len(primary_texts):
        raise ValueError("primary decoded entry count differs from game-data manifest count")
    if reference.get("count") is None or int(reference["count"]) != len(reference_texts):
        raise ValueError("reference decoded entry count differs from game-data manifest count")
    comparison = compare_text_lists(
        primary_texts,
        reference_texts,
    )

    def source_record(record: dict, source_path: Path, output_path: Path) -> dict:
        return {
            "source": record["source"],
            "source_bytes": source_path.stat().st_size,
            "source_sha256": sha256(source_path),
            "status": record["status"],
            "output": record["output"],
            "output_sha256": sha256(output_path),
            "entry_count": record.get("count"),
            "method": record.get("method"),
            "tool_versions": record.get("tool_versions", {}),
        }

    return {
        "schema": "lgpe-personal-monsname-crossref-v1",
        "source_version": VERSION,
        "nca_folder": NCA,
        "primary": source_record(primary, primary_source, primary_output),
        "reference": source_record(reference, reference_source, reference_output),
        "comparison": comparison,
        "interpretation": (
            "text values are compared by index only; the match does not assign source identity or labels"
        ),
    }
