"""Auditable BSEQ structure decoding via the pinned external pbseqtool source."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath

from . import batch
from .core import PROJECT, VERSION, decode_destination, sha256, source_dirs, add_receipts

PBSEQTOOL_COMMIT = "6f122d1b7945797cae472960b798bf28523f8acd"
PBSEQTOOL_RELATIVE = Path("tools/src/pbseqtool")
SCHEMA = "lgpe-research.bseq.v1"
DEMO_SEQUENCE_PREFIX = "bin/demo/sequence/"
_LOADED: dict[str, tuple[object, object, str]] = {}


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def format_exception_chain(exc: BaseException) -> str:
    """Render an exception and its explicit/implicit cause without loops."""
    parts = []
    seen = set()
    current = exc
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        parts.append(f"{type(current).__name__}: {current}")
        if current.__cause__ is not None:
            current = current.__cause__
        elif not current.__suppress_context__:
            current = current.__context__
        else:
            current = None
    return " <- ".join(parts)


def parser_failure_diagnostic(exc: BaseException, source_data: bytes) -> dict:
    """Capture parser cursor/header evidence without assigning command semantics."""
    chain = []
    seen = set()
    current = exc
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        chain.append(current)
        if current.__cause__ is not None:
            current = current.__cause__
        elif not current.__suppress_context__:
            current = current.__context__
        else:
            current = None

    deepest = chain[-1] if chain else exc
    diagnostic = {
        "exception_type": type(exc).__name__,
        "cause": {"type": type(deepest).__name__, "message": str(deepest)},
    }
    if isinstance(deepest, KeyError) and deepest.args:
        diagnostic["lookup_key"] = str(deepest.args[0])
    if isinstance(deepest, UnicodeDecodeError):
        diagnostic["decode_error"] = {
            "encoding": deepest.encoding,
            "start": deepest.start,
            "end": deepest.end,
            "reason": deepest.reason,
        }

    parser_locals = None
    for error in chain:
        traceback = error.__traceback__
        while traceback is not None:
            local_vars = traceback.tb_frame.f_locals
            if (
                traceback.tb_frame.f_code.co_name == "from_bytes"
                and isinstance(local_vars.get("offset"), int)
                and "cmd_id" in local_vars
            ):
                parser_locals = local_vars
                break
            traceback = traceback.tb_next
        if parser_locals is not None:
            break

    if parser_locals is None:
        diagnostic["parser_frame_found"] = False
        return diagnostic

    offset = parser_locals["offset"]
    command_id = str(parser_locals["cmd_id"])
    diagnostic.update({
        "parser_frame_found": True,
        "command_offset": offset,
        "command_id_hex": command_id,
        "command_header_raw_hex": source_data[offset:offset + 16].hex(),
    })
    options = parser_locals.get("opts")
    if isinstance(options, dict):
        diagnostic["parsed_option_words"] = {
            key: value for key, value in options.items()
            if key.startswith("Option") and isinstance(value, int)
        }

    parameter = parser_locals.get("param")
    if parameter is not None:
        names = getattr(parameter, "names", [])
        diagnostic["parser_parameter"] = {
            "name": names[0] if names else None,
            "value_type": getattr(parameter, "value_type", None),
            "length": getattr(parameter, "length", None),
        }

    argument_bytes = parser_locals.get("arg_bytes")
    evidence_bytes = source_data[offset:offset + 128]
    if isinstance(argument_bytes, (bytes, bytearray)):
        argument_bytes = bytes(argument_bytes)
        diagnostic["parameter_bytes"] = {
            "length": len(argument_bytes),
            "sha256": _sha256_bytes(argument_bytes),
        }
        evidence_bytes += argument_bytes

    ascii_runs = []
    for match in re.finditer(rb"[\x20-\x7e]{6,}", evidence_bytes):
        run = match.group().decode("ascii")
        if run not in ascii_runs:
            ascii_runs.append(run[:256])
        if len(ascii_runs) == 8:
            break
    if ascii_runs:
        diagnostic["nearby_ascii_runs"] = ascii_runs
    return diagnostic


def demo_sequence_unsupported_reason(relative_path: str) -> str | None:
    if relative_path.replace("\\", "/").casefold().startswith(DEMO_SEQUENCE_PREFIX):
        return (
            "pbseqtool does not support demo/cutscene sequences per its README; "
            "the attempted parser exception is retained in parser_error"
        )
    return None


def load_pbseqtool(project: Path = PROJECT):
    """Load pbseqtool without vendoring it or leaking its generic module names."""
    checkout = (project / PBSEQTOOL_RELATIVE).resolve()
    key = str(checkout)
    if key in _LOADED:
        return _LOADED[key]
    if not (checkout / ".git").is_dir():
        raise FileNotFoundError(
            f"pbseqtool source is missing at {checkout}; run scripts/Fetch-Tool-Sources.ps1"
        )
    head = subprocess.run(
        ["git", "-C", str(checkout), "rev-parse", "HEAD"],
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    if head != PBSEQTOOL_COMMIT:
        raise ValueError(f"pbseqtool commit mismatch: expected {PBSEQTOOL_COMMIT}, got {head}")
    dirty = subprocess.run(
        ["git", "-C", str(checkout), "status", "--porcelain", "--untracked-files=no"],
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    if dirty:
        raise ValueError("pbseqtool tracked source has local modifications")

    readme = (checkout / "README.md").read_text(encoding="utf-8")
    reuse_permission = "feel free" in readme.casefold() and "use it as a base" in readme.casefold()
    if not reuse_permission:
        raise ValueError("pbseqtool README reuse permission text was not found")

    reference_path = checkout / "commandDictionaries" / "LGPECommandReference.json"
    reference_bytes = reference_path.read_bytes()
    reference_hash = _sha256_bytes(reference_bytes)
    alias_name = f"_lgpe_pbseq_cmdReference_{head[:12]}"
    sesd_name = f"_lgpe_pbseq_sesd_{head[:12]}"
    reference_spec = importlib.util.spec_from_file_location(alias_name, checkout / "cmdReference.py")
    if reference_spec is None or reference_spec.loader is None:
        raise ImportError(f"cannot load pbseqtool reference module from {checkout}")
    reference_module = importlib.util.module_from_spec(reference_spec)
    sys.modules[alias_name] = reference_module

    previous_reference = sys.modules.get("cmdReference")
    try:
        sys.modules["cmdReference"] = reference_module
        sesd_spec = importlib.util.spec_from_file_location(sesd_name, checkout / "sesd.py")
        if sesd_spec is None or sesd_spec.loader is None:
            raise ImportError(f"cannot load pbseqtool SESD module from {checkout}")
        sesd_module = importlib.util.module_from_spec(sesd_spec)
        sys.modules[sesd_name] = sesd_module
        reference_spec.loader.exec_module(reference_module)
        sesd_spec.loader.exec_module(sesd_module)
    finally:
        if previous_reference is None:
            sys.modules.pop("cmdReference", None)
        else:
            sys.modules["cmdReference"] = previous_reference

    command_reference = reference_module.CmdReference(json.loads(reference_bytes))
    if command_reference.game != "LGPE":
        raise ValueError(f"pinned command dictionary is for {command_reference.game}, not LGPE")
    result = (sesd_module.SESD, command_reference, reference_hash)
    _LOADED[key] = result
    return result


def decode_bseq_bytes(
    data: bytes, source_stem: str, sesd_class=None, command_reference=None,
    command_dictionary_sha256: str | None = None,
) -> dict:
    """Decode a BSEQ and independently reparse its normalized serialization."""
    if sesd_class is None or command_reference is None:
        sesd_class, command_reference, loaded_hash = load_pbseqtool()
        command_dictionary_sha256 = command_dictionary_sha256 or loaded_hash
    if len(data) < 16 or data[:4] != b"SESD":
        raise ValueError("input is not a complete SESD BSEQ header")
    game_version = int.from_bytes(data[4:8], "little")
    if game_version != 3:
        raise ValueError(f"SESD version {game_version} is not the LGPE version 3")

    parsed = sesd_class.from_bytes(data, "LGPE", command_reference)
    sequence = parsed.get_json_dict_simple(seq_name=source_stem, opts_setting=2)
    rebuilt = parsed.get_bseq()
    reparsed = sesd_class.from_bytes(rebuilt, "LGPE", command_reference)
    reparsed_sequence = reparsed.get_json_dict_simple(seq_name=source_stem, opts_setting=2)
    semantic_equal = sequence == reparsed_sequence
    if not semantic_equal:
        raise ValueError("pbseqtool semantic dictionary changed after serialize/reparse")
    groups = sequence.get("Data", [])
    command_count = sum(len(group.get("Commands", [])) for group in groups)
    return {
        "schema": SCHEMA,
        "decoder": {
            "name": "pbseqtool SESD parser",
            "commit": PBSEQTOOL_COMMIT,
            "game_dictionary": "LGPECommandReference.json",
            "command_dictionary_sha256": command_dictionary_sha256,
            "license_status": "README grants reuse as a base; no formal LICENSE file",
            "semantics_status": "command names/parameters are parser-reference fields; gameplay meanings remain unverified",
        },
        "source": {
            "format": "SESD",
            "lgpe_format_version": game_version,
            "size": len(data),
            "sha256": _sha256_bytes(data),
            "raw_hex": data.hex(),
        },
        "validation": {
            "group_count": len(groups),
            "command_count": command_count,
            "byte_roundtrip_exact": rebuilt == data,
            "semantic_roundtrip_equal": semantic_equal,
            "rebuilt_size": len(rebuilt),
        },
        "sequence": sequence,
    }


def run_bseq_batch(
    root: Path = PROJECT.parent, project: Path = PROJECT, limit: int = 20,
    execute: bool = False, only_sources: set[str] | None = None,
) -> dict:
    romfs = source_dirs(root)["romfs"]
    catalog = batch._scan_catalog(project)
    files = sorted(
        (row for row in catalog if row["partition"] == "romfs" and row["suffix"].casefold() == ".bseq"),
        key=lambda row: row["relative_path"].casefold(),
    )
    canonical = {row["relative_path"].casefold(): row["relative_path"] for row in files}
    if only_sources is not None:
        requested = {name.replace("\\", "/").casefold() for name in only_sources}
        missing = sorted(requested - canonical.keys())
        if missing:
            raise ValueError(f"source list contains paths not found in the .bseq scan: {missing[:5]}")
        selected_names = requested
        selected = [row for row in files if row["relative_path"].casefold() in selected_names]
    else:
        selected = files if not limit else files[:limit]
        selected_names = {row["relative_path"].casefold() for row in selected}

    parser_class = command_reference = None
    dictionary_hash = None
    if execute:
        parser_class, command_reference, dictionary_hash = load_pbseqtool(project)

    old_rows = {}
    manifest = project / "manifests" / "bseq.jsonl"
    if manifest.is_file():
        old_rows = {
            str(row.get("source", "")).casefold(): row
            for row in (json.loads(line) for line in manifest.read_text(encoding="utf-8").splitlines() if line.strip())
        }
    receipts = []
    records = []
    failures = []
    resolved = []
    selected_count = 0
    for item in files:
        rel = item["relative_path"]
        source = romfs.joinpath(*PurePosixPath(rel).parts)
        target = decode_destination("romfs", rel, ".json", project)
        row = {
            "domain": "bseq", "source": rel,
            "source_bytes": int(item["bytes"]),
            "output": str(target.relative_to(project)),
        }
        if rel.casefold() not in selected_names:
            row["status"] = "PENDING"
            row["reason"] = "outside current --limit or --sources-file selection"
            records.append(row)
            continue
        selected_count += 1
        if not execute:
            row["status"] = "DRY_RUN"
            records.append(row)
            continue
        temporary = None
        source_data = b""
        try:
            source_hash = sha256(source)
            row["source_sha256"] = source_hash
            old = old_rows.get(rel.casefold(), {})
            if target.exists():
                if (
                    old.get("status") in {"DECODED", "DECODED_EXISTING_VERIFIED"}
                    and old.get("source_sha256") == source_hash
                    and old.get("output_sha256") == sha256(target)
                ):
                    row.update({
                        "status": "DECODED_EXISTING_VERIFIED",
                        "output_sha256": old["output_sha256"],
                        "output_bytes": target.stat().st_size,
                        "validation": old.get("validation", {}),
                        "decoder_commit": PBSEQTOOL_COMMIT,
                    })
                    records.append(row)
                    resolved.append({"domain": "bseq", "source": rel})
                    continue
                raise FileExistsError(f"unattributed/conflicting BSEQ JSON exists: {target}")

            source_data = source.read_bytes()
            if _sha256_bytes(source_data) != source_hash:
                raise ValueError("BSEQ source changed between hash and parser read")
            try:
                decoded = decode_bseq_bytes(
                    source_data, PurePosixPath(rel).stem, parser_class,
                    command_reference, dictionary_hash,
                )
            except Exception as exc:
                parser_error = format_exception_chain(exc)
                unsupported_reason = demo_sequence_unsupported_reason(rel)
                if unsupported_reason:
                    row.update({
                        "status": "UNSUPPORTED", "reason": unsupported_reason,
                        "parser_error": parser_error,
                        "parser_diagnostic": parser_failure_diagnostic(exc, source_data),
                    })
                    resolved.append({"domain": "bseq", "source": rel})
                else:
                    row.update({"status": "FAILED", "error": parser_error})
                records.append(row)
                failures.append({key: value for key, value in row.items() if key not in {"output"}})
                continue
            temporary = target.with_name(target.name + ".partial")
            if temporary.exists():
                raise FileExistsError(f"stale partial BSEQ output: {temporary}")
            target.parent.mkdir(parents=True, exist_ok=True)
            temporary.write_text(json.dumps(decoded, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            temporary.replace(target)
            if sha256(source) != source_hash:
                target.unlink(missing_ok=True)
                raise ValueError("BSEQ source changed during decode")
            output_hash = sha256(target)
            validation = decoded["validation"]
            row.update({
                "status": "DECODED", "output_sha256": output_hash,
                "output_bytes": target.stat().st_size, "validation": validation,
                "decoder_commit": PBSEQTOOL_COMMIT,
                "command_dictionary_sha256": dictionary_hash,
            })
            receipts.append(batch._receipt(
                project, root, rel, source, target,
                "pbseqtool SESD → JSON with raw source bytes retained",
                {
                    "name": "pbseqtool", "commit": PBSEQTOOL_COMMIT,
                    "command_dictionary_sha256": dictionary_hash,
                    "license_status": "README reuse permission; no formal LICENSE",
                },
                source_sha256=source_hash, output_sha256=output_hash,
                status="DECODED", validation=validation,
                command=["uv", "run", "lgpe", "decode-sequences", "--execute"],
                schema=SCHEMA,
            ))
            records.append(row)
            resolved.append({"domain": "bseq", "source": rel})
        except Exception as exc:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
            row.update({"status": "FAILED", "error": f"{type(exc).__name__}: {exc}"})
            records.append(row)
            failures.append({key: value for key, value in row.items() if key not in {"output"}})

    batch.write_jsonl_selected(manifest, records, only_sources)
    if execute:
        if receipts:
            add_receipts(project, receipts, trusted_outputs=True)
        batch.merge_failures(project, failures, resolved=resolved)
    statuses = [row.get("status") for row in records]
    return {
        "scanned_bseq": len(files),
        "selected": selected_count,
        "decoded": sum(status in {"DECODED", "DECODED_EXISTING_VERIFIED"} for status in statuses),
        "failed": sum(status == "FAILED" for status in statuses),
        "unsupported": sum(status == "UNSUPPORTED" for status in statuses),
        "pending": sum(status == "PENDING" for status in statuses),
        "execute": execute,
        "manifest": str(manifest),
    }
