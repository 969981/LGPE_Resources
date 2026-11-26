"""Bounded, provenance-preserving batch conversions for LGPE visual assets."""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path, PurePosixPath

from . import assets_decode
from .batch import _receipt, _scan_catalog, existing_domain_outputs, merge_failures, write_jsonl_selected
from .core import PROJECT, VERSION, add_receipts, sha256, source_dirs

KINDS = {
    "texture": (".bntx", ".png", "BNTX"),
    "model": (".gfbmdl", ".glb", None),
    "animation": (".gfbanm", ".json", None),
    "particle": (".ptcl", ".json", "VFXB"),
}
REVISIONS = {
    "BNTX-Extractor": "2c08e8e55fcc666ba6568a102f36dabd6c584e25",
    "Pokemon-Switch-Model-Importer-Blender": "bb597581916c7407385afb5461efe4d2ae2f38f9",
    "io_scene_gfbanm": "567db8f342a8ca27be8abf58ddaffeb6f5206bd4",
    "Switch-Toolbox": "3fcb87f1fea25ad56db139b0d9577db591f54118",
}


def _existing_outputs(project: Path, domain: str) -> dict[str, dict]:
    return existing_domain_outputs(project, domain)


def run_asset_batch(
    kind: str,
    root: Path = PROJECT.parent,
    project: Path = PROJECT,
    limit: int = 20,
    execute: bool = False,
    blender: Path | None = None,
    ffmpeg: Path | None = None,
    only_sources: set[str] | None = None,
    timeout: int = 180,
) -> dict:
    if kind not in KINDS:
        raise ValueError(f"unsupported asset batch kind: {kind}")
    suffix, output_suffix, expected_signature = KINDS[kind]
    romfs = source_dirs(root)["romfs"]
    catalog = sorted(
        (row for row in _scan_catalog(project)
         if row["partition"] == "romfs" and row["suffix"].lower() == suffix),
        key=lambda row: row["relative_path"].casefold(),
    )
    candidates = []
    results = []
    for item in catalog:
        base = {
            "domain": kind,
            "source": item["relative_path"],
            "source_bytes": int(item["bytes"]),
            "signature": item["signature"],
        }
        if expected_signature and item["signature"] != expected_signature:
            results.append({**base, "status": "UNKNOWN", "reason": f"expected signature {expected_signature}"})
            continue
        relative = PurePosixPath(item["relative_path"])
        if relative.is_absolute() or ".." in relative.parts or not relative.parts:
            results.append({**base, "status": "FAILED", "reason": "unsafe relative path in scan catalog"})
            continue
        source = romfs.joinpath(*relative.parts)
        candidates.append((source, item, base))

    if only_sources is not None:
        selected_names = {source.casefold() for source in only_sources}
        selected = [entry for entry in candidates if entry[1]["relative_path"].casefold() in selected_names]
    else:
        selected = candidates if not limit else candidates[:limit]
    selected_sources = {str(source).casefold() for source, _, _ in selected}
    receipts = []
    existing = _existing_outputs(project, kind)
    project_work = project / "work"
    project_work.mkdir(parents=True, exist_ok=True)

    for source, item, base in candidates:
        rel = item["relative_path"]
        relative = PurePosixPath(rel)
        output = project / "decoded" / VERSION / "romfs" / Path(*relative.parts).with_suffix(output_suffix)
        row = {**base, "output": str(output.relative_to(project))}
        if str(source).casefold() not in selected_sources:
            results.append({**row, "status": "PENDING", "reason": "outside current --limit"})
            continue
        if not execute:
            results.append({**row, "status": "DRY_RUN"})
            continue
        source_hash = sha256(source)
        row["source_sha256"] = source_hash
        output_key = os.path.normcase(os.path.abspath(os.fspath(output))).casefold()
        prior = existing.get(output_key)
        if output.exists():
            if (
                prior
                and prior.get("source_sha256") == source_hash
                and prior.get("output_sha256") == sha256(output)
            ):
                previous_row = prior.get("manifest_row", {})
                row.update({key: value for key, value in previous_row.items() if key not in row and key != "status"})
                row.update({
                    "status": "DECODED_EXISTING_VERIFIED",
                    "output_sha256": prior["output_sha256"],
                    "output_bytes": output.stat().st_size,
                })
                results.append(row)
                continue
            row.update({"status": "FAILED", "error": f"unattributed/conflicting output exists: {output}"})
            results.append(row)
            continue

        commands = []
        tool_versions = {}
        conversion = None
        try:
            with tempfile.TemporaryDirectory(prefix=f"asset-{kind}-", dir=project_work) as tmp:
                staging = Path(tmp) / ("converted" + output_suffix)
                if kind == "texture":
                    ffmpeg = ffmpeg or Path(r"D:\Tool\ffmpeg-8.0.1-full_build\bin\ffmpeg.exe")
                    tool_versions = {"BNTX-Extractor": REVISIONS["BNTX-Extractor"]}
                    conversion = assets_decode.convert_bntx(source, staging, project, ffmpeg, commands)
                    if conversion.get("decoder") == "ffmpeg":
                        tool_versions["ffmpeg"] = {"version": "8.0.1", "executable_sha256": sha256(ffmpeg)}
                    if conversion.get("decoder", "").startswith("texture2ddecoder"):
                        tool_versions["texture2ddecoder"] = {"version": "1.0.6", "license": "MIT"}
                elif kind == "model":
                    blender = blender or Path(r"D:\Tool\Blender 5.1\blender.exe")
                    script = Path(__file__).with_name("assets_blender.py")
                    tool_versions = {
                        "Pokemon-Switch-Model-Importer-Blender": REVISIONS["Pokemon-Switch-Model-Importer-Blender"],
                        "blender": {"version": "5.1.2", "executable_sha256": sha256(blender)},
                    }
                    assets_decode.run_command(
                        [str(blender), "--background", "--factory-startup", "--python",
                         str(script), "--", str(project), str(source), str(staging)],
                        commands, timeout=timeout,
                    )
                elif kind == "animation":
                    tool = project / "tools" / "src" / "io_scene_gfbanm"
                    tool_versions = {"io_scene_gfbanm": REVISIONS["io_scene_gfbanm"]}
                    parsed = assets_decode.animation_json(source, tool)
                    staging.write_text(json.dumps(parsed, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                else:
                    tool_versions = {"Switch-Toolbox": REVISIONS["Switch-Toolbox"]}
                    parsed = assets_decode.ptcl_sections(source.read_bytes())
                    staging.write_text(json.dumps(parsed, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

                validation = assets_decode.validate_output(staging)
                if sha256(source) != source_hash:
                    raise ValueError("source changed during conversion")
                output.parent.mkdir(parents=True, exist_ok=True)
                staging.replace(output)

            output_hash = sha256(output)
            status = "DECODED" if kind in {"texture", "model"} else "STRUCTURE_DECODED_RENDER_UNSUPPORTED"
            row.update({
                "status": status,
                "output_sha256": output_hash,
                "output_bytes": output.stat().st_size,
                "validation": validation,
                "conversion": conversion,
                "tool_versions": tool_versions,
                "commands": commands,
            })
            receipts.append(_receipt(
                project, root, rel, source, output,
                "lgpe_research.asset_batch/" + kind,
                tool_versions,
                source_sha256=source_hash,
                output_sha256=output_hash,
                status=status,
                validation=validation,
                conversion=conversion,
                command=commands,
            ))
        except Exception as exc:
            message = f"{type(exc).__name__}: {exc}"
            unsupported = (
                isinstance(exc, NotImplementedError)
                or "unsupported" in str(exc).lower()
                or "only one-texture" in str(exc).lower()
            )
            row.update({
                "status": "UNSUPPORTED" if unsupported else "FAILED",
                "error": message,
                "conversion": conversion,
                "tool_versions": tool_versions,
                "commands": commands,
            })
        results.append(row)

    manifest = project / "manifests" / f"{kind}s.jsonl"
    write_jsonl_selected(manifest, results, only_sources)
    merge_failures(
        project,
        [{key: row.get(key) for key in ("domain", "source", "status", "error")}
         for row in results if row.get("status") in {"FAILED", "UNSUPPORTED"}],
        resolved=[{"domain": kind, "source": row["source"]} for row in results
                  if row.get("status") in {"DECODED", "DECODED_EXISTING_VERIFIED", "STRUCTURE_DECODED_RENDER_UNSUPPORTED"}],
    )
    if execute:
        add_receipts(project, receipts, trusted_outputs=True)
    statuses = [row.get("status") for row in results]
    return {
        "catalogued": len(catalog),
        "compatible": len(candidates),
        "selected": len(selected),
        "decoded": sum(status in {"DECODED", "DECODED_EXISTING_VERIFIED", "STRUCTURE_DECODED_RENDER_UNSUPPORTED"} for status in statuses),
        "failed": sum(status == "FAILED" for status in statuses),
        "unsupported": sum(status == "UNSUPPORTED" for status in statuses),
        "unknown": sum(status == "UNKNOWN" for status in statuses),
        "pending": sum(status == "PENDING" for status in statuses),
        "execute": execute,
        "manifest": str(manifest),
    }
