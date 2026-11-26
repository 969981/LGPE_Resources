"""Batch decoders and canonical evidence registration for LGPE 1.0.2."""
from __future__ import annotations

import csv
import json
import os
import struct
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath, PureWindowsPath

from . import archive_reader, gamedata_decode, localized_sort_decode
from .core import (
    NCA, PROJECT, VERSION, decode_destination, ensure_inside, probe,
    sha256, source_dirs, add_receipts, _trusted_decoded_path,
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".partial")
    temporary.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )
    temporary.replace(path)


def read_source_list(path: Path) -> set[str]:
    """Read normalized ROMFS-relative source paths, one per line."""
    return {
        line.strip().replace("\\", "/")
        for line in path.read_text(encoding="utf-8-sig").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }



def write_jsonl_selected(
    path: Path, rows: list[dict], only_sources: set[str] | None = None,
) -> None:
    completed = {
        "DECODED", "DECODED_EXISTING_VERIFIED", "CROSS_VALIDATED",
        "STRUCTURE_DECODED_RENDER_UNSUPPORTED", "FAILED", "UNSUPPORTED", "UNKNOWN",
    }
    if only_sources is None:
        if not path.is_file() or not any(
            row.get("status") in {"PENDING", "DRY_RUN"} for row in rows
        ):
            write_jsonl(path, rows)
            return
        previous = [
            json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        by_source = {str(row.get("source", "")).casefold(): row for row in previous}
        for row in rows:
            source = str(row.get("source", "")).casefold()
            old = by_source.get(source)
            if row.get("status") in {"PENDING", "DRY_RUN"} and old and old.get("status") in completed:
                continue
            by_source[source] = row
        write_jsonl(path, list(by_source.values()))
        return

    selected = {source.casefold() for source in only_sources}
    previous = []
    if path.is_file():
        previous = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    by_source = {str(row.get("source", "")).casefold(): row for row in previous}
    for row in rows:
        source = str(row.get("source", "")).casefold()
        if source in selected:
            by_source[source] = row
    write_jsonl(path, list(by_source.values()))


def merge_failures(
    project: Path, additions: list[dict], resolved: list[dict] | None = None,
) -> list[dict]:
    path = project / "manifests" / "failures.jsonl"
    rows = []
    if path.is_file():
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    resolved_keys = {
        (str(row.get("domain", "")).casefold(), str(row.get("source", "")).casefold())
        for row in (resolved or []) if row.get("domain") and row.get("source")
    }
    if resolved_keys:
        rows = [
            row for row in rows
            if (str(row.get("domain", "")).casefold(), str(row.get("source", "")).casefold()) not in resolved_keys
        ]
    keys = {(row.get("domain"), row.get("source"), row.get("status"), row.get("error")) for row in rows}
    for row in additions:
        key = (row.get("domain"), row.get("source"), row.get("status"), row.get("error"))
        if key not in keys:
            rows.append(row)
            keys.add(key)
    write_jsonl(path, rows)
    return rows


def _source(root: Path, rel: str, partition: str = "romfs") -> Path:
    base = source_dirs(root)[partition]
    return ensure_inside(base / Path(rel), base)


def _receipt(
    project: Path, root: Path, rel: str, source: Path, output: Path,
    method: str, tool_version, status: str = "DECODED",
    partition: str = "romfs", source_sha256: str | None = None,
    output_sha256: str | None = None, **metadata,
) -> dict:
    source = Path(os.path.abspath(os.fspath(source)))
    output = _trusted_decoded_path(output, project)
    return {
        "timestamp_utc": utc_now(),
        "version": VERSION,
        "source_version": "Pokemon Let's Go Pikachu 1.0.2",
        "nca_folder": NCA,
        "partition": partition,
        "relative_source": rel.replace("\\", "/"),
        "source_file": str(source),
        "source_sha256": source_sha256 or sha256(source),
        "output_file": str(output),
        "output_sha256": output_sha256 or sha256(output),
        "output_size": output.stat().st_size,
        "method": method,
        "tool_version": tool_version,
        "status": status,
        **metadata,
    }


def register_sample_evidence(root: Path = PROJECT.parent, project: Path = PROJECT) -> dict:
    """Rehash and register outputs already produced by the three sample units."""
    romfs = source_dirs(root)["romfs"]
    receipts: list[dict] = []
    failures: list[dict] = []
    resolved: list[dict] = []
    seen = {"archives": 0, "gamedata": 0, "assets": 0}

    archive_log = project / "work" / "archive-results.jsonl"
    if archive_log.is_file():
        for line in archive_log.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            container = json.loads(line)
            if container.get("status") != "DECODED":
                failures.append({"domain": "archive", **container})
                continue
            source = _source(root, container["source"])
            outbase = Path(container["output"])
            source_hash = sha256(source)
            for member in container.get("members", []):
                target = outbase.joinpath(*PurePosixPath(member["internal_path"]).parts)
                try:
                    ensure_inside(target, project / "decoded")
                    if source_hash != container["source_sha256"]:
                        raise ValueError("source SHA256 differs from archive evidence")
                    if sha256(target) != member["sha256"]:
                        raise ValueError("member SHA256 differs from archive evidence")
                    receipts.append(_receipt(
                        project, root, container["source"], source, target,
                        container["method"],
                        container["source_references"],
                        source_sha256=source_hash, output_sha256=member["sha256"],
                        status="DECODED",
                        internal_path=member["internal_path"],
                        container_index=member["index"],
                        container_source_sha256=container["source_sha256"],
                        container_header_hex=container["header_hex"],
                        folder_hash=member.get("folder_hash"),
                        filename_hash=member.get("filename_hash"),
                        full_path_hash=member.get("full_path_hash"),
                        name_resolution=member.get("name_resolution"),
                        compression=member.get("compression"),
                        packed_offset=member.get("offset"),
                        packed_size=member.get("packed_size"),
                        packed_sha256=member.get("packed_sha256"),
                        hash_corpus_sha256=container.get("hash_corpus_sha256"),
                        command="uv run python -m lgpe_research.archive_reader --execute",
                    ))
                    seen["archives"] += 1
                    resolved.append({"domain": "archive", "source": container["source"]})
                except (OSError, ValueError) as exc:
                    failures.append({
                        "domain": "archive", "source": container["source"],
                        "internal_path": member.get("internal_path"),
                        "status": "FAILED", "error": f"{type(exc).__name__}: {exc}",
                    })

    game_log = project / "decoded" / "gamedata-sample-evidence.json"
    if game_log.is_file():
        for record in json.loads(game_log.read_text(encoding="utf-8")):
            if record.get("status") != "DECODED":
                failures.append({"domain": "gamedata", **record})
                continue
            rel = record["source"]
            source = _source(root, rel)
            target = project / Path(record["output"])
            try:
                ensure_inside(target, project / "decoded")
                if sha256(source) != record["input_sha256"]:
                    raise ValueError("source SHA256 differs from decoder evidence")
                if sha256(target) != record["output_sha256"]:
                    raise ValueError("output SHA256 differs from decoder evidence")
                receipts.append(_receipt(
                    project, root, rel, source, target,
                    "lgpe_research.gamedata_decode/" + gamedata_decode.SCHEMA,
                    record.get("tool_commits", {}),
                    source_sha256=record["input_sha256"],
                    output_sha256=record["output_sha256"],
                    status="CROSS_VALIDATED",
                    companion_sha256=record.get("tbl_sha256"),
                    count=record.get("count"),
                    slot_count=record.get("slot_count"),
                    unpaired_labels=record.get("unpaired_labels"),
                    command="uv run python -m lgpe_research.gamedata_decode --execute",
                ))
                seen["gamedata"] += 1
                resolved.append({"domain": "gamedata", "source": rel})
            except (OSError, ValueError) as exc:
                failures.append({
                    "domain": "gamedata", "source": rel, "status": "FAILED",
                    "error": f"{type(exc).__name__}: {exc}",
                })

    asset_log = project / "logs" / "assets_samples.jsonl"
    if asset_log.is_file():
        for line in asset_log.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            record = json.loads(line)
            status = record.get("status", "")
            if status not in {"DECODED", "STRUCTURE_DECODED_RENDER_UNSUPPORTED"}:
                failures.append({"domain": str(record.get("kind", "asset")), **record})
                continue
            rel = record["source"]
            source = _source(root, rel)
            target = project / Path(record["output"])
            try:
                ensure_inside(target, project / "decoded")
                if sha256(source) != record["source_sha256"]:
                    raise ValueError("source SHA256 differs from asset evidence")
                if sha256(target) != record["output_sha256"]:
                    raise ValueError("output SHA256 differs from asset evidence")
                receipts.append(_receipt(
                    project, root, rel, source, target,
                    "lgpe_research.assets_decode/" + str(record.get("kind")),
                    record.get("tools", {}),
                    source_sha256=record["source_sha256"],
                    output_sha256=record["output_sha256"],
                    status=status,
                    validation=record.get("validation"),
                    command=record.get("commands", []),
                ))
                seen["assets"] += 1
                resolved.append({"domain": str(record.get("kind", "asset")), "source": rel})
            except (OSError, ValueError) as exc:
                failures.append({
                    "domain": str(record.get("kind", "asset")), "source": rel, "status": "FAILED",
                    "error": f"{type(exc).__name__}: {exc}",
                })

    add_receipts(project, receipts, trusted_outputs=True)
    all_failures = merge_failures(project, failures, resolved=resolved)
    return {
        "registered_outputs": len(receipts),
        "verified_archive_members": seen["archives"],
        "verified_gamedata_outputs": seen["gamedata"],
        "verified_asset_outputs": seen["assets"],
        "failed_or_unsupported": len(all_failures),
    }


def existing_domain_outputs(project: Path, domain: str) -> dict[str, dict]:
    manifest_name = "audio.jsonl" if domain == "audio" else f"{domain}s.jsonl"
    paths = [project / "manifests" / manifest_name, project / "logs" / "assets_samples.jsonl"]
    result = {}
    accepted = {"DECODED", "DECODED_EXISTING_VERIFIED", "CROSS_VALIDATED", "STRUCTURE_DECODED_RENDER_UNSUPPORTED"}
    for path in paths:
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("status") not in accepted:
                continue
            if path.name == "assets_samples.jsonl" and row.get("kind") != domain:
                continue
            output = row.get("output")
            if not output:
                continue
            target = Path(output)
            if not target.is_absolute():
                target = project / target
            key = os.path.normcase(os.path.abspath(os.fspath(target))).casefold()
            entry = result.setdefault(key, {})
            entry.update({
                "source_sha256": row.get("source_sha256", row.get("input_sha256")),
                "output_sha256": row.get("output_sha256"),
            })
            if path.name == manifest_name or "manifest_row" not in entry:
                entry["manifest_row"] = row
    return result


def _scan_catalog(project: Path) -> list[dict[str, str]]:
    path = project / "manifests" / "files.csv"
    if not path.is_file():
        raise FileNotFoundError("run uv run lgpe scan before domain batches")
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def run_archive_batch(
    root: Path = PROJECT.parent, project: Path = PROJECT,
    limit: int = 20, execute: bool = False,
    only_sources: set[str] | None = None,
) -> dict:
    romfs = source_dirs(root)["romfs"]
    output_root = project / "decoded" / VERSION / "romfs"
    corpus = project / "tools" / "src" / "Switch-Toolbox" / "File_Format_Library" / "Resources" / "Hashes" / "Pkmn.txt"
    if not corpus.is_file():
        raise FileNotFoundError(f"pinned Toolbox hash corpus missing: {corpus}")

    candidates = []
    unknown = []
    catalog = _scan_catalog(project)
    archive_rows = sorted(
        (row for row in catalog if row["partition"] == "romfs" and row["suffix"].lower() in {".gfpak", ".arc"}),
        key=lambda row: row["relative_path"].casefold(),
    )
    for item in archive_rows:
        path = romfs.joinpath(*PurePosixPath(item["relative_path"]).parts)
        suffix = PurePosixPath(item["relative_path"]).suffix.lower()
        signature = item["signature"]
        supported_magic = (
            suffix == ".gfpak" and signature == "GFLXPACK"
        ) or (
            suffix == ".arc" and signature == "SARC"
        )
        row = {
            "domain": "archive",
            "source": item["relative_path"],
            "source_bytes": int(item["bytes"]),
            "signature": signature,
            "header_hex": item["header_hex"],
        }
        if supported_magic:
            candidates.append((path, row))
        else:
            unknown.append({**row, "status": "UNKNOWN", "reason": "extension/header not validated by current decoder"})

    if only_sources is not None:
        selected_names = {source.casefold() for source in only_sources}
        selected = [(path, row) for path, row in candidates if row["source"].casefold() in selected_names]
    else:
        selected = candidates if not limit else candidates[:limit]
    selected_sources = {row["source"].casefold() for _, row in selected}
    pending = [
        {**row, "status": "PENDING", "reason": "outside retry selection" if only_sources is not None else "outside current --limit"}
        for _, row in candidates if row["source"].casefold() not in selected_sources
    ]
    results = list(unknown) + pending
    receipts = []
    for path, base_row in selected:
        try:
            result = archive_reader.extract(path, romfs, output_root, corpus, execute)
            result.update({"domain": "archive", "source": base_row["source"]})
            results.append(result)
            if execute and result.get("status") == "DECODED":
                source = path
                outbase = Path(result["output"])
                for member in result.get("members", []):
                    target = outbase.joinpath(*PurePosixPath(member["internal_path"]).parts)
                    receipts.append(_receipt(
                        project, root, base_row["source"], source, target,
                        result["method"], result.get("source_references", {}),
                        source_sha256=result["source_sha256"],
                        output_sha256=member["sha256"],
                        status="DECODED",
                        internal_path=member["internal_path"],
                        container_index=member["index"],
                        container_source_sha256=result["source_sha256"],
                        container_header_hex=result["header_hex"],
                        folder_hash=member.get("folder_hash"),
                        filename_hash=member.get("filename_hash"),
                        full_path_hash=member.get("full_path_hash"),
                        name_resolution=member.get("name_resolution"),
                        compression=member.get("compression"),
                        packed_offset=member.get("offset"),
                        packed_size=member.get("packed_size"),
                        packed_sha256=member.get("packed_sha256"),
                        hash_corpus_sha256=result.get("hash_corpus_sha256"),
                        command="uv run lgpe decode-archives --execute",
                    ))
        except Exception as exc:
            results.append({
                **base_row, "status": "UNSUPPORTED" if isinstance(exc, NotImplementedError) else "FAILED",
                "error": f"{type(exc).__name__}: {exc}",
            })

    write_jsonl_selected(project / "manifests" / "archives.jsonl", results, only_sources)
    merge_failures(
        project,
        [{k: r.get(k) for k in ("domain", "source", "status", "error")} for r in results if r.get("status") in {"FAILED", "UNSUPPORTED"}],
        resolved=[{"domain": "archive", "source": r["source"]} for r in results if r.get("status") == "DECODED"],
    )
    if execute:
        add_receipts(project, receipts, trusted_outputs=True)
    statuses = [r.get("status") for r in results]
    return {
        "catalogued": len(candidates) + len(unknown),
        "compatible": len(candidates),
        "selected": len(selected),
        "pending": sum(s == "PENDING" for s in statuses),
        "decoded_containers": sum(s == "DECODED" for s in statuses),
        "decoded_members": sum(int(r.get("member_count", 0)) for r in results if r.get("status") == "DECODED"),
        "failed": sum(s == "FAILED" for s in statuses),
        "unsupported": sum(s == "UNSUPPORTED" for s in statuses),
        "unknown": sum(s == "UNKNOWN" for s in statuses),
        "execute": execute,
    }


def run_gamedata_batch(
    root: Path = PROJECT.parent, project: Path = PROJECT,
    limit: int = 20, execute: bool = False,
    only_sources: set[str] | None = None,
) -> dict:
    romfs = source_dirs(root)["romfs"]
    prefix = "bin/message/"
    scan_rows = _scan_catalog(project)
    catalog = [
        row for row in scan_rows
        if row["partition"] == "romfs"
        and row["relative_path"].casefold().startswith(prefix)
        and row["suffix"].lower() in {".dat", ".tbl"}
    ]
    catalog.sort(key=lambda row: row["relative_path"].casefold())
    romfs_rows = [row for row in scan_rows if row["partition"] == "romfs"]
    romfs_names = {row["relative_path"].casefold() for row in romfs_rows}
    ahtb_tables = []
    for row in romfs_rows:
        if row["suffix"].lower() != ".tbl" or row["signature"].casefold() != "ahtb":
            continue
        dat_name = PurePosixPath(row["relative_path"]).with_suffix(".dat").as_posix()
        if dat_name.casefold() not in romfs_names:
            ahtb_tables.append(row)
    ahtb_tables.sort(key=lambda row: row["relative_path"].casefold())
    ahtb_names = {row["relative_path"].casefold() for row in ahtb_tables}
    table_lookup = {
        row["relative_path"].casefold(): row for row in catalog
        if row["suffix"].lower() == ".tbl"
    }
    dat_rows = [row for row in catalog if row["suffix"].lower() == ".dat"]
    tbl_rows = [row for row in catalog if row["suffix"].lower() == ".tbl"]
    grammar_prefix = "bin/message/grammar/"
    grammar_rows = [
        row for row in dat_rows
        if row["relative_path"].casefold().startswith(grammar_prefix)
    ]
    grammar_names = {row["relative_path"].casefold() for row in grammar_rows}
    paired = []
    paired_sources = set()
    paired_tables = set()
    for item in dat_rows:
        rel = item["relative_path"]
        table_rel = str(PurePosixPath(rel).with_suffix(".tbl"))
        table_item = table_lookup.get(table_rel.casefold())
        if table_item is not None:
            path = romfs.joinpath(*PurePosixPath(rel).parts)
            table = romfs.joinpath(*PurePosixPath(table_item["relative_path"]).parts)
            paired.append((path, rel, table, table_item["relative_path"], item, table_item))
            paired_sources.add(rel.casefold())
            paired_tables.add(table_item["relative_path"].casefold())
    if only_sources is not None:
        selected_names = {source.casefold() for source in only_sources}
        selected = [entry for entry in paired if entry[1].casefold() in selected_names]
    else:
        selected = paired if not limit else paired[:limit]
    results = []
    receipts = []

    for item in dat_rows:
        if (item["relative_path"].casefold() not in paired_sources
                and item["relative_path"].casefold() not in grammar_names):
            results.append({
                "domain": "gamedata", "source": item["relative_path"],
                "status": "UNKNOWN", "reason": "message DAT has no paired TBL",
            })
    for item in tbl_rows:
        if (item["relative_path"].casefold() not in paired_tables
                and item["relative_path"].casefold() not in ahtb_names):
            results.append({
                "domain": "gamedata", "source": item["relative_path"],
                "status": "UNKNOWN", "reason": "TBL has no paired message DAT",
            })

    selected_sources = {entry[1].casefold() for entry in selected}
    for path, rel, table, table_rel, item, table_item in paired:
        if rel.casefold() not in selected_sources:
            results.append({
                "domain": "gamedata", "source": rel, "status": "PENDING",
                "reason": "outside current --limit",
            })
            continue
        output = decode_destination("romfs", rel, ".json", project)
        row = {
            "domain": "gamedata", "source": rel,
            "companion": table_rel,
            "source_bytes": int(item["bytes"]), "companion_bytes": int(table_item["bytes"]),
            "method": "lgpe_research.gamedata_decode/message",
            "tool_versions": {
                "pokedat": "bd423b2cad9aa852fddb796bbba3c5e7b381289b",
                "pkNX": "d191cd0e5c05f2af81d9a41c1f1d82e6621b351a",
            },
        }
        if not execute:
            results.append({**row, "status": "DRY_RUN", "output": str(output)})
            continue
        try:
            source_hash = sha256(path)
            companion_hash = sha256(table)
            row.update({"source_sha256": source_hash, "companion_sha256": companion_hash})
            value = gamedata_decode.message(path.read_bytes(), table.read_bytes(), project / "tools" / "src" / "pokedat")
            payload = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
            output.parent.mkdir(parents=True, exist_ok=True)
            if output.exists():
                if output.read_bytes() != payload:
                    raise FileExistsError(f"conflicting output: {output}")
            else:
                temporary = output.with_name(output.name + ".lgpe.partial")
                if temporary.exists():
                    raise FileExistsError(f"stale partial: {temporary}")
                with temporary.open("xb") as stream:
                    stream.write(payload)
                temporary.replace(output)
            if sha256(path) != source_hash or sha256(table) != companion_hash:
                raise ValueError("source or companion changed during decode")
            row.update({
                "status": "DECODED", "output": str(output.relative_to(project)),
                "output_sha256": sha256(output), "output_bytes": output.stat().st_size,
                "count": len(value["lines"]),
                "unpaired_labels": len(value["unpaired_labels"]),
            })
            receipts.append(_receipt(
                project, root, rel, path, output, row["method"], row["tool_versions"],
                source_sha256=source_hash, output_sha256=row["output_sha256"],
                status="DECODED", companion=table_rel,
                companion_sha256=row["companion_sha256"], count=row["count"],
                unpaired_labels=row["unpaired_labels"],
                command="uv run lgpe decode-gamedata --execute",
            ))
        except Exception as exc:
            row.update({"status": "FAILED", "error": f"{type(exc).__name__}: {exc}"})
        results.append(row)

    if only_sources is not None:
        selected_grammar = [
            row for row in grammar_rows
            if row["relative_path"].casefold()
            in {source.casefold() for source in only_sources}
        ]
    else:
        selected_grammar = grammar_rows if not limit else grammar_rows[:limit]
    selected_grammar_names = {row["relative_path"].casefold() for row in selected_grammar}
    for item in grammar_rows:
        rel = item["relative_path"]
        if rel.casefold() not in selected_grammar_names:
            results.append({
                "domain": "gamedata", "source": rel, "status": "PENDING",
                "reason": "outside current --limit or retry selection",
            })
            continue
        path = _source(root, rel)
        output = decode_destination("romfs", rel, ".json", project)
        row = {
            "domain": "gamedata", "source": rel,
            "source_bytes": int(item["bytes"]),
            "method": "lgpe_research.gamedata_decode/grammar_data",
            "tool_versions": {
                "decoder_schema": gamedata_decode.SCHEMA,
                "Ghidra": "12.2 PUBLIC",
                "main_sha256": "1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8",
                "path_xref_function": "main+0x1ae750",
                "resource_request_helper": "main+0x00adc70",
            },
        }
        if not execute:
            results.append({**row, "status": "DRY_RUN", "output": str(output)})
            continue
        try:
            data = path.read_bytes()
            source_hash = gamedata_decode.sha(data)
            if len(data) != int(item["bytes"]):
                raise ValueError("grammar source size differs from scan catalog")
            value = gamedata_decode.grammar_data(data)
            if bytes.fromhex(value["raw_hex"]) != data:
                raise ValueError("grammar raw_hex does not reassemble to the source")
            payload = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
            output.parent.mkdir(parents=True, exist_ok=True)
            if output.exists():
                if output.read_bytes() != payload:
                    raise FileExistsError(f"conflicting output: {output}")
            else:
                temporary = output.with_name(output.name + ".lgpe.partial")
                if temporary.exists():
                    raise FileExistsError(f"stale partial: {temporary}")
                with temporary.open("xb") as stream:
                    stream.write(payload)
                temporary.replace(output)
            if sha256(path) != source_hash:
                raise ValueError("grammar source changed during decode")
            row.update({
                "status": "DECODED", "output": str(output.relative_to(project)),
                "source_sha256": source_hash, "output_sha256": sha256(output),
                "output_bytes": output.stat().st_size,
                "count": value["offset_count"],
                "record_format": value["format"],
                "text_segment_count": len(value["entries"]),
            })
            receipts.append(_receipt(
                project, root, rel, path, output, row["method"], row["tool_versions"],
                source_sha256=source_hash, output_sha256=row["output_sha256"],
                status="DECODED", count=row["count"],
                record_format=row["record_format"],
                text_segment_count=row["text_segment_count"],
                command="uv run lgpe decode-gamedata --execute",
            ))
        except Exception as exc:
            row.update({"status": "FAILED", "error": f"{type(exc).__name__}: {exc}"})
        results.append(row)

    if only_sources is not None:
        selected_ahtb = [
            row for row in ahtb_tables
            if row["relative_path"].casefold() in {source.casefold() for source in only_sources}
        ]
    else:
        selected_ahtb = ahtb_tables if not limit else ahtb_tables[:limit]
    selected_ahtb_names = {row["relative_path"].casefold() for row in selected_ahtb}
    for item in ahtb_tables:
        rel = item["relative_path"]
        if rel.casefold() not in selected_ahtb_names:
            results.append({
                "domain": "gamedata", "source": rel, "status": "PENDING",
                "reason": "outside current --limit or retry selection",
            })
            continue
        path = _source(root, rel)
        output = decode_destination("romfs", rel, ".json", project)
        row = {
            "domain": "gamedata", "source": rel,
            "source_bytes": int(item["bytes"]),
            "method": "lgpe_research.gamedata_decode/tbl_labels",
            "tool_versions": {"decoder_schema": gamedata_decode.SCHEMA},
        }
        if not execute:
            row.update({"status": "DRY_RUN", "output": str(output)})
            results.append(row)
            continue
        try:
            data = path.read_bytes()
            source_hash = gamedata_decode.sha(data)
            if len(data) != int(item["bytes"]):
                raise ValueError("source size differs from scan catalog")
            value = gamedata_decode.tbl_labels(data)
            payload = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
            output.parent.mkdir(parents=True, exist_ok=True)
            if output.exists():
                if output.read_bytes() != payload:
                    raise FileExistsError(f"conflicting output: {output}")
            else:
                temporary = output.with_name(output.name + ".lgpe.partial")
                if temporary.exists():
                    raise FileExistsError(f"stale partial: {temporary}")
                with temporary.open("xb") as stream:
                    stream.write(payload)
                temporary.replace(output)
            if sha256(path) != source_hash:
                raise ValueError("source changed during decode")
            row.update({
                "status": "DECODED", "output": str(output.relative_to(project)),
                "source_sha256": source_hash, "output_sha256": sha256(output),
                "output_bytes": output.stat().st_size,
                "count": value["entry_count"], "record_format": value["format"],
            })
            receipts.append(_receipt(
                project, root, rel, path, output, row["method"], row["tool_versions"],
                source_sha256=source_hash, output_sha256=row["output_sha256"],
                status="DECODED", count=row["count"], record_format=row["record_format"],
                command="uv run lgpe decode-gamedata --execute",
            ))
        except Exception as exc:
            row.update({"status": "FAILED", "error": f"{type(exc).__name__}: {exc}"})
        results.append(row)

    tables = [
        ("bin/pokelib/personal/personal_total.bin", gamedata_decode.personal, "personal"),
        ("bin/field/param/encount/encount_data_p.bin", gamedata_decode.encounters, "encounters"),
        ("bin/field/param/encount/encount_data_e.bin", gamedata_decode.encounters, "encounters"),
        ("bin/pokelib/waza/waza_data.bin", gamedata_decode.move_data_7, "moves"),
        ("bin/pokelib/item/item_hash_to_index.dat", gamedata_decode.item_hash_to_index, "item_hash"),
    ]
    selected_message_sources = {entry[1].casefold() for entry in selected}
    for rel, decoder, name in tables:
        path = _source(root, rel)
        if only_sources is not None and rel.casefold() not in {source.casefold() for source in only_sources}:
            results.append({"domain": "gamedata", "source": rel, "status": "PENDING", "reason": "outside retry selection"})
            continue
        output = decode_destination("romfs", rel, ".json", project)
        row = {
            "domain": "gamedata", "source": rel, "source_sha256": sha256(path),
            "source_bytes": path.stat().st_size,
            "method": "lgpe_research.gamedata_decode/" + name,
            "tool_versions": (
                {
                    "decoder_schema": gamedata_decode.SCHEMA,
                    "Ghidra": "12.2 PUBLIC",
                    "main_sha256": "1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8",
                    "pkNX_candidate_parser": "d191cd0e5c05f2af81d9a41c1f1d82e6621b351a",
                }
                if name == "item_hash"
                else {"pkNX": "d191cd0e5c05f2af81d9a41c1f1d82e6621b351a"}
            ),
        }
        if not execute:
            results.append({**row, "status": "DRY_RUN", "output": str(output)})
            continue
        try:
            value = decoder(path.read_bytes())
            payload = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
            output.parent.mkdir(parents=True, exist_ok=True)
            if output.exists():
                if output.read_bytes() != payload:
                    raise FileExistsError(f"conflicting output: {output}")
            else:
                temporary = output.with_name(output.name + ".lgpe.partial")
                if temporary.exists():
                    raise FileExistsError(f"stale partial: {temporary}")
                with temporary.open("xb") as stream:
                    stream.write(payload)
                temporary.replace(output)
            if sha256(path) != row["source_sha256"]:
                raise ValueError("source changed during decode")
            row.update({
                "status": "DECODED", "output": str(output.relative_to(project)),
                "output_sha256": sha256(output), "output_bytes": output.stat().st_size,
                "count": len(value.get("entries", value.get("tables", []))),
            })
            if name == "encounters":
                row["slot_count"] = sum(
                    len(v) for table in value["tables"] for v in table.values()
                    if isinstance(v, list)
                )
            receipts.append(_receipt(
                project, root, rel, path, output, row["method"], row["tool_versions"],
                source_sha256=row["source_sha256"], output_sha256=row["output_sha256"],
                status="DECODED",
                count=row["count"], slot_count=row.get("slot_count"),
                command="uv run lgpe decode-gamedata --execute",
            ))
        except Exception as exc:
            row.update({"status": "FAILED", "error": f"{type(exc).__name__}: {exc}"})
        results.append(row)

    # These data sources have format-specific decoders or exact path evidence.
    # field_pocket.dat is handled separately from Item.FromBytes: exact-build
    # main code indexes this 0x422-byte table and reads its low three bits.
    # battle_pocket.dat has a complete value-level match against Item.PocketBattle;
    # its exact-build main loader/accessor has not been established.
    # Other unmatched item DAT files remain UNKNOWN.
    record_groups = [
        ("unlabeled_monsname", "bin/pokelib/personal/monsname.dat", ".dat",
         lambda data: gamedata_decode.unlabeled_message(data, project / "tools" / "src" / "pokedat"),
         lambda row: int(row["bytes"]) >= 20),
        ("zukan_sort", "bin/app/zukan_data/bin/zukan_sort_", ".bin",
         gamedata_decode.zukan_sort_data, lambda row: int(row["bytes"]) % 2 == 0),
        ("field_pocket", "bin/pokelib/item/field_pocket.dat", ".dat", gamedata_decode.field_pocket,
         lambda row: int(row["bytes"]) == 0x422),
        ("battle_pocket", "bin/pokelib/item/battle_pocket.dat", ".dat", gamedata_decode.battle_pocket,
         lambda row: int(row["bytes"]) == 0x422),
        ("items", "bin/pokelib/item/", ".dat", gamedata_decode.item,
         lambda row: int(row["bytes"]) == 0x24),
        ("trainer_data", "bin/trainer/trainer_data/", ".bin", gamedata_decode.trainer_data_7b,
         lambda row: int(row["bytes"]) == 0x17),
        ("trainer_poke", "bin/trainer/trainer_poke/", ".bin", gamedata_decode.trainer_poke_7b,
         lambda row: int(row["bytes"]) % 0x28 == 0),
        ("trainer_type", "bin/trainer/trainer_type/", ".bin", gamedata_decode.trainer_class_7b,
         lambda row: int(row["bytes"]) == 0x24),
        ("evolution", "bin/pokelib/evolution/", ".bin", gamedata_decode.evolution_set_7,
         lambda row: int(row["bytes"]) == 0x40),
        ("mega_evolution", "bin/pokelib/mega_evolution/", ".bin", gamedata_decode.mega_evolution_7,
         lambda row: int(row["bytes"]) % 8 == 0),
        ("encounter_static", "bin/script_event_data/event_encount.bin", ".bin", gamedata_decode.encounter_static_7b,
         lambda row: int(row["bytes"]) % 0x40 == 0),
        ("encounter_gift", "bin/script_event_data/add_poke.bin", ".bin", gamedata_decode.encounter_gift_7b,
         lambda row: int(row["bytes"]) % 0x20 == 0),
        ("encounter_trade", "bin/script_event_data/field_trade_data.bin", ".bin", gamedata_decode.encounter_trade_7b,
         lambda row: int(row["bytes"]) % 0x58 == 0),
    ]
    record_summaries = {}
    selected_only = {source.casefold() for source in only_sources} if only_sources is not None else None
    for group_name, prefix, suffix, decoder, compatible in record_groups:
        group_rows = [
            row for row in scan_rows
            if row["partition"] == "romfs"
            and (
                row["relative_path"].casefold() == prefix.casefold()
                if group_name in {"unlabeled_monsname", "field_pocket", "battle_pocket"}
                else row["relative_path"].casefold().startswith(prefix.casefold())
            )
            and row["suffix"].lower() == suffix
        ]
        if group_name == "items":
            group_rows = [
                row for row in group_rows
                if row["relative_path"].casefold() not in {
                    "bin/pokelib/item/field_pocket.dat",
                    "bin/pokelib/item/battle_pocket.dat",
                    "bin/pokelib/item/item_hash_to_index.dat",
                }
            ]
        group_rows.sort(key=lambda row: row["relative_path"].casefold())
        candidates = [row for row in group_rows if compatible(row)]
        incompatible = [row for row in group_rows if not compatible(row)]
        if selected_only is not None:
            selected_records = [row for row in candidates if row["relative_path"].casefold() in selected_only]
        else:
            selected_records = candidates if not limit else candidates[:limit]
        selected_record_names = {row["relative_path"].casefold() for row in selected_records}
        group_results = []
        for item in incompatible:
            reason = (
                "Source is shorter than the minimum LGPE text header"
                if group_name == "unlabeled_monsname"
                else f"No accepted {group_name} record size in pinned pkNX GameManagerGG path"
            )
            if item["relative_path"].casefold() == "bin/pokelib/item/item_hash_to_index.dat":
                reason = "Pinned pkNX ItemHash8 parser is mapped only for SWSH; no LGPE reader is verified"
            record = {
                "domain": "gamedata", "source": item["relative_path"],
                "status": "UNKNOWN",
                "reason": reason,
            }
            results.append(record)
            group_results.append(record)
        for item in candidates:
            rel = item["relative_path"]
            if rel.casefold() not in selected_record_names:
                record = {
                    "domain": "gamedata", "source": rel, "status": "PENDING",
                    "reason": "outside current --limit or retry selection",
                }
                results.append(record)
                group_results.append(record)
                continue
            path = _source(root, rel)
            output = decode_destination("romfs", rel, ".json", project)
            if group_name == "unlabeled_monsname":
                tool_versions = {
                    "decoder_schema": gamedata_decode.SCHEMA,
                    "pokedat": "bd423b2cad9aa852fddb796bbba3c5e7b381289b",
                    "pkNX": "d191cd0e5c05f2af81d9a41c1f1d82e6621b351a",
                }
            elif group_name == "field_pocket":
                tool_versions = {
                    "decoder_schema": gamedata_decode.SCHEMA,
                    "Ghidra": "12.2 PUBLIC",
                    "pkNX": "d191cd0e5c05f2af81d9a41c1f1d82e6621b351a",
                    "main_sha256": "1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8",
                }
            elif group_name == "battle_pocket":
                tool_versions = {
                    "decoder_schema": gamedata_decode.SCHEMA,
                    "pkNX": "d191cd0e5c05f2af81d9a41c1f1d82e6621b351a",
                    "main_sha256": "1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8",
                }
            elif group_name == "zukan_sort":
                tool_versions = {
                    "decoder_schema": gamedata_decode.SCHEMA,
                    "Ghidra": "12.2 PUBLIC",
                    "main_sha256": "1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8",
                }
            else:
                tool_versions = {"pkNX": "d191cd0e5c05f2af81d9a41c1f1d82e6621b351a"}
            record = {
                "domain": "gamedata", "source": rel,
                "method": "lgpe_research.gamedata_decode/" + group_name,
                "source_bytes": int(item["bytes"]),
                "tool_versions": tool_versions,
            }
            if not execute:
                record.update({"status": "DRY_RUN", "output": str(output)})
                results.append(record)
                group_results.append(record)
                continue
            try:
                data = path.read_bytes()
                source_hash = gamedata_decode.sha(data)
                value = decoder(data)
                if bytes.fromhex(value["raw_hex"]) != data:
                    raise ValueError("decoded raw_hex does not reassemble to the input bytes")
                payload = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
                output.parent.mkdir(parents=True, exist_ok=True)
                if output.exists():
                    if output.read_bytes() != payload:
                        raise FileExistsError(f"conflicting output: {output}")
                else:
                    temporary = output.with_name(output.name + ".lgpe.partial")
                    if temporary.exists():
                        raise FileExistsError(f"stale partial: {temporary}")
                    with temporary.open("xb") as stream:
                        stream.write(payload)
                    temporary.replace(output)
                if sha256(path) != source_hash:
                    raise ValueError("source changed during decode")
                count = len(value["entries"]) if "entries" in value else 1
                record.update({
                    "status": "DECODED", "output": str(output.relative_to(project)),
                    "source_sha256": source_hash, "output_sha256": sha256(output),
                    "output_bytes": output.stat().st_size, "count": count,
                    "record_format": value["format"],
                })
                receipts.append(_receipt(
                    project, root, rel, path, output, record["method"],
                    record["tool_versions"], source_sha256=source_hash,
                    output_sha256=record["output_sha256"], status="DECODED",
                    count=count, record_format=record["record_format"],
                    command="uv run lgpe decode-gamedata --execute",
                ))
            except Exception as exc:
                record.update({"status": "FAILED", "error": f"{type(exc).__name__}: {exc}"})
            results.append(record)
            group_results.append(record)
        record_summaries[group_name] = {
            "catalogued": len(group_rows), "compatible": len(candidates),
            "selected": len(selected_records),
            "decoded": sum(row.get("status") == "DECODED" for row in group_results),
            "failed": sum(row.get("status") == "FAILED" for row in group_results),
            "unknown": sum(row.get("status") == "UNKNOWN" for row in group_results),
            "pending": sum(row.get("status") == "PENDING" for row in group_results),
        }

    sort_prefix = "bin/app/sort_string/"
    localized_sort_rows = [
        row for row in scan_rows
        if row["partition"] == "romfs"
        and row["relative_path"].casefold().startswith(sort_prefix)
        and row["suffix"].lower() == ".dat"
    ]
    localized_sort_rows.sort(key=lambda row: row["relative_path"].casefold())
    sort_group_specs = (
        ("sort_table", "_sort_table.dat", 2, localized_sort_decode.decode_sort_table,
         "0x7100374a90"),
        ("initial_to_sort", "_initial_to_sort.dat", 4,
         localized_sort_decode.decode_initial_to_sort, "0x7100374ad0"),
    )
    request_callers = {
        "item": "0x7100b31400",
        "monsname": "0x7100b315e0",
        "waza": "0x7100b318c0",
    }
    main_sha256 = "1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8"
    localized_sort_summaries = {}
    for group_name, filename_suffix, record_width, decoder, accessor in sort_group_specs:
        group_rows = [
            row for row in localized_sort_rows
            if row["relative_path"].casefold().endswith(filename_suffix)
        ]
        group_rows.sort(key=lambda row: row["relative_path"].casefold())
        candidates = [
            row for row in group_rows
            if int(row["bytes"]) > 0 and int(row["bytes"]) % record_width == 0
        ]
        incompatible = [row for row in group_rows if row not in candidates]
        if selected_only is not None:
            selected_records = [
                row for row in candidates
                if row["relative_path"].casefold() in selected_only
            ]
        else:
            selected_records = candidates if not limit else candidates[:limit]
        selected_names = {row["relative_path"].casefold() for row in selected_records}
        group_results = []
        for item in incompatible:
            record = {
                "domain": "gamedata", "source": item["relative_path"],
                "status": "FAILED",
                "reason": f"source length is not a positive multiple of {record_width}",
            }
            results.append(record)
            group_results.append(record)
        for item in candidates:
            rel = item["relative_path"]
            if rel.casefold() not in selected_names:
                record = {
                    "domain": "gamedata", "source": rel, "status": "PENDING",
                    "reason": "outside current --limit or retry selection",
                }
                results.append(record)
                group_results.append(record)
                continue
            path = _source(root, rel)
            output = decode_destination("romfs", rel, ".json", project)
            family = PurePosixPath(rel).name.split("_", 1)[0]
            if family not in request_callers:
                record = {
                    "domain": "gamedata", "source": rel, "status": "UNKNOWN",
                    "reason": "no exact-build path request was matched to this family",
                }
                results.append(record)
                group_results.append(record)
                continue
            request_caller = request_callers[family]
            record = {
                "domain": "gamedata", "source": rel,
                "method": f"lgpe_research.localized_sort_decode/{group_name}",
                "source_bytes": int(item["bytes"]),
                "tool_versions": {
                    "decoder_schema": localized_sort_decode.SCHEMA,
                    "Ghidra": "12.2 PUBLIC",
                    "main_sha256": main_sha256,
                    "resource_loader": "main+0x374530",
                    "resource_request_caller": request_caller,
                    "element_reader": accessor,
                },
                "static_evidence": {
                    "resource_loader": "main+0x374530 binds the second resource to buffer +0x340 and the third to +0x360",
                    "element_reader": (
                        "main+0x374a90 bounds the index by byte_length/2 and reads one little-endian u16"
                        if group_name == "sort_table"
                        else "main+0x374ad0 reads two little-endian u16 fields at index*4; callers pass them as an inclusive iteration range"
                    ),
                },
            }
            if not execute:
                record.update({"status": "DRY_RUN", "output": str(output)})
                results.append(record)
                group_results.append(record)
                continue
            try:
                data = path.read_bytes()
                source_hash = gamedata_decode.sha(data)
                if len(data) != int(item["bytes"]):
                    raise ValueError("source size differs from scan catalog")
                value = decoder(data)
                if bytes.fromhex(value["raw_hex"]) != data:
                    raise ValueError("decoded raw_hex does not reassemble to the input bytes")
                payload = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
                output.parent.mkdir(parents=True, exist_ok=True)
                if output.exists():
                    if output.read_bytes() != payload:
                        raise FileExistsError(f"conflicting output: {output}")
                else:
                    temporary = output.with_name(output.name + ".lgpe.partial")
                    if temporary.exists():
                        raise FileExistsError(f"stale partial: {temporary}")
                    with temporary.open("xb") as stream:
                        stream.write(payload)
                    temporary.replace(output)
                if sha256(path) != source_hash:
                    raise ValueError("source changed during decode")
                record.update({
                    "status": "DECODED", "output": str(output.relative_to(project)),
                    "source_sha256": source_hash, "output_sha256": sha256(output),
                    "output_bytes": output.stat().st_size,
                    "count": value["entry_count"], "record_format": value["format"],
                })
                receipts.append(_receipt(
                    project, root, rel, path, output, record["method"],
                    record["tool_versions"], source_sha256=source_hash,
                    output_sha256=record["output_sha256"], status="DECODED",
                    count=record["count"], record_format=record["record_format"],
                    command="uv run lgpe decode-gamedata --execute",
                ))
            except Exception as exc:
                record.update({"status": "FAILED", "error": f"{type(exc).__name__}: {exc}"})
            results.append(record)
            group_results.append(record)
        localized_sort_summaries[group_name] = {
            "catalogued": len(group_rows), "compatible": len(candidates),
            "selected": len(selected_records),
            "decoded": sum(row.get("status") == "DECODED" for row in group_results),
            "failed": sum(row.get("status") == "FAILED" for row in group_results),
            "unknown": sum(row.get("status") == "UNKNOWN" for row in group_results),
            "pending": sum(row.get("status") == "PENDING" for row in group_results),
        }

    initial_index_rows = [
        row for row in localized_sort_rows
        if row["relative_path"].casefold().endswith("_initial_index.dat")
    ]
    initial_index_results = []
    for item in initial_index_rows:
        rel = item["relative_path"]
        if selected_only is not None and rel.casefold() not in selected_only:
            continue
        record = {
            "domain": "gamedata", "source": rel, "status": "UNKNOWN",
            "reason": "exact-build path request is known, but no element read has been traced for this first resource",
        }
        results.append(record)
        initial_index_results.append(record)
    localized_sort_summaries["initial_index"] = {
        "catalogued": len(initial_index_rows), "compatible": 0, "selected": 0,
        "decoded": 0, "failed": 0,
        "unknown": len(initial_index_results), "pending": 0,
    }

    write_jsonl_selected(project / "manifests" / "gamedata.jsonl", results, only_sources)
    merge_failures(
        project,
        [{k: r.get(k) for k in ("domain", "source", "status", "error")} for r in results if r.get("status") == "FAILED"],
        resolved=[{"domain": "gamedata", "source": r["source"]} for r in results if r.get("status") in {"DECODED", "CROSS_VALIDATED"}],
    )
    if execute:
        add_receipts(project, receipts, trusted_outputs=True)
    statuses = [r.get("status") for r in results]
    return {
        "message_dat_scanned": len(dat_rows),
        "paired_messages": len(paired),
        "unpaired_ahtb_tables": len(ahtb_tables),
        "selected_ahtb_tables": len(selected_ahtb),
        "selected_messages": len(selected),
        "grammar_sources": len(grammar_rows),
        "selected_grammar_sources": len(selected_grammar),
        "decoded_grammar_sources": sum(
            row.get("status") == "DECODED"
            for row in results
            if row.get("source", "").casefold() in grammar_names
        ),
        "pending_messages": sum(
            r.get("status") == "PENDING" and str(r.get("source", "")).casefold() in paired_sources
            for r in results
        ),
        "pending_sources": sum(r.get("status") == "PENDING" for r in results),
        "tables_scanned": len(tables),
        "pknx_record_groups": record_summaries,
        "localized_sort_groups": localized_sort_summaries,
        "decoded_outputs": sum(r.get("status") in {"DECODED", "CROSS_VALIDATED"} for r in results),
        "failed": sum(r.get("status") == "FAILED" for r in results),
        "unknown": sum(r.get("status") == "UNKNOWN" for r in results),
        "execute": execute,
    }


def register_gamedata_manifest(
    root: Path = PROJECT.parent, project: Path = PROJECT,
    only_sources: set[str] | None = None,
) -> dict:
    """Rehash and register completed game-data manifest outputs without decoding them again."""
    path = project / "manifests" / "gamedata.jsonl"
    if not path.is_file():
        raise FileNotFoundError(path)
    romfs = source_dirs(root)["romfs"]
    receipts = []
    failures = []
    resolved = []
    selected_names = {source.casefold() for source in only_sources} if only_sources is not None else None
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("status") not in {"DECODED", "CROSS_VALIDATED"}:
            continue
        rel = row["source"]
        if selected_names is not None and rel.casefold() not in selected_names:
            continue
        source_rel = PurePosixPath(rel)
        output_rel = Path(row["output"])
        if source_rel.is_absolute() or ".." in source_rel.parts:
            raise ValueError(f"unsafe source path in manifest: {rel}")
        if output_rel.is_absolute() or ".." in output_rel.parts or not output_rel.parts or output_rel.parts[0] != "decoded":
            raise ValueError(f"unsafe output path in manifest: {row['output']}")
        source = romfs.joinpath(*source_rel.parts)
        output = project / output_rel
        try:
            source_hash = sha256(source)
            output_hash = sha256(output)
            if source_hash != row["source_sha256"]:
                raise ValueError("source SHA256 differs from batch manifest")
            if output_hash != row["output_sha256"]:
                raise ValueError("output SHA256 differs from batch manifest")
            companion = row.get("companion")
            if companion:
                companion_rel = PurePosixPath(companion)
                if companion_rel.is_absolute() or ".." in companion_rel.parts:
                    raise ValueError(f"unsafe companion path in manifest: {companion}")
                table = romfs.joinpath(*companion_rel.parts)
                if sha256(table) != row.get("companion_sha256"):
                    raise ValueError("companion SHA256 differs from batch manifest")
            receipts.append(_receipt(
                project, root, rel, source, output,
                row["method"], row.get("tool_versions", {}),
                source_sha256=source_hash,
                output_sha256=output_hash,
                status="DECODED",
                companion=companion,
                companion_sha256=row.get("companion_sha256"),
                count=row.get("count"),
                slot_count=row.get("slot_count"),
                unpaired_labels=row.get("unpaired_labels"),
                command="uv run lgpe decode-gamedata --execute",
            ))
            resolved.append({"domain": "gamedata", "source": rel})
        except Exception as exc:
            failures.append({
                "domain": "gamedata", "source": rel, "status": "FAILED",
                "error": f"{type(exc).__name__}: {exc}",
            })
    registered = add_receipts(project, receipts, trusted_outputs=True)
    failure_rows = merge_failures(project, failures, resolved=resolved)
    return {
        "selected_sources": len(only_sources) if only_sources is not None else None,
        "verified": len(receipts),
        "registered_outputs": registered,
        "failed": len(failures),
        "failure_registry": len(failure_rows),
    }


def run_learnset_batch(
    root: Path = PROJECT.parent, project: Path = PROJECT,
    limit: int = 20, execute: bool = False,
    only_sources: set[str] | None = None,
) -> dict:
    """Decode Learnset6 records without changing the extracted archive members."""
    archive_rel = "bin/archive/waza_oboe.gfpak"
    archive_catalog = project / "manifests" / "archives.jsonl"
    if not archive_catalog.is_file():
        raise FileNotFoundError("run `uv run lgpe decode-archives` before learnset decoding")
    archive_row = next((
        json.loads(line) for line in archive_catalog.read_text(encoding="utf-8").splitlines()
        if line.strip() and json.loads(line).get("source", "").casefold() == archive_rel.casefold()
    ), None)
    if archive_row is None or archive_row.get("status") not in {"DECODED", "DECODED_EXISTING_VERIFIED"}:
        raise ValueError(f"learnset source archive is not successfully extracted: {archive_rel}")
    archive_path = _source(root, archive_rel)
    archive_hash = sha256(archive_path)
    if archive_hash != archive_row.get("source_sha256"):
        raise ValueError("waza_oboe.gfpak hash differs from the archive manifest")

    outputs_manifest = project / "manifests" / "outputs.jsonl"
    if not outputs_manifest.is_file():
        raise FileNotFoundError("archive member receipts are missing; run `uv run lgpe decode-archives`")
    member_rows = []
    for line in outputs_manifest.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if (
            row.get("relative_source", "").casefold() == archive_rel.casefold()
            and row.get("internal_path") is not None
            and row.get("source_internal_path") is None
            and row.get("container_index") is not None
        ):
            member_rows.append(row)
    member_rows.sort(key=lambda row: int(row["container_index"]))
    expected_count = int(archive_row.get("member_count", 0))
    if len(member_rows) != expected_count or len({int(row["container_index"]) for row in member_rows}) != expected_count:
        raise ValueError(f"expected {expected_count} unique archive members, found {len(member_rows)} receipts")

    selected_names = {source.casefold() for source in only_sources} if only_sources is not None else None
    archive_selected = selected_names is None or archive_rel.casefold() in selected_names
    selected_rows = member_rows if archive_selected and not limit else member_rows[:limit] if archive_selected else []
    selected_indexes = {int(row["container_index"]) for row in selected_rows}
    container_dir = (
        project / "decoded" / VERSION / "romfs"
        / Path(*PurePosixPath(archive_rel).parent.parts)
        / (PurePosixPath(archive_rel).name + ".contents")
    )
    container_dir = ensure_inside(container_dir, project / "decoded")
    manifest_path = project / "manifests" / "learnsets.jsonl"
    old_rows = [
        json.loads(line) for line in manifest_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ] if manifest_path.is_file() else []
    by_internal = {str(row.get("source_internal_path", "")).casefold(): row for row in old_rows}
    results = []
    receipts = []
    failure_rows = []
    for member in member_rows:
        index = int(member["container_index"])
        raw_internal = PurePosixPath(str(member["internal_path"]).replace("\\", "/"))
        if raw_internal.is_absolute() or ".." in raw_internal.parts or not raw_internal.parts:
            raise ValueError(f"unsafe archive member path: {member['internal_path']}")
        source = ensure_inside(container_dir.joinpath(*raw_internal.parts), container_dir)
        if Path(member["output_file"]).resolve() != source.resolve():
            raise ValueError(f"archive receipt path does not match internal path: {raw_internal}")
        output_internal = raw_internal.with_suffix(".json")
        output = ensure_inside(container_dir.joinpath(*output_internal.parts), container_dir)
        record = {
            "domain": "learnset", "source": archive_rel,
            "source_internal_path": raw_internal.as_posix(),
            "output_internal_path": output_internal.as_posix(),
            "container_index": index,
            "method": "lgpe_research.gamedata_decode/learnset_6",
            "tool_versions": {"pkNX": "d191cd0e5c05f2af81d9a41c1f1d82e6621b351a"},
            "source_bytes": int(member["output_size"]),
        }
        if not archive_selected or index not in selected_indexes:
            record.update({"status": "PENDING", "reason": "outside current limit or source selection"})
        elif not execute:
            record.update({"status": "DRY_RUN", "output": str(output.relative_to(project))})
        else:
            try:
                data = source.read_bytes()
                member_hash = gamedata_decode.sha(data)
                if member_hash != member.get("output_sha256"):
                    raise ValueError("extracted archive member SHA256 differs from its receipt")
                value = gamedata_decode.learnset_6(data)
                if bytes.fromhex(value["raw_hex"]) != data:
                    raise ValueError("learnset raw_hex does not reassemble to the archive member")
                payload = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
                output.parent.mkdir(parents=True, exist_ok=True)
                if output.exists():
                    if output.read_bytes() != payload:
                        raise FileExistsError(f"conflicting output: {output}")
                else:
                    temporary = output.with_name(output.name + ".lgpe.partial")
                    if temporary.exists():
                        raise FileExistsError(f"stale partial: {temporary}")
                    with temporary.open("xb") as stream:
                        stream.write(payload)
                    temporary.replace(output)
                if gamedata_decode.sha(source.read_bytes()) != member_hash:
                    raise ValueError("archive member changed during learnset conversion")
                output_hash = sha256(output)
                record.update({
                    "status": "DECODED", "output": str(output.relative_to(project)),
                    "source_sha256": member_hash, "container_source_sha256": archive_hash,
                    "output_sha256": output_hash, "output_bytes": output.stat().st_size,
                    "count": len(value["entries"]),
                    "trailing_word_hex": value["trailing_word_hex"],
                })
                receipts.append(_receipt(
                    project, root, archive_rel, source, output, record["method"],
                    record["tool_versions"], source_sha256=member_hash,
                    output_sha256=output_hash, status="DECODED",
                    internal_path=output_internal.as_posix(),
                    source_internal_path=raw_internal.as_posix(),
                    container_index=index,
                    container_source_file=str(archive_path),
                    container_source_sha256=archive_hash,
                    record_format=value["format"], count=record["count"],
                    command="uv run lgpe decode-learnsets --execute",
                ))
            except Exception as exc:
                record.update({"status": "FAILED", "error": f"{type(exc).__name__}: {exc}"})
                failure_rows.append({
                    "domain": "learnset", "source": archive_rel,
                    "status": "FAILED", "error": f"member {index} ({raw_internal}): {type(exc).__name__}: {exc}",
                })
        previous = by_internal.get(raw_internal.as_posix().casefold())
        if record.get("status") in {"PENDING", "DRY_RUN"} and previous and previous.get("status") == "DECODED":
            results.append(previous)
        else:
            results.append(record)
    merged = {str(row.get("source_internal_path", "")).casefold(): row for row in old_rows}
    for row in results:
        merged[str(row["source_internal_path"]).casefold()] = row
    write_jsonl(manifest_path, sorted(merged.values(), key=lambda row: int(row.get("container_index", 0))))
    if execute and receipts:
        add_receipts(project, receipts, trusted_outputs=True)
    if execute:
        resolved = []
        if archive_selected and len(selected_rows) == expected_count and not failure_rows:
            resolved.append({"domain": "learnset", "source": archive_rel})
        merge_failures(project, failure_rows, resolved=resolved)
    if execute and sha256(archive_path) != archive_hash:
        raise ValueError("source archive changed during learnset batch")
    return {
        "archive": archive_rel, "container_members": expected_count,
        "selected_members": len(selected_rows),
        "decoded_members": sum(row.get("status") == "DECODED" for row in results),
        "failed": sum(row.get("status") == "FAILED" for row in results),
        "failed_members": sum(row.get("status") == "FAILED" for row in results),
        "pending_members": sum(row.get("status") == "PENDING" for row in results),
        "unknown_members": sum(row.get("status") == "UNKNOWN" for row in results),
        "execute": execute,
    }


def _safe_relative_posix(value: str, label: str) -> PurePosixPath:
    relative = PurePosixPath(str(value).replace("\\", "/"))
    if relative.is_absolute() or ".." in relative.parts or not relative.parts:
        raise ValueError(f"unsafe {label}: {value}")
    return relative


class _ContainedPathResolver:
    """Check path containment once per shared directory instead of per path component."""

    def __init__(self, root: Path):
        self.root = Path(root).expanduser().resolve()
        self._resolved_parents = {self.root: self.root}
        self._verified_paths: set[Path] = {self.root}

    def resolve(self, path: Path) -> Path:
        candidate = Path(os.path.abspath(os.fspath(path)))
        try:
            relative = candidate.relative_to(self.root)
        except ValueError as exc:
            raise ValueError(f"path outside allowed directory: {candidate}") from exc
        if not relative.parts:
            return self.root
        if candidate in self._verified_paths:
            return candidate

        parent = candidate.parent
        resolved_parent = self._resolved_parents.get(parent)
        if resolved_parent is None:
            resolved_parent = parent.resolve()
            try:
                resolved_parent.relative_to(self.root)
            except ValueError as exc:
                raise ValueError(f"path outside allowed directory: {candidate}") from exc
            self._resolved_parents[parent] = resolved_parent

        if candidate.is_symlink():
            raise ValueError(f"symlink is not allowed in verified path: {candidate}")
        self._verified_paths.add(candidate)
        return candidate


def _map_foreign_windows_path(
    value: str, expected: Path, allowed_root: Path, label: str,
) -> Path:
    """Map a foreign Windows receipt to an already validated local mirror path."""
    windows_path = PureWindowsPath(value)
    if not windows_path.is_absolute():
        raise ValueError(f"{label} is outside its allowed directory: {value}")
    relative_parts = expected.relative_to(allowed_root).parts
    recorded_parts = windows_path.parts
    if len(recorded_parts) < len(relative_parts):
        raise ValueError(f"{label} does not match its local mirror: {value}")
    recorded_suffix = tuple(part.casefold() for part in recorded_parts[-len(relative_parts):])
    expected_suffix = tuple(part.casefold() for part in relative_parts)
    if recorded_suffix != expected_suffix:
        raise ValueError(f"{label} does not match its local mirror: {value}")
    return expected


def _map_foreign_posix_path(
    value: str, expected: Path, allowed_root: Path, label: str,
) -> Path:
    """Map a WSL /mnt/<drive> receipt only when its full path matches locally."""
    posix_path = PurePosixPath(value)
    expected_windows = PureWindowsPath(os.fspath(expected))
    root_windows = PureWindowsPath(os.fspath(allowed_root))
    if not posix_path.is_absolute():
        raise ValueError(f"{label} does not match its local mirror: {value}")

    expected_posix = PurePosixPath(os.fspath(expected))
    root_posix = PurePosixPath(os.fspath(allowed_root))
    if expected_posix.is_absolute() and root_posix.is_absolute():
        try:
            expected_posix.relative_to(root_posix)
        except ValueError as exc:
            raise ValueError(f"expected {label} is outside its allowed directory") from exc
        if tuple(part.casefold() for part in posix_path.parts) == tuple(
            part.casefold() for part in expected_posix.parts
        ):
            return expected

    try:
        expected_windows.relative_to(root_windows)
    except ValueError as exc:
        raise ValueError(f"expected {label} is outside its allowed directory") from exc

    if not expected_windows.anchor:
        raise ValueError(f"{label} cannot map to a local root: {value}")
    expected_parts = tuple(part.casefold() for part in expected_windows.parts[1:])
    recorded_parts = tuple(part.casefold() for part in posix_path.parts[1:])
    if (
        len(recorded_parts) >= 3
        and recorded_parts[0] == "mnt"
        and len(recorded_parts[1]) == 1
        and recorded_parts[2:] == expected_parts
    ):
        return expected
    raise ValueError(f"{label} does not match its local mirror: {value}")


def _resolve_receipt_output_path(
    value: str, expected: Path, resolver: _ContainedPathResolver,
) -> Path:
    recorded = Path(value)
    windows_path = PureWindowsPath(value)
    posix_path = PurePosixPath(value)
    if posix_path.is_absolute() and not recorded.is_absolute():
        return _map_foreign_posix_path(value, expected, resolver.root, "output path")
    if windows_path.is_absolute() and not recorded.is_absolute():
        return _map_foreign_windows_path(value, expected, resolver.root, "output path")
    if recorded.is_absolute() and Path(os.path.abspath(os.fspath(recorded))) == expected:
        return expected
    try:
        output = resolver.resolve(recorded)
    except ValueError:
        if posix_path.is_absolute():
            return _map_foreign_posix_path(value, expected, resolver.root, "output path")
        if windows_path.is_absolute():
            return _map_foreign_windows_path(value, expected, resolver.root, "output path")
        raise
    if output != expected:
        raise ValueError("output mirror path does not match its source")
    return output


def _resolve_receipt_source_path(
    value: str, expected: Path, resolver: _ContainedPathResolver,
) -> Path:
    recorded = Path(value)
    windows_path = PureWindowsPath(value)
    posix_path = PurePosixPath(value)
    if posix_path.is_absolute() and not recorded.is_absolute():
        return _map_foreign_posix_path(value, expected, resolver.root, "source path")
    if windows_path.is_absolute() and not recorded.is_absolute():
        return _map_foreign_windows_path(value, expected, resolver.root, "source path")
    if recorded.is_absolute() and Path(os.path.abspath(os.fspath(recorded))) == expected:
        return expected
    try:
        return resolver.resolve(recorded)
    except ValueError:
        if posix_path.is_absolute():
            return _map_foreign_posix_path(value, expected, resolver.root, "source path")
        if windows_path.is_absolute():
            return _map_foreign_windows_path(value, expected, resolver.root, "source path")
        raise


def verify_outputs(
    project: Path = PROJECT, only_sources: set[str] | None = None,
    root: Path | None = None,
) -> dict:
    manifest = project / "manifests" / "outputs.jsonl"
    if not manifest.is_file():
        return {"registered": 0, "verified": 0, "bad": 0, "errors": ["no output manifest"]}
    decoded_paths = _ContainedPathResolver(project / "decoded")
    game_root = (root or project.parent).expanduser().resolve()
    source_paths = {
        partition: _ContainedPathResolver(path)
        for partition, path in source_dirs(game_root).items()
    }
    source_cache: dict[str, str] = {}
    selected_names = {source.casefold() for source in only_sources} if only_sources is not None else None
    bad = []
    count = 0
    with manifest.open("r", encoding="utf-8") as manifest_file:
        for line_number, line in enumerate(manifest_file, 1):
            if not line.strip():
                continue
            count += 1
            try:
                row = json.loads(line)
                relative_source = str(row.get("relative_source", ""))
                if selected_names is not None and relative_source.casefold() not in selected_names:
                    count -= 1
                    continue
                rel = _safe_relative_posix(relative_source, "source path in output manifest")
                partition = row["partition"]
                if partition not in source_paths:
                    raise ValueError(f"invalid partition in output manifest: {partition}")
                source_resolver = source_paths[partition]

                source_internal = row.get("source_internal_path")
                if source_internal is not None:
                    source_member = _safe_relative_posix(source_internal, "source internal path")
                    expected_source = (
                        decoded_paths.root / VERSION / partition / Path(*rel.parent.parts)
                        / (rel.name + ".contents")
                    ).joinpath(*source_member.parts)
                    source_resolver = decoded_paths
                else:
                    expected_source = source_resolver.root.joinpath(*rel.parts)

                internal_path = row.get("internal_path")
                if internal_path is not None:
                    output_member = _safe_relative_posix(internal_path, "internal output path")
                    expected_output = (
                        decoded_paths.root / VERSION / partition / Path(*rel.parent.parts)
                        / (rel.name + ".contents")
                    ).joinpath(*output_member.parts)
                else:
                    output_extension = PureWindowsPath(str(row["output_file"])).suffix
                    if not output_extension:
                        output_extension = Path(str(row["output_file"])).suffix
                    if (
                        not output_extension.startswith(".")
                        or "/" in output_extension or "\\" in output_extension
                        or output_extension in (".", "..")
                    ):
                        raise ValueError("new extension must be like .json, .png, or .wav")
                    relative_output = rel.with_suffix(output_extension)
                    expected_output = (
                        decoded_paths.root / VERSION / partition / Path(*relative_output.parts)
                    )
                expected_output = decoded_paths.resolve(expected_output)
                output = _resolve_receipt_output_path(
                    str(row["output_file"]), expected_output, decoded_paths,
                )
                if not output.is_file():
                    raise FileNotFoundError(output)
                if sha256(output) != row["output_sha256"]:
                    raise ValueError("output SHA256 mismatch")
                expected_source = source_resolver.resolve(expected_source)
                source = _resolve_receipt_source_path(
                    str(row["source_file"]), expected_source, source_resolver,
                )
                key = os.path.normcase(os.path.abspath(os.fspath(source))).casefold()
                current = source_cache.get(key)
                if current is None:
                    current = sha256(source)
                    source_cache[key] = current
                if current != row["source_sha256"]:
                    raise ValueError("source SHA256 mismatch")
                if source_internal is not None and expected_source != source:
                    raise ValueError("source member path does not match its container receipt")
                container_source = row.get("container_source_file")
                if container_source is not None:
                    container_resolver = source_paths[partition]
                    expected_container = container_resolver.root.joinpath(*rel.parts)
                    expected_container = container_resolver.resolve(expected_container)
                    container_path = _resolve_receipt_source_path(
                        str(container_source), expected_container, container_resolver,
                    )
                    key = os.path.normcase(os.path.abspath(os.fspath(container_path))).casefold()
                    current_container = source_cache.get(key)
                    if current_container is None:
                        current_container = sha256(container_path)
                        source_cache[key] = current_container
                    if current_container != row.get("container_source_sha256"):
                        raise ValueError("container source SHA256 mismatch")
            except Exception as exc:
                bad.append({"line": line_number, "error": f"{type(exc).__name__}: {exc}"})
    return {
        "registered": count, "verified": count - len(bad), "bad": len(bad), "errors": bad,
        "selected_sources": len(only_sources) if only_sources is not None else None,
    }


def verify_samples(root: Path = PROJECT.parent, project: Path = PROJECT) -> dict:
    registered = register_sample_evidence(root, project)
    verification = verify_outputs(project, root=root)
    failure_path = project / "manifests" / "failures.jsonl"
    failure_rows = [
        json.loads(line)
        for line in failure_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ] if failure_path.is_file() else []
    failed_count = sum(row.get("status") == "FAILED" for row in failure_rows)
    unsupported_count = sum(row.get("status") == "UNSUPPORTED" for row in failure_rows)
    unclassified_count = len(failure_rows) - failed_count - unsupported_count
    registered["failed"] = failed_count
    registered["unsupported"] = unsupported_count
    registered["unclassified_failure_statuses"] = unclassified_count
    registered["failed_or_unsupported"] = len(failure_rows)
    return {**registered, **verification}


def run_audio_batch(
    root: Path = PROJECT.parent, project: Path = PROJECT,
    limit: int = 20, execute: bool = False,
    tool: Path | None = None, overwrite: bool = False, timeout: int = 240,
    only_sources: set[str] | None = None,
) -> dict:
    import subprocess
    from .assets_decode import validate_output

    romfs = source_dirs(root)["romfs"]
    tool = tool or (project / "tools" / "bin" / "vgmstream-r2168" / "vgmstream-cli.exe")
    tool = Path(tool)
    audio_items = sorted(
        (row for row in _scan_catalog(project) if row["partition"] == "romfs" and row["suffix"].lower() == ".wem"),
        key=lambda row: row["relative_path"].casefold(),
    )
    files = [(romfs.joinpath(*PurePosixPath(row["relative_path"]).parts), row) for row in audio_items]
    if only_sources is not None:
        selected_names = {source.casefold() for source in only_sources}
        selected = [(path, item) for path, item in files if item["relative_path"].casefold() in selected_names]
    else:
        selected = files if not limit else files[:limit]
    selected_set = {str(path).casefold() for path, _ in selected}
    records = []
    receipts = []
    source_hash_cache = {}
    if execute and (not tool.is_file()):
        raise FileNotFoundError(f"vgmstream-cli missing: {tool}")
    binary_hash = sha256(tool) if execute else None

    existing = existing_domain_outputs(project, "audio")

    for source, item in files:
        rel = item["relative_path"]
        target = decode_destination("romfs", rel, ".wav", project)
        row = {
            "domain": "audio", "source": rel,
            "source_bytes": int(item["bytes"]),
            "output": str(target.relative_to(project)),
        }
        if str(source).casefold() not in selected_set:
            records.append({**row, "status": "PENDING", "reason": "outside current --limit"})
            continue
        if not execute:
            records.append({**row, "status": "DRY_RUN"})
            continue
        source_hash = sha256(source)
        row["source_sha256"] = source_hash
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            receipt = existing.get(str(target.resolve()).casefold())
            if target.exists() and not overwrite:
                if (
                    receipt
                    and receipt.get("source_sha256") == source_hash
                    and receipt.get("output_sha256") == sha256(target)
                ):
                    records.append({
                        **row, "status": "DECODED_EXISTING_VERIFIED",
                        "output_sha256": receipt["output_sha256"],
                        "output_bytes": target.stat().st_size,
                    })
                    continue
                raise FileExistsError(f"unattributed/conflicting output exists: {target}")

            temporary = target.with_name(target.stem + ".lgpe.partial.wav")
            if temporary.exists():
                raise FileExistsError(f"stale partial: {temporary}")
            command = [str(tool), "-i", "-o", str(temporary), str(source)]
            result = subprocess.run(
                command, capture_output=True, text=True, encoding="utf-8",
                errors="replace", timeout=timeout, check=False,
            )
            row["command"] = command
            row["stdout"] = result.stdout
            row["stderr"] = result.stderr
            if result.returncode != 0 or not temporary.is_file():
                raise RuntimeError(f"vgmstream exit {result.returncode}: {result.stderr[-500:]}")
            validation = validate_output(temporary)
            if target.exists() and overwrite:
                temporary.replace(target)
            else:
                temporary.replace(target)
            if sha256(source) != source_hash:
                raise ValueError("source changed during decode")
            output_hash = sha256(target)
            row.update({
                "status": "DECODED", "validation": validation,
                "output_sha256": output_hash, "output_bytes": target.stat().st_size,
            })
            receipts.append(_receipt(
                project, root, rel, source, target,
                "vgmstream-cli -i WEM to PCM16 WAV",
                {"release": "r2168", "executable_sha256": binary_hash},
                source_sha256=source_hash, output_sha256=output_hash,
                status="DECODED", validation=validation, command=command,
            ))
        except Exception as exc:
            row.update({"status": "FAILED", "error": f"{type(exc).__name__}: {exc}"})
            temporary = target.with_name(target.stem + ".lgpe.partial.wav")
            if temporary.exists():
                temporary.unlink()
        records.append(row)

    write_jsonl_selected(project / "manifests" / "audio.jsonl", records, only_sources)
    if execute:
        add_receipts(project, receipts, trusted_outputs=True)
        new_failures = [
            {k: v for k, v in row.items() if k not in {"stdout", "stderr", "command"}}
            for row in records if row.get("status") == "FAILED"
        ]
        merge_failures(
            project, new_failures,
            resolved=[{"domain": "audio", "source": row["source"]} for row in records
                      if row.get("status") in {"DECODED", "DECODED_EXISTING_VERIFIED"}],
        )

    statuses = [row.get("status") for row in records]
    return {
        "scanned_wem": len(files),
        "selected": len(selected),
        "decoded": sum(status in {"DECODED", "DECODED_EXISTING_VERIFIED"} for status in statuses),
        "failed": sum(status == "FAILED" for status in statuses),
        "pending": sum(status == "PENDING" for status in statuses),
        "execute": execute,
    }


def parse_wave_source(data: bytes) -> dict:
    """Parse bounded RIFF/WAVE chunks without treating the suffix as proof."""
    if len(data) < 12 or data[:4] != b"RIFF" or data[8:12] != b"WAVE":
        raise ValueError("source is not a RIFF/WAVE file")
    riff_end = struct.unpack_from("<I", data, 4)[0] + 8
    if riff_end < 12 or riff_end > len(data):
        raise ValueError("RIFF size exceeds source bytes")

    format_chunk = None
    fact_samples = None
    data_bytes = 0
    data_chunks = 0
    offset = 12
    while offset < riff_end:
        if offset + 8 > riff_end:
            raise ValueError("truncated RIFF chunk header")
        tag = data[offset:offset + 4]
        chunk_size = struct.unpack_from("<I", data, offset + 4)[0]
        payload_offset = offset + 8
        payload_end = payload_offset + chunk_size
        if payload_end > riff_end:
            raise ValueError(f"RIFF chunk {tag!r} exceeds declared RIFF boundary")
        payload = data[payload_offset:payload_end]

        if tag == b"fmt ":
            if format_chunk is not None:
                raise ValueError("duplicate RIFF fmt chunk")
            if chunk_size < 16:
                raise ValueError("RIFF fmt chunk is shorter than WAVEFORMAT")
            format_chunk = struct.unpack_from("<HHIIHH", payload, 0) + (chunk_size, payload)
        elif tag == b"fact":
            if chunk_size < 4:
                raise ValueError("RIFF fact chunk lacks sample count")
            if fact_samples is not None:
                raise ValueError("duplicate RIFF fact chunk")
            fact_samples = struct.unpack_from("<I", payload, 0)[0]
        elif tag == b"data":
            data_chunks += 1
            data_bytes += chunk_size

        next_offset = payload_end + (chunk_size & 1)
        if next_offset > riff_end:
            raise ValueError(f"RIFF chunk {tag!r} is missing its alignment byte")
        offset = next_offset

    if offset != riff_end:
        raise ValueError("RIFF chunks do not end at the declared RIFF boundary")
    if format_chunk is None:
        raise ValueError("RIFF/WAVE lacks fmt chunk")
    if not data_chunks:
        raise ValueError("RIFF/WAVE lacks data chunk")

    format_tag, channels, sample_rate, average_bytes_per_second, block_align, bits_per_sample, fmt_size, fmt_payload = format_chunk
    samples_per_block = None
    coefficient_count = None
    if format_tag == 2:
        if bits_per_sample != 4 or channels < 1 or block_align < 1 or sample_rate < 1:
            raise ValueError("invalid Microsoft ADPCM WAVEFORMAT fields")
        if fmt_size < 22:
            raise ValueError("Microsoft ADPCM fmt chunk lacks extension fields")
        extension_size = struct.unpack_from("<H", fmt_payload, 16)[0]
        if extension_size > fmt_size - 18:
            raise ValueError("Microsoft ADPCM extension exceeds fmt chunk")
        samples_per_block, coefficient_count = struct.unpack_from("<HH", fmt_payload, 18)
        if not samples_per_block or not coefficient_count:
            raise ValueError("Microsoft ADPCM fmt chunk has empty block parameters")
        coefficient_bytes_end = 22 + coefficient_count * 4
        if coefficient_bytes_end > fmt_size or coefficient_bytes_end > 18 + extension_size:
            raise ValueError("Microsoft ADPCM coefficient table exceeds fmt extension")
        if fact_samples is None or fact_samples == 0:
            raise ValueError("Microsoft ADPCM WAVE lacks a nonempty fact sample count")
    elif format_tag == 1:
        if channels < 1 or sample_rate < 1 or block_align < 1 or bits_per_sample not in {8, 16, 24, 32}:
            raise ValueError("invalid PCM WAVEFORMAT fields")

    codec = {1: "PCM", 2: "Microsoft ADPCM", 17: "IMA ADPCM"}.get(
        format_tag, f"WAVE format tag 0x{format_tag:04x}",
    )
    return {
        "riff_bytes": riff_end,
        "trailing_bytes": len(data) - riff_end,
        "format_tag": format_tag,
        "codec": codec,
        "channels": channels,
        "sample_rate": sample_rate,
        "average_bytes_per_second": average_bytes_per_second,
        "block_align": block_align,
        "bits_per_sample": bits_per_sample,
        "fmt_chunk_bytes": fmt_size,
        "fact_samples": fact_samples,
        "samples_per_block": samples_per_block,
        "coefficient_count": coefficient_count,
        "data_bytes": data_bytes,
        "data_chunks": data_chunks,
    }


def run_wave_batch(
    root: Path = PROJECT.parent, project: Path = PROJECT,
    limit: int = 20, execute: bool = False,
    tool: Path | None = None, overwrite: bool = False, timeout: int = 240,
    only_sources: set[str] | None = None,
) -> dict:
    """Decode verified Microsoft ADPCM WAVE sources to mirrored PCM16 WAVE."""
    import subprocess

    from .assets_decode import validate_output
    from .bnk_media import _external_path

    tool = Path(tool or (project / "tools" / "bin" / "vgmstream-r2168" / "vgmstream-cli.exe"))
    wave_items = sorted(
        (
            row for row in _scan_catalog(project)
            if row["partition"].casefold() == "romfs" and row["suffix"].casefold() == ".wav"
        ),
        key=lambda row: row["relative_path"].casefold(),
    )
    files = [(_source(root, row["relative_path"]), row) for row in wave_items]
    if only_sources is not None:
        selected_names = {source.replace("\\", "/").casefold() for source in only_sources}
        selected = [
            (path, item) for path, item in files
            if item["relative_path"].replace("\\", "/").casefold() in selected_names
        ]
    else:
        selected = files if not limit else files[:limit]
    selected_set = {item["relative_path"].replace("\\", "/").casefold() for _, item in selected}
    existing = existing_domain_outputs(project, "wave")
    records: list[dict] = []
    receipts: list[dict] = []
    failures: list[dict] = []
    resolved: list[dict] = []
    binary_hash = None

    for source, item in files:
        rel = item["relative_path"].replace("\\", "/")
        target = decode_destination("romfs", rel, ".wav", project)
        row = {
            "domain": "wave", "partition": "romfs", "source": rel,
            "source_bytes": int(item["bytes"]),
            "output": target.relative_to(project).as_posix(),
        }
        if rel.casefold() not in selected_set:
            records.append({**row, "status": "PENDING", "reason": "outside current --limit/source selection"})
            continue
        if not execute:
            records.append({**row, "status": "DRY_RUN"})
            continue

        temporary = target.with_name(target.stem + ".lgpe.partial.wav")
        unattributed_target_hash = None
        temporary_owned = False
        try:
            if not source.is_file():
                raise FileNotFoundError(f"catalogued source is missing: {source}")
            source_hash = sha256(source)
            row["source_sha256"] = source_hash
            if source.stat().st_size != int(item["bytes"]):
                raise ValueError("source byte length differs from scan catalog")
            source_info = parse_wave_source(source.read_bytes())
            row["source_format"] = {
                key: source_info[key] for key in (
                    "format_tag", "codec", "channels", "sample_rate", "bits_per_sample",
                    "block_align", "fact_samples", "data_bytes",
                )
            }
            if source_info["format_tag"] != 2:
                reason = (
                    "source is already PCM; no conversion was performed"
                    if source_info["format_tag"] == 1
                    else f"no verified conversion for {source_info['codec']} WAVE sources"
                )
                records.append({**row, "status": "UNKNOWN", "reason": reason})
                resolved.append({"domain": "wave", "source": rel})
                continue

            receipt = existing.get(str(target.resolve()).casefold())
            if target.exists() and not overwrite:
                if receipt:
                    if (
                        receipt.get("source_sha256") == source_hash
                        and receipt.get("output_sha256") == sha256(target)
                    ):
                        validation = validate_output(target)
                        if (
                            validation["channels"] != source_info["channels"]
                            or validation["sample_rate"] != source_info["sample_rate"]
                            or validation["frames"] != source_info["fact_samples"]
                        ):
                            raise ValueError("existing PCM16 output metadata differs from source WAVE")
                        records.append({
                            **row, "status": "DECODED_EXISTING_VERIFIED",
                            "validation": validation,
                            "output_sha256": receipt["output_sha256"],
                            "output_bytes": target.stat().st_size,
                        })
                        resolved.append({"domain": "wave", "source": rel})
                        continue
                    raise FileExistsError(f"attributed/conflicting output exists: {target}")
                # Preserve an unreceipted file. A fresh decode below may adopt
                # it only when its bytes exactly match the verified result.
                unattributed_target_hash = sha256(target)

            if not tool.is_file():
                raise FileNotFoundError(f"vgmstream-cli missing: {tool}")
            if binary_hash is None:
                binary_hash = sha256(tool)
            target.parent.mkdir(parents=True, exist_ok=True)
            if temporary.exists():
                raise FileExistsError(f"stale partial: {temporary}")
            command = [
                str(tool), "-i", "-o",
                _external_path(temporary, tool), _external_path(source, tool),
            ]
            temporary_owned = True
            result = subprocess.run(
                command, capture_output=True, text=True, encoding="utf-8",
                errors="replace", timeout=timeout, check=False,
            )
            row["command"] = command
            row["stdout"] = result.stdout
            row["stderr"] = result.stderr
            if result.returncode != 0 or not temporary.is_file():
                raise RuntimeError(f"vgmstream exit {result.returncode}: {result.stderr[-500:]}")
            validation = validate_output(temporary)
            if validation["channels"] != source_info["channels"]:
                raise ValueError("decoded channel count differs from source WAVE")
            if validation["sample_rate"] != source_info["sample_rate"]:
                raise ValueError("decoded sample rate differs from source WAVE")
            if validation["frames"] != source_info["fact_samples"]:
                raise ValueError(
                    f"decoded frame count {validation['frames']} differs from source fact count "
                    f"{source_info['fact_samples']}"
                )
            if sha256(source) != source_hash:
                raise ValueError("source changed during decode")
            status = "DECODED"
            if unattributed_target_hash is not None and not overwrite:
                if not target.is_file() or sha256(target) != unattributed_target_hash:
                    raise FileExistsError(f"preexisting output changed during verification: {target}")
                candidate_hash = sha256(temporary)
                if candidate_hash != unattributed_target_hash:
                    raise FileExistsError(
                        f"unattributed output differs from fresh decode; preserved existing file: {target}"
                    )
                temporary.unlink()
                status = "DECODED_EXISTING_VERIFIED"
            else:
                temporary.replace(target)
            output_hash = sha256(target)
            row.update({
                "status": status, "validation": validation,
                "output_sha256": output_hash, "output_bytes": target.stat().st_size,
            })
            receipts.append(_receipt(
                project, root, rel, source, target,
                "vgmstream-cli -i Microsoft ADPCM WAVE to PCM16 WAVE",
                {"release": "r2168", "executable_sha256": binary_hash},
                source_sha256=source_hash, output_sha256=output_hash,
                status=status, validation=validation,
                source_format=row["source_format"], command=command,
            ))
            resolved.append({"domain": "wave", "source": rel})
        except Exception as exc:
            row.update({"status": "FAILED", "error": f"{type(exc).__name__}: {exc}"})
            failures.append({
                "domain": "wave", "source": rel, "status": "FAILED",
                "error": f"{type(exc).__name__}: {exc}",
            })
            if temporary_owned and temporary.exists():
                temporary.unlink()
        records.append(row)

    write_jsonl_selected(project / "manifests" / "waves.jsonl", records, only_sources)
    if execute:
        add_receipts(project, receipts, trusted_outputs=True)
        merge_failures(project, failures, resolved=resolved)

    statuses = [record.get("status") for record in records]
    return {
        "scanned_wav": len(files), "selected": len(selected),
        "decoded": sum(status in {"DECODED", "DECODED_EXISTING_VERIFIED"} for status in statuses),
        "failed": sum(status == "FAILED" for status in statuses),
        "unknown": sum(status == "UNKNOWN" for status in statuses),
        "pending": sum(status == "PENDING" for status in statuses),
        "execute": execute,
    }
