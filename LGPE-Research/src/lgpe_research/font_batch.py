"""Bounded, provenance-preserving BFOTF to OpenType batch conversion."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PurePosixPath, PureWindowsPath

from .batch import (
    _ContainedPathResolver, _receipt, _resolve_receipt_output_path,
    _resolve_receipt_source_path, _scan_catalog, existing_domain_outputs,
    merge_failures, write_jsonl_selected,
)
from .core import PROJECT, VERSION, add_receipts, ensure_inside, sha256, source_dirs
from .fonts_decode import decode_bfotf, inspect_opentype


SWITCH_TOOLBOX = {
    "commit": "3fcb87f1fea25ad56db139b0d9577db591f54118",
    "license": "GPL-3.0",
    "source_file": "File_Format_Library/FileFormats/Font/BFTTF.cs",
}
METHOD = "lgpe_research.font_batch/BFTTF wordwise XOR to OpenType"


def _output_key(path: Path) -> str:
    return os.path.normcase(os.path.abspath(os.fspath(path))).casefold()


def _output_inside_decoded(output: Path, project: Path) -> Path:
    decoded_root = project / "decoded"
    resolved_decoded_root = decoded_root.resolve()
    expected_decoded_root = project.resolve() / "decoded"
    if _output_key(resolved_decoded_root) != _output_key(expected_decoded_root):
        raise ValueError(f"decoded output root redirects through a symlink: {decoded_root}")
    resolved_output = ensure_inside(output, decoded_root)
    if _output_key(resolved_output) != _output_key(output):
        raise ValueError(f"decoded output path traverses a symlink: {output}")
    return resolved_output


def _existing_font_receipts(
    project: Path, root: Path, sources: set[str],
) -> dict[str, dict]:
    """Find this decoder's prior central receipts without parsing unrelated rows."""
    manifest = project / "manifests" / "outputs.jsonl"
    wanted = {source.replace("\\", "/").casefold() for source in sources}
    if not manifest.is_file() or not wanted:
        return {}

    decoded_paths = _ContainedPathResolver(project / "decoded")
    source_paths = _ContainedPathResolver(source_dirs(root)["romfs"])
    receipts: dict[str, dict] = {}
    with manifest.open("r", encoding="utf-8") as stream:
        for line in stream:
            folded = line.casefold()
            if not any(source in folded for source in wanted):
                continue
            receipt = json.loads(line)
            source = str(receipt.get("relative_source", "")).replace("\\", "/").casefold()
            if (
                source not in wanted or receipt.get("method") != METHOD
                or receipt.get("partition") != "romfs"
                or receipt.get("status") != "DECODED"
            ):
                continue
            relative = PurePosixPath(source)
            expected_output = (
                decoded_paths.root / VERSION / "romfs"
                / Path(*relative.with_suffix(".otf").parts)
            )
            expected_output = decoded_paths.resolve(expected_output)
            expected_source = source_paths.resolve(
                source_paths.root.joinpath(*relative.parts)
            )
            recorded_output = str(receipt.get("output_file", ""))
            recorded_source = str(receipt.get("source_file", ""))
            # Native absolute paths must name this exact project/source tree;
            # foreign Windows/WSL paths are mapped by the same verifier helpers.
            if (
                Path(recorded_output).is_absolute()
                and _output_key(Path(recorded_output)) != _output_key(expected_output)
            ) or (
                Path(recorded_source).is_absolute()
                and _output_key(Path(recorded_source)) != _output_key(expected_source)
            ):
                continue
            try:
                if _resolve_receipt_output_path(
                    recorded_output, expected_output, decoded_paths,
                ) != expected_output:
                    continue
                if _resolve_receipt_source_path(
                    recorded_source, expected_source, source_paths,
                ) != expected_source:
                    continue
            except (OSError, RuntimeError, ValueError):
                continue
            receipts[source] = receipt
            if len(receipts) == len(wanted):
                break
    return receipts


def run_font_batch(
    root: Path = PROJECT.parent,
    project: Path = PROJECT,
    limit: int = 20,
    execute: bool = False,
    only_sources: set[str] | None = None,
) -> dict:
    """Convert catalogued ROMFS BFOTF files to path-mirrored OTF outputs."""
    romfs = source_dirs(root)["romfs"]
    catalog = sorted(
        (
            row for row in _scan_catalog(project)
            if row["partition"].casefold() == "romfs"
            and row["suffix"].casefold() == ".bfotf"
        ),
        key=lambda row: (row["relative_path"].casefold(), row["relative_path"]),
    )
    candidates: list[tuple[Path | None, dict, str, Path | None, str | None]] = []
    for item in catalog:
        rel = item["relative_path"].replace("\\", "/")
        relative = PurePosixPath(rel)
        windows_relative = PureWindowsPath(rel)
        if (
            relative.is_absolute() or windows_relative.drive
            or ".." in relative.parts or not relative.parts
        ):
            candidates.append((
                None, item, rel, None,
                f"unsafe relative source path: {rel!r}",
            ))
            continue
        output = project / "decoded" / VERSION / "romfs" / Path(*relative.parts).with_suffix(".otf")
        try:
            source = ensure_inside(romfs.joinpath(*relative.parts), romfs)
            candidates.append((source, item, rel, output, None))
        except (OSError, RuntimeError, ValueError) as exc:
            candidates.append((
                None, item, rel, output,
                f"invalid source path: {type(exc).__name__}: {exc}",
            ))

    if only_sources is None:
        selected = candidates if not limit else candidates[:limit]
    else:
        selected_names = {source.replace("\\", "/").casefold() for source in only_sources}
        selected = [entry for entry in candidates if entry[2].casefold() in selected_names]
    selected_names = {entry[2].casefold() for entry in selected}
    prior_outputs = existing_domain_outputs(project, "font")
    registered_font_receipts: dict[str, dict] | None = None
    manifest_rows = []
    receipts = []
    for source, item, rel, output, path_error in candidates:
        row = {
            "domain": "font",
            "source": rel,
            "partition": "romfs",
            "source_bytes": int(item["bytes"]),
            "signature": item["signature"],
            "output": output.relative_to(project).as_posix() if output else None,
            "decoder": METHOD,
            "tool_versions": {"Switch-Toolbox": SWITCH_TOOLBOX},
        }
        if rel.casefold() not in selected_names:
            row.update({"status": "PENDING", "reason": "outside current --limit or source selection"})
            manifest_rows.append(row)
            continue
        if path_error:
            row.update({
                "status": "FAILED",
                "error": path_error,
                "retry_command": "uv run lgpe retry-failed --domain font --execute",
            })
            manifest_rows.append(row)
            continue
        if not execute:
            row["status"] = "DRY_RUN"
            manifest_rows.append(row)
            continue

        try:
            assert source is not None and output is not None
            _output_inside_decoded(output, project)
            source_hash = sha256(source)
            row["source_sha256"] = source_hash
            output_key = _output_key(output)
            prior = prior_outputs.get(output_key)
            if output.exists():
                existing_hash = sha256(output)
                prior_row = prior.get("manifest_row", {}) if prior else {}
                prior_hashes_match = bool(
                    prior
                    and prior.get("source_sha256") == source_hash
                    and prior.get("output_sha256") == existing_hash
                )
                if prior_row.get("receipt_registered") is True and prior_hashes_match:
                    receipt_is_registered = True
                    registered_receipt = None
                else:
                    if registered_font_receipts is None:
                        registered_font_receipts = _existing_font_receipts(
                            project, root,
                            {entry[2] for entry in selected if entry[0] is not None},
                        )
                    registered_receipt = registered_font_receipts.get(rel.casefold())
                    receipt_is_registered = bool(
                        registered_receipt
                        and registered_receipt.get("source_sha256") == source_hash
                        and registered_receipt.get("output_sha256") == existing_hash
                    )
                if receipt_is_registered:
                    validation = inspect_opentype(output.read_bytes())
                    row.update({
                        key: value for key, value in prior_row.items()
                        if key not in row and key != "status"
                    })
                    for key in ("conversion", "validation", "command"):
                        if key not in row and registered_receipt:
                            row[key] = registered_receipt.get(key)
                    row.update({
                        "status": "DECODED_EXISTING_VERIFIED",
                        "source_sha256": source_hash,
                        "output_sha256": existing_hash,
                        "output_bytes": output.stat().st_size,
                        "validation": validation,
                        "receipt_registered": True,
                    })
                else:
                    decoded, conversion = decode_bfotf(source.read_bytes())
                    validation = inspect_opentype(output.read_bytes())
                    existing_hash = sha256(output)
                    if sha256(source) != source_hash:
                        raise ValueError("source SHA-256 changed during conversion")
                    if existing_hash == hashlib.sha256(decoded).hexdigest():
                        command = [
                            "uv", "run", "lgpe", "decode-fonts",
                            "--root", str(root), "--limit", str(limit), "--execute",
                        ]
                        row.update({
                            "status": "DECODED_EXISTING_VERIFIED",
                            "output_sha256": existing_hash,
                            "output_bytes": output.stat().st_size,
                            "validation": validation,
                            "conversion": conversion,
                            "recovered_receipt": True,
                            "command": command,
                        })
                        receipts.append(_receipt(
                            project, root, rel, source, output, METHOD,
                            {"Switch-Toolbox": SWITCH_TOOLBOX},
                            source_sha256=source_hash,
                            output_sha256=existing_hash,
                            validation=validation,
                            conversion=conversion,
                            command=command,
                        ))
                    else:
                        row.update({
                            "status": "FAILED",
                            "error": f"unattributed or conflicting output already exists: {output}",
                            "retry_command": "uv run lgpe retry-failed --domain font --execute",
                        })
                manifest_rows.append(row)
                continue

            decoded, conversion = decode_bfotf(source.read_bytes())
            validation = inspect_opentype(decoded)
            if sha256(source) != source_hash:
                raise ValueError("source SHA-256 changed during conversion")
            _output_inside_decoded(output, project)
            output.parent.mkdir(parents=True, exist_ok=True)
            _output_inside_decoded(output, project)
            created_identity: tuple[int, int] | None = None
            try:
                with output.open("xb") as stream:
                    stat = os.fstat(stream.fileno())
                    created_identity = (stat.st_dev, stat.st_ino)
                    stream.write(decoded)
                    stream.flush()
                    os.fsync(stream.fileno())
            except BaseException:
                if created_identity is not None:
                    try:
                        current = output.stat()
                    except FileNotFoundError:
                        pass
                    else:
                        if (current.st_dev, current.st_ino) == created_identity:
                            try:
                                output.unlink(missing_ok=True)
                            except OSError:
                                pass
                raise

            output_hash = sha256(output)
            command = [
                "uv", "run", "lgpe", "decode-fonts",
                "--root", str(root), "--limit", str(limit), "--execute",
            ]
            row.update({
                "status": "DECODED",
                "output_sha256": output_hash,
                "output_bytes": output.stat().st_size,
                "validation": validation,
                "conversion": conversion,
                "command": command,
            })
            receipts.append(_receipt(
                project, root, rel, source, output, METHOD,
                {"Switch-Toolbox": SWITCH_TOOLBOX},
                source_sha256=source_hash,
                output_sha256=output_hash,
                validation=validation,
                conversion=conversion,
                command=command,
            ))
        except (RuntimeError, ValueError) as exc:
            message = f"{type(exc).__name__}: {exc}"
            is_unknown = "unsupported BFOTF magic" in str(exc)
            row.update({
                "status": "UNKNOWN" if is_unknown else "FAILED",
                "reason" if is_unknown else "error": message,
            })
            if not is_unknown:
                row["retry_command"] = "uv run lgpe retry-failed --domain font --execute"
        except OSError as exc:
            row.update({
                "status": "FAILED",
                "error": f"{type(exc).__name__}: {exc}",
                "retry_command": "uv run lgpe retry-failed --domain font --execute",
            })
        manifest_rows.append(row)

    if execute and receipts:
        add_receipts(
            project, receipts, trusted_outputs=True,
            replace_source_receipts=True,
        )
        registered_sources = {
            str(receipt.get("relative_source", "")).replace("\\", "/").casefold()
            for receipt in receipts
        }
        for row in manifest_rows:
            if (
                row.get("status") in {"DECODED", "DECODED_EXISTING_VERIFIED"}
                and str(row.get("source", "")).casefold() in registered_sources
            ):
                row["receipt_registered"] = True

    manifest = project / "manifests" / "fonts.jsonl"
    write_jsonl_selected(manifest, manifest_rows, only_sources)
    merge_failures(
        project,
        [
            {key: row.get(key) for key in ("domain", "source", "status", "error")}
            for row in manifest_rows if row.get("status") == "FAILED"
        ],
        resolved=[
            {"domain": "font", "source": row["source"]}
            for row in manifest_rows
            if row.get("status") in {"DECODED", "DECODED_EXISTING_VERIFIED"}
        ],
    )
    statuses = [row.get("status") for row in manifest_rows]
    return {
        "catalogued": len(catalog),
        "compatible": sum(source is not None for source, *_ in candidates),
        "selected": len(selected),
        "decoded": sum(status in {"DECODED", "DECODED_EXISTING_VERIFIED"} for status in statuses),
        "failed": sum(status == "FAILED" for status in statuses),
        "unknown": sum(status == "UNKNOWN" for status in statuses),
        "pending": sum(status == "PENDING" for status in statuses),
        "execute": execute,
        "manifest": str(manifest),
    }
