"""Decode supported LGPE NX BFFNT files and their embedded texture sheets."""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path, PurePosixPath, PureWindowsPath

from . import assets_decode
from .batch import _receipt, _scan_catalog, merge_failures, write_jsonl_selected
from .bffnt_decode import parse_bffnt
from .core import PROJECT, VERSION, add_receipts, ensure_inside, sha256, source_dirs
from .font_batch import _output_inside_decoded

METHOD = "lgpe_research.bffnt_batch/nx_ffnt"
SWITCH_TOOLBOX = "3fcb87f1fea25ad56db139b0d9577db591f54118"
BNTX_EXTRACTOR = "2c08e8e55fcc666ba6568a102f36dabd6c584e25"


def _path_key(path: Path) -> str:
    return os.path.normcase(os.path.abspath(os.fspath(path))).casefold()


def _write_exclusive(path: Path, data: bytes, project: Path) -> tuple[int, int]:
    _output_inside_decoded(path, project)
    path.parent.mkdir(parents=True, exist_ok=True)
    _output_inside_decoded(path, project)
    with path.open("xb") as stream:
        identity = os.fstat(stream.fileno())
        try:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        except BaseException:
            try:
                current = path.stat()
            except FileNotFoundError:
                pass
            else:
                if (current.st_dev, current.st_ino) == (identity.st_dev, identity.st_ino):
                    try:
                        path.unlink(missing_ok=True)
                    except OSError:
                        pass
            raise
    return identity.st_dev, identity.st_ino


def _remove_created(created: list[tuple[Path, tuple[int, int]]]) -> None:
    for path, identity in reversed(created):
        try:
            current = path.stat()
        except FileNotFoundError:
            continue
        if (current.st_dev, current.st_ino) == identity:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass


def _legacy_command_report_matches(previous: Path, staged: Path) -> bool:
    """Recognize only the prior JSON form differing by transient command logs."""
    try:
        report = json.loads(previous.read_text(encoding="utf-8"))
        sheets = report["texture_glyph"]["sheets"]
        if len(sheets) != 1:
            return False
        commands = sheets[0].pop("commands", None)
        if not isinstance(commands, list) or not commands or not all(
            isinstance(command, dict) for command in commands
        ):
            return False
        normalized = (json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        return normalized == staged.read_bytes()
    except (OSError, ValueError, TypeError, KeyError, IndexError):
        return False


def run_bffnt_batch(
    root: Path = PROJECT.parent,
    project: Path = PROJECT,
    limit: int = 20,
    execute: bool = False,
    ffmpeg: Path | None = None,
    only_sources: set[str] | None = None,
) -> dict:
    """Decode catalogued NX FFNT files without modifying any source file."""
    ffmpeg = ffmpeg or Path(r"D:\Tool\ffmpeg-8.0.1-full_build\bin\ffmpeg.exe")
    romfs = source_dirs(root)["romfs"]
    catalog = sorted(
        (row for row in _scan_catalog(project)
         if row["partition"] == "romfs" and row["suffix"].casefold() == ".bffnt"),
        key=lambda row: (row["relative_path"].casefold(), row["relative_path"]),
    )
    candidates = []
    rows: list[dict] = []
    for item in catalog:
        relative_text = item["relative_path"].replace("\\", "/")
        relative = PurePosixPath(relative_text)
        windows_relative = PureWindowsPath(relative_text)
        if (
            relative.is_absolute() or windows_relative.drive
            or ".." in relative.parts or not relative.parts
        ):
            candidates.append((None, item, relative_text, None, "unsafe catalog source path"))
            continue
        source = None
        path_error = None
        try:
            source = ensure_inside(romfs.joinpath(*relative.parts), romfs)
        except (OSError, RuntimeError, ValueError) as exc:
            path_error = f"invalid source path: {type(exc).__name__}: {exc}"
        output = project / "decoded" / VERSION / "romfs" / Path(*relative.parts).with_suffix(".json")
        candidates.append((source, item, relative_text, output, path_error))

    if only_sources is None:
        selected = candidates if not limit else candidates[:limit]
    else:
        selected_names = {source.replace("\\", "/").casefold() for source in only_sources}
        selected = [entry for entry in candidates if entry[2].casefold() in selected_names]
    selected_names = {entry[2].casefold() for entry in selected}
    project_work = project / "work"
    project_work.mkdir(parents=True, exist_ok=True)
    receipts = []

    for source, item, relative_text, output_json, path_error in candidates:
        relative = PurePosixPath(relative_text)
        contents_relative = relative.as_posix() + ".contents"
        planned_outputs = [
            (relative.with_suffix(".json")).as_posix(),
            f"{contents_relative}/Sheet_0.bntx",
            f"{contents_relative}/Sheet_0.png",
        ]
        row = {
            "domain": "bffnt",
            "source": relative_text,
            "partition": "romfs",
            "source_bytes": int(item["bytes"]),
            "signature": item["signature"],
            "decoder": METHOD,
            "tool_versions": {
                "Switch-Toolbox": SWITCH_TOOLBOX,
                "BNTX-Extractor": BNTX_EXTRACTOR,
            },
            "output": output_json.relative_to(project).as_posix() if output_json else None,
            "planned_outputs": [
                (Path("decoded") / VERSION / "romfs" / Path(value)).as_posix()
                for value in planned_outputs
            ],
        }
        if relative_text.casefold() not in selected_names:
            row.update({"status": "PENDING", "reason": "outside current --limit or source selection"})
            rows.append(row)
            continue
        if path_error:
            row.update({"status": "FAILED", "error": path_error})
            rows.append(row)
            continue
        if item["signature"] != "BFFNT":
            row.update({"status": "UNKNOWN", "reason": "catalogued .bffnt does not have the observed FFNT signature"})
            rows.append(row)
            continue
        if not execute:
            row["status"] = "DRY_RUN"
            rows.append(row)
            continue

        assert source is not None and output_json is not None
        source_hash = sha256(source)
        row["source_sha256"] = source_hash
        staged_files: list[tuple[str, Path, Path, dict]] = []
        created: list[tuple[Path, tuple[int, int]]] = []
        try:
            _output_inside_decoded(output_json, project)
            source_data = source.read_bytes()
            report, sheets = parse_bffnt(source_data)
            if sha256(source) != source_hash:
                raise ValueError("BFFNT source SHA-256 changed during parsing")
            if len(sheets) != 1:
                raise NotImplementedError(
                    f"BFFNT has {len(sheets)} texture sheets; only the observed single-sheet layout is validated"
                )
            if sheets[0][:4] != b"BNTX":
                raise NotImplementedError("BFFNT texture sheet is not a supported embedded BNTX")

            with tempfile.TemporaryDirectory(prefix="bffnt-", dir=project_work) as temporary:
                staging_root = Path(temporary)
                staged_json = staging_root / output_json.name
                staging_contents = staging_root / f"{output_json.name}.contents"
                staging_contents.mkdir()
                sheet = report["texture_glyph"]["sheets"][0]
                internal_bntx = str(sheet["internal_path"])
                staged_bntx = staging_contents / internal_bntx
                staged_bntx.write_bytes(sheets[0])
                if sha256(staged_bntx) != sheet["sha256"]:
                    raise ValueError("staged BNTX hash differs from the embedded TGLP sheet bytes")
                png_relative = str(PurePosixPath(internal_bntx).with_suffix(".png"))
                staged_png = staging_contents / png_relative
                commands = []
                conversion = assets_decode.convert_bntx(
                    staged_bntx, staged_png, project, ffmpeg, commands,
                )
                png_validation = assets_decode.validate_output(staged_png)
                if (conversion.get("width"), conversion.get("height")) != (
                    report["texture_glyph"]["sheet_width"],
                    report["texture_glyph"]["sheet_height"],
                ):
                    raise ValueError("embedded BNTX image dimensions differ from TGLP sheet dimensions")
                sheet.update({
                    "output_bntx_internal_path": internal_bntx,
                    "output_png_internal_path": png_relative,
                    "output_png_bytes": staged_png.stat().st_size,
                    "output_png_sha256": sha256(staged_png),
                    "png_validation": png_validation,
                    "conversion": conversion,
                })
                tool_versions = {
                    "Switch-Toolbox": SWITCH_TOOLBOX,
                    "BNTX-Extractor": BNTX_EXTRACTOR,
                    "ffmpeg": {"executable_sha256": sha256(ffmpeg)},
                }
                report["source"] = {
                    "version": "Pokemon Let's Go Pikachu 1.0.2",
                    "partition": "romfs",
                    "relative_path": relative_text,
                    "bytes": len(source_data),
                    "sha256": source_hash,
                }
                report["decoder"] = METHOD
                report["tool_versions"] = tool_versions
                report["outputs"] = [
                    {"role": "structure", "path": output_json.relative_to(project).as_posix()},
                    {
                        "role": "embedded_texture",
                        "path": (
                            Path("decoded") / VERSION / "romfs" / Path(contents_relative) / internal_bntx
                        ).as_posix(),
                        "sha256": sha256(staged_bntx),
                        "bytes": staged_bntx.stat().st_size,
                    },
                    {
                        "role": "texture_png",
                        "path": (
                            Path("decoded") / VERSION / "romfs" / Path(contents_relative) / png_relative
                        ).as_posix(),
                        "sha256": sha256(staged_png),
                        "bytes": staged_png.stat().st_size,
                    },
                ]
                staged_json.write_text(
                    json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                    newline="\n",
                )
                if json.loads(staged_json.read_text(encoding="utf-8")) != report:
                    raise ValueError("BFFNT JSON serialization did not round-trip")
                output_contents = output_json.with_name(f"{relative.name}.contents")
                artifact_specs = [
                    ("structure", staged_json, output_json, None, None),
                    ("embedded_texture", staged_bntx, output_contents / internal_bntx, 0, internal_bntx),
                    ("texture_png", staged_png, output_contents / png_relative, 0, png_relative),
                ]
                expected_hashes = {
                    _path_key(destination): sha256(staging)
                    for _, staging, destination, _, _ in artifact_specs
                }
                legacy_command_reports: dict[str, str] = {}
                for _, staging, destination, _, _ in artifact_specs:
                    _output_inside_decoded(destination, project)
                    if destination.exists() and sha256(destination) != expected_hashes[_path_key(destination)]:
                        key = _path_key(destination)
                        if (
                            destination == output_json
                            and _legacy_command_report_matches(destination, staging)
                        ):
                            legacy_command_reports[key] = sha256(destination)
                        else:
                            raise ValueError(f"conflicting decoded output exists: {destination}")

                for _, staging, destination, _, _ in artifact_specs:
                    if destination.exists():
                        continue
                    try:
                        identity = _write_exclusive(destination, staging.read_bytes(), project)
                    except FileExistsError:
                        if sha256(destination) != expected_hashes[_path_key(destination)]:
                            raise ValueError(f"competing writer created conflicting output: {destination}")
                    else:
                        created.append((destination, identity))

                if sha256(source) != source_hash:
                    raise ValueError("BFFNT source SHA-256 changed during conversion")
                for key, previous_hash in legacy_command_reports.items():
                    match = next(
                        (staging, destination)
                        for _, staging, destination, _, _ in artifact_specs
                        if _path_key(destination) == key
                    )
                    staging, destination = match
                    _output_inside_decoded(destination, project)
                    current_hash = sha256(destination)
                    if current_hash == expected_hashes[key]:
                        continue
                    if (
                        current_hash != previous_hash
                        or not _legacy_command_report_matches(destination, staging)
                    ):
                        raise ValueError(f"decoded output changed during legacy JSON normalization: {destination}")
                    os.replace(staging, destination)
                    _output_inside_decoded(destination, project)
                    if sha256(destination) != expected_hashes[key]:
                        raise ValueError(f"normalized BFFNT JSON differs from staged bytes: {destination}")
                    row["normalized_legacy_command_log"] = True
                output_hashes = {
                    _path_key(destination): sha256(destination)
                    for _, _, destination, _, _ in artifact_specs
                }
                if output_hashes != expected_hashes:
                    raise ValueError("one or more published BFFNT outputs differ from staged bytes")

                for role, staging, destination, container_index, internal_path in artifact_specs:
                    digest = output_hashes[_path_key(destination)]
                    tool_record = (
                        {"Switch-Toolbox": SWITCH_TOOLBOX}
                        if role != "texture_png" else tool_versions
                    )
                    receipts.append(_receipt(
                        project, root, relative_text, source, destination, METHOD,
                        tool_record, source_sha256=source_hash,
                        output_sha256=digest,
                        internal_path=internal_path,
                        container_index=container_index,
                        artifact_role=role,
                        command=commands if role == "texture_png" else [],
                        validation=(png_validation if role == "texture_png" else {
                            "kind": role,
                            "signature": "BNTX" if role == "embedded_texture" else "JSON",
                        }),
                    ))
                row.update({
                    "status": "DECODED",
                    "source_sha256": source_hash,
                    "output_sha256": sha256(output_json),
                    "output_bytes": output_json.stat().st_size,
                    "output_paths": [
                        receipt["output_file"] for receipt in receipts
                        if receipt.get("relative_source", "").casefold() == relative_text.casefold()
                    ],
                    "section_count": len(report["sections"]),
                    "texture_sheet_count": len(sheets),
                    "glyph_width_entries": sum(
                        section["entry_count"] for section in report["character_width_sections"]
                    ),
                    "character_map_sections": len(report["character_map_sections"]),
                    "conversion": conversion,
                    "tool_versions": tool_versions,
                    "commands": commands,
                    "receipt_registered": True,
                })
            rows.append(row)
        except NotImplementedError as exc:
            _remove_created(created)
            row.update({"status": "UNSUPPORTED", "reason": f"{type(exc).__name__}: {exc}"})
            rows.append(row)
        except Exception as exc:
            _remove_created(created)
            row.update({
                "status": "FAILED",
                "error": f"{type(exc).__name__}: {exc}",
                "retry_command": "uv run lgpe retry-failed --domain bffnt --execute",
            })
            rows.append(row)

    if execute and receipts:
        add_receipts(
            project, receipts, trusted_outputs=True,
            replace_source_receipts=True,
        )
        registered = {str(row["relative_source"]).casefold() for row in receipts}
        for row in rows:
            if row.get("status") == "DECODED" and str(row.get("source", "")).casefold() in registered:
                row["receipt_registered"] = True

    manifest = project / "manifests" / "bffnt.jsonl"
    write_jsonl_selected(manifest, rows, only_sources)
    merge_failures(
        project,
        [
            {key: row.get(key) for key in ("domain", "source", "status", "error")}
            for row in rows if row.get("status") in {"FAILED", "UNSUPPORTED"}
        ],
        resolved=[{"domain": "bffnt", "source": row["source"]}
                  for row in rows if row.get("status") == "DECODED"],
    )
    statuses = [row.get("status") for row in rows]
    return {
        "catalogued": len(catalog),
        "compatible": sum(source is not None for source, *_ in candidates),
        "selected": len(selected),
        "decoded": sum(status == "DECODED" for status in statuses),
        "failed": sum(status == "FAILED" for status in statuses),
        "unknown": sum(status == "UNKNOWN" for status in statuses),
        "unsupported": sum(status == "UNSUPPORTED" for status in statuses),
        "pending": sum(status == "PENDING" for status in statuses),
        "manifest": str(manifest),
    }
