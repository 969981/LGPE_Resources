from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path, PurePosixPath

from .batch import _receipt, _scan_catalog, merge_failures, write_jsonl_selected
from .core import PROJECT, VERSION, add_receipts, sha256, source_dirs

WWISER_COMMIT = "08e937b649bc7007c234bbd59e34a41d5eef3b38"
SUCCESS = {"DECODED", "DECODED_EXISTING_VERIFIED"}


def _existing_bnk_outputs(project: Path) -> dict[str, dict]:
    result = {}
    paths = [
        project / "manifests" / "bnk.jsonl",
        project / "logs" / "assets_samples.jsonl",
    ]
    for path in paths:
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("status") not in SUCCESS:
                continue
            if path.name == "assets_samples.jsonl" and row.get("kind") != "bnk":
                continue
            output = row.get("output")
            if not output:
                continue
            output_path = Path(output)
            if not output_path.is_absolute():
                output_path = project / output_path
            result[os.path.normcase(os.path.abspath(os.fspath(output_path))).casefold()] = {
                "source_sha256": row.get("source_sha256"),
                "output_sha256": row.get("output_sha256"),
            }
    return result


def _validate_xml(path: Path) -> dict:
    root = ET.parse(path).getroot()
    if not root.tag or len(root) == 0:
        raise ValueError("wwiser XML has no root element or top-level records")
    return {
        "format": "XML",
        "root": root.tag,
        "top_level_elements": len(root),
        "bytes": path.stat().st_size,
    }


def _write_results(project: Path, results: list[dict], receipts: list[dict], only_sources: set[str] | None) -> None:
    manifest = project / "manifests" / "bnk.jsonl"
    write_jsonl_selected(manifest, results, only_sources)
    merge_failures(
        project,
        [
            {"domain": "bnk", "source": row.get("source"), "status": row.get("status"), "error": row.get("error")}
            for row in results if row.get("status") == "FAILED"
        ],
        resolved=[
            {"domain": "bnk", "source": row["source"]}
            for row in results if row.get("status") in SUCCESS
        ],
    )
    if receipts:
        add_receipts(project, receipts, trusted_outputs=True)


def _summary(catalog: list[dict], candidates: list[tuple], results: list[dict], selected: int, execute: bool, project: Path) -> dict:
    statuses = [row.get("status") for row in results]
    return {
        "scanned_bnk": len(catalog),
        "compatible": len(candidates),
        "selected": selected,
        "decoded": sum(status in SUCCESS for status in statuses),
        "failed": sum(status == "FAILED" for status in statuses),
        "unknown": sum(status == "UNKNOWN" for status in statuses),
        "pending": sum(status == "PENDING" for status in statuses),
        "execute": execute,
        "manifest": str(project / "manifests" / "bnk.jsonl"),
    }


def _run_config_batch(
    root: Path,
    project: Path,
    tool: Path,
    catalog: list[dict],
    candidates: list[tuple[Path, Path, dict, dict]],
    seed_results: list[dict],
    timeout: int,
) -> dict:
    """Run wwiser in bounded config chunks, then validate/register each XML separately."""
    existing = _existing_bnk_outputs(project)
    results = list(seed_results)
    receipts = []
    work = project / "work"
    work.mkdir(parents=True, exist_ok=True)
    pending = []
    for source, target, item, base in candidates:
        rel = item["relative_path"]
        target_key = os.path.normcase(os.path.abspath(os.fspath(target))).casefold()
        row = {**base, "output": str(target.relative_to(project))}
        source_hash = sha256(source)
        row["source_sha256"] = source_hash
        prior = existing.get(target_key)
        if target.exists():
            if (
                prior
                and prior.get("source_sha256") == source_hash
                and prior.get("output_sha256") == sha256(target)
            ):
                row.update({
                    "status": "DECODED_EXISTING_VERIFIED",
                    "output_sha256": prior["output_sha256"],
                    "output_bytes": target.stat().st_size,
                })
            else:
                row.update({"status": "FAILED", "error": f"unattributed/conflicting output exists: {target}"})
            results.append(row)
            continue
        pending.append((source, target, item, base, source_hash, row))

    chunk_size = 20
    for start in range(0, len(pending), chunk_size):
        chunk = pending[start:start + chunk_size]
        with tempfile.TemporaryDirectory(prefix="bnk-batch-", dir=work) as temp_name:
            temp = Path(temp_name)
            config_path = temp / "wwconfig-batch.txt"
            expected = []
            commands = []
            config_lines = []
            for index, (source, target, item, base, source_hash, row) in enumerate(chunk):
                staging_base = temp / f"bank-{index:04d}"
                stage_xml = staging_base.with_suffix(".xml")
                args = [
                    sys.executable, str(tool), "-d", "xml", "-dn",
                    str(staging_base), str(source),
                ]
                commands.append(args)
                config_lines.append(" ".join(shlex.quote(arg) for arg in args[2:]))
                expected.append((stage_xml, source, target, item, base, source_hash, row, args))
            config_path.write_text("\n#@new\n".join(config_lines) + "\n", encoding="utf-8")
            invocation = [sys.executable, str(tool), str(config_path)]
            try:
                completed = subprocess.run(
                    invocation,
                    cwd=project,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=max(timeout, 900),
                    check=False,
                )
                batch_error = (
                    f"wwiser config exit {completed.returncode}"
                    if completed.returncode != 0 else ""
                )
                stderr = completed.stderr[-1500:]
            except Exception as exc:
                completed = None
                batch_error = f"{type(exc).__name__}: {exc}"
                stderr = ""

            for stage_xml, source, target, item, base, source_hash, row, args in expected:
                row["command"] = args
                if batch_error:
                    row["batch_error"] = batch_error
                if stderr:
                    row["stderr"] = stderr
                try:
                    if not stage_xml.is_file():
                        raise RuntimeError(batch_error or "wwiser produced no XML output")
                    validation = _validate_xml(stage_xml)
                    if sha256(source) != source_hash:
                        raise ValueError("source changed during decode")
                    output_hash = sha256(stage_xml)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    stage_xml.replace(target)
                    tool_versions = {
                        "wwiser_version": "20260808",
                        "wwiser_commit": WWISER_COMMIT,
                        "python": sys.version.split()[0],
                    }
                    row.update({
                        "status": "DECODED",
                        "output_sha256": output_hash,
                        "output_bytes": target.stat().st_size,
                        "validation": validation,
                        "tool_versions": tool_versions,
                    })
                    receipts.append(_receipt(
                        project,
                        root,
                        item["relative_path"],
                        source,
                        target,
                        "wwiser -d xml (Wwise BNK hierarchy and metadata)",
                        tool_versions,
                        source_sha256=source_hash,
                        output_sha256=output_hash,
                        status="DECODED",
                        validation=validation,
                        command=args,
                    ))
                except Exception as exc:
                    row.update({"status": "FAILED", "error": f"{type(exc).__name__}: {exc}"})
                results.append(row)

    _write_results(project, results, receipts, None)
    return _summary(catalog, candidates, results, len(candidates), True, project)


def run_bnk_batch(
    root: Path = PROJECT.parent,
    project: Path = PROJECT,
    limit: int = 20,
    execute: bool = False,
    timeout: int = 300,
    only_sources: set[str] | None = None,
) -> dict:
    """Decode Wwise BNK hierarchy metadata to mirrored XML with wwiser."""
    romfs = source_dirs(root)["romfs"]
    tool = project / "tools" / "src" / "wwiser" / "wwiser.py"
    catalog = sorted(
        (
            row for row in _scan_catalog(project)
            if row["partition"] == "romfs" and row["suffix"].lower() == ".bnk"
        ),
        key=lambda row: row["relative_path"].casefold(),
    )
    candidates = []
    results = []
    for item in catalog:
        rel = item["relative_path"]
        base = {
            "domain": "bnk",
            "partition": "romfs",
            "source": rel,
            "source_bytes": int(item["bytes"]),
            "signature": item["signature"],
        }
        if item["signature"] != "Wwise BKHD":
            results.append({**base, "status": "UNKNOWN", "reason": "expected Wwise BKHD signature"})
            continue
        relative = PurePosixPath(rel)
        if relative.is_absolute() or ".." in relative.parts or not relative.parts:
            results.append({**base, "status": "FAILED", "error": "unsafe relative path in scan catalog"})
            continue
        source = romfs.joinpath(*relative.parts)
        target = project / "decoded" / VERSION / "romfs" / Path(*relative.parts).with_suffix(".xml")
        candidates.append((source, target, item, base))

    if only_sources is not None:
        selected_names = {source.casefold() for source in only_sources}
        selected = [entry for entry in candidates if entry[2]["relative_path"].casefold() in selected_names]
    else:
        selected = candidates if not limit else candidates[:limit]
    if execute and not tool.is_file():
        raise FileNotFoundError(f"pinned wwiser source missing: {tool}")

    if execute and limit == 0 and only_sources is None:
        return _run_config_batch(root, project, tool, catalog, candidates, results, timeout)

    selected_targets = {
        os.path.normcase(os.path.abspath(os.fspath(target))).casefold()
        for _, target, _, _ in selected
    }
    existing = _existing_bnk_outputs(project)
    if execute:
        work = project / "work"
        work.mkdir(parents=True, exist_ok=True)
    receipts = []
    for source, target, item, base in candidates:
        rel = item["relative_path"]
        target_key = os.path.normcase(os.path.abspath(os.fspath(target))).casefold()
        row = {**base, "output": str(target.relative_to(project))}
        if target_key not in selected_targets:
            results.append({**row, "status": "PENDING", "reason": "outside current --limit"})
            continue
        if not execute:
            results.append({**row, "status": "DRY_RUN"})
            continue
        source_hash = sha256(source)
        row["source_sha256"] = source_hash
        prior = existing.get(target_key)
        if target.exists():
            if (
                prior
                and prior.get("source_sha256") == source_hash
                and prior.get("output_sha256") == sha256(target)
            ):
                row.update({
                    "status": "DECODED_EXISTING_VERIFIED",
                    "output_sha256": prior["output_sha256"],
                    "output_bytes": target.stat().st_size,
                })
                results.append(row)
                continue
            row.update({"status": "FAILED", "error": f"unattributed/conflicting output exists: {target}"})
            results.append(row)
            continue

        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(prefix="bnk-", dir=work) as temp_dir:
                staging_base = Path(temp_dir) / "decoded"
                staging = staging_base.with_suffix(".xml")
                command = [
                    sys.executable, str(tool), "-d", "xml", "-dn",
                    str(staging_base), str(source),
                ]
                completed = subprocess.run(
                    command,
                    cwd=project,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=timeout,
                    check=False,
                )
                row["command"] = command
                row["stdout"] = completed.stdout
                row["stderr"] = completed.stderr
                if completed.returncode != 0 or not staging.is_file():
                    raise RuntimeError(
                        f"wwiser exit {completed.returncode}: {completed.stderr[-1000:]}"
                    )
                validation = _validate_xml(staging)
                if sha256(source) != source_hash:
                    raise ValueError("source changed during decode")
                output_hash = sha256(staging)
                staging.replace(target)
            tool_versions = {
                "wwiser_version": "20260808",
                "wwiser_commit": WWISER_COMMIT,
                "python": sys.version.split()[0],
            }
            row.update({
                "status": "DECODED",
                "output_sha256": output_hash,
                "output_bytes": target.stat().st_size,
                "validation": validation,
                "tool_versions": tool_versions,
            })
            receipts.append(_receipt(
                project, root, rel, source, target,
                "wwiser -d xml (Wwise BNK hierarchy and metadata)",
                tool_versions,
                source_sha256=source_hash,
                output_sha256=output_hash,
                status="DECODED",
                validation=validation,
                command=command,
            ))
        except Exception as exc:
            row.update({"status": "FAILED", "error": f"{type(exc).__name__}: {exc}"})
        results.append(row)

    _write_results(project, results, receipts, only_sources)
    return _summary(catalog, candidates, results, len(selected), execute, project)
