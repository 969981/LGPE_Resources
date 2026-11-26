"""Schema-free, provenance-preserving inspection of LGPE GFBCol roots."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath

from .batch import _scan_catalog, merge_failures, write_jsonl_selected
from .core import PROJECT, VERSION, ensure_inside, sha256, source_dirs
from .flatbuffer_structure import root_table_view
from .gfbcol_structure import root_reference_view


DECODER = "lgpe_research.gfbcol_structure.root_reference_view"
DECODER_VERSION = 3


def _slot0_string_candidate_count(nested_structure: dict) -> int:
    root_slot = next(
        (slot for slot in nested_structure["slots"] if slot["slot_index"] == 0),
        {},
    )
    return sum(
        element.get("table", {}).get("slot0_string_candidate", {}).get("classification")
        == "UTF8_NUL_TERMINATED_LENGTH_PREFIX_CANDIDATE"
        for element in root_slot.get("elements", [])
    )


def _root_reference_view_v2(data: bytes) -> dict:
    """Recreate the exact nested view emitted by decoder v2 for safe migration."""
    expected = root_reference_view(data)
    for slot in expected["slots"]:
        for element in slot.get("elements", []):
            element.get("table", {}).pop("slot0_string_candidate", None)
    expected["analysis_scope"] = "root-slot vector extents and child table envelopes only"
    return expected


def _validate_output(source: Path, output: Path, source_rel: str, source_hash: str) -> dict:
    source_bytes = source.read_bytes()
    if sha256(source) != source_hash:
        raise ValueError("source SHA256 changed during validation")
    obj = json.loads(output.read_text(encoding="utf-8"))
    expected_root = root_table_view(source_bytes)
    if obj.get("schema_status") != "UNKNOWN" or obj.get("slot_semantics") != "UNKNOWN":
        raise ValueError("output must preserve unresolved schema status")
    if obj.get("source") != {
        "partition": "romfs",
        "relative_path": source_rel,
        "bytes": len(source_bytes),
        "sha256": source_hash,
    }:
        raise ValueError("output source identity does not match input")
    if obj.get("root_table") != expected_root:
        raise ValueError("serialized root-table view differs from source bytes")
    expected_nested = root_reference_view(source_bytes)
    if obj.get("nested_structure") != expected_nested:
        raise ValueError("serialized root-reference view differs from source bytes")
    return {
        "root_table_validated": True,
        "nested_structure_validated": True,
        "table_envelope_count": sum(
            len(slot.get("elements", []))
            for slot in expected_nested["slots"]
            if slot.get("classification") == "VECTOR_OF_VALID_TABLE_ENVELOPES"
        ),
        "slot0_string_shape_candidate_count": _slot0_string_candidate_count(expected_nested),
        "schema_status": "UNKNOWN",
        "slot_count": len(expected_root["slots"]),
    }


def _validate_legacy_output(
    source: Path,
    output: Path,
    source_rel: str,
    source_hash: str,
    prior: dict,
    project: Path,
) -> None:
    """Accept only the exact prior root-only decoder before migrating to v3."""
    if prior.get("decoder") != {
        "implementation": "lgpe_research.flatbuffer_structure.root_table_view",
        "version": 1,
    }:
        raise ValueError("existing output is not attributable to the previous collision decoder")
    if prior.get("source_sha256") != source_hash:
        raise ValueError("existing output source hash differs from current source")
    if prior.get("output_sha256") != sha256(output):
        raise ValueError("existing output hash differs from previous collision manifest")
    if prior.get("output") != output.relative_to(project).as_posix():
        raise ValueError("existing output path differs from previous collision manifest")
    source_bytes = source.read_bytes()
    record = json.loads(output.read_text(encoding="utf-8"))
    if record.get("schema_status") != "UNKNOWN" or record.get("slot_semantics") != "UNKNOWN":
        raise ValueError("legacy output does not preserve UNKNOWN semantic status")
    if record.get("source") != {
        "partition": "romfs",
        "relative_path": source_rel,
        "bytes": len(source_bytes),
        "sha256": source_hash,
    }:
        raise ValueError("legacy output source identity differs from current source")
    if record.get("root_table") != root_table_view(source_bytes):
        raise ValueError("legacy root-table view differs from current source")


def _validate_v2_output(
    source: Path,
    output: Path,
    source_rel: str,
    source_hash: str,
    prior: dict,
    project: Path,
) -> None:
    """Accept only the hash-attributed v2 nested output before migrating to v3."""
    if prior.get("decoder") != {"implementation": DECODER, "version": 2}:
        raise ValueError("existing output is not attributable to collision decoder v2")
    if prior.get("source_sha256") != source_hash:
        raise ValueError("existing v2 output source hash differs from current source")
    if prior.get("output_sha256") != sha256(output):
        raise ValueError("existing v2 output hash differs from previous collision manifest")
    if prior.get("output") != output.relative_to(project).as_posix():
        raise ValueError("existing v2 output path differs from previous collision manifest")
    source_bytes = source.read_bytes()
    record = json.loads(output.read_text(encoding="utf-8"))
    if record.get("schema_status") != "UNKNOWN" or record.get("slot_semantics") != "UNKNOWN":
        raise ValueError("v2 output does not preserve UNKNOWN semantic status")
    if record.get("source") != {
        "partition": "romfs",
        "relative_path": source_rel,
        "bytes": len(source_bytes),
        "sha256": source_hash,
    }:
        raise ValueError("v2 output source identity differs from current source")
    if record.get("root_table") != root_table_view(source_bytes):
        raise ValueError("v2 root-table view differs from current source")
    if record.get("nested_structure") != _root_reference_view_v2(source_bytes):
        raise ValueError("v2 nested structure differs from current source")


def _make_record(source_bytes: bytes, source_rel: str, source_hash: str) -> dict:
    return {
        "format_candidate": "FlatBuffers-compatible root/table envelope",
        "analysis_scope": "root table and vectors, child table envelopes, plus slot-0 UTF-8 string-shaped candidates; field types and collision semantics remain UNKNOWN",
        "schema_status": "UNKNOWN",
        "slot_semantics": "UNKNOWN",
        "source": {
            "partition": "romfs",
            "relative_path": source_rel,
            "bytes": len(source_bytes),
            "sha256": source_hash,
        },
        "decoder": {"implementation": DECODER, "version": DECODER_VERSION},
        "root_table": root_table_view(source_bytes),
        "nested_structure": root_reference_view(source_bytes),
    }


def run_collision_batch(
    root: Path = PROJECT.parent,
    project: Path = PROJECT,
    limit: int = 20,
    execute: bool = False,
    only_sources: set[str] | None = None,
) -> dict:
    romfs = source_dirs(root)["romfs"]
    catalog = sorted(
        (row for row in _scan_catalog(project)
         if row["partition"] == "romfs" and row["suffix"].lower() == ".gfbcol"),
        key=lambda row: row["relative_path"].casefold(),
    )
    selected_names = {name.replace("\\", "/").casefold() for name in only_sources} if only_sources is not None else None
    selected = [row for row in catalog if selected_names is None or row["relative_path"].casefold() in selected_names]
    if selected_names is None and limit:
        selected = selected[:limit]
    selected_names_effective = {row["relative_path"].casefold() for row in selected}

    manifest_path = project / "manifests" / "collisions.jsonl"
    previous = {}
    if manifest_path.is_file():
        previous = {
            row.get("source", "").casefold(): row
            for row in (json.loads(line) for line in manifest_path.read_text(encoding="utf-8").splitlines())
            if row.get("source")
        }

    results = []
    root_decoded = failed = schema_unknown = pending = verified = 0
    string_shape_candidates = 0
    for item in catalog:
        rel = item["relative_path"].replace("\\", "/")
        relative = PurePosixPath(rel)
        base = {
            "domain": "collision",
            "partition": "romfs",
            "source": rel,
            "source_bytes": int(item["bytes"]),
            "signature": item["signature"],
        }
        if relative.is_absolute() or ".." in relative.parts or not relative.parts:
            row = {**base, "status": "FAILED", "error": "unsafe relative path in scan catalog"}
            failed += 1
            results.append(row)
            continue
        expected_output = project / "decoded" / VERSION / "romfs" / Path(*relative.parts).with_suffix(".json")
        try:
            output = ensure_inside(expected_output, project / "decoded")
            if output != expected_output:
                raise ValueError(f"decoded output path resolves through a symlink: {expected_output}")
        except (OSError, ValueError) as exc:
            row = {**base, "status": "FAILED", "error": f"{type(exc).__name__}: {exc}"}
            failed += 1
            results.append(row)
            continue
        row = {**base, "output": output.relative_to(project).as_posix()}
        if rel.casefold() not in selected_names_effective:
            row.update({"status": "PENDING", "reason": "outside current selection"})
            pending += 1
            results.append(row)
            continue
        if not execute:
            row.update({"status": "DRY_RUN", "reason": "root, child envelopes, and slot-0 string-shaped candidates will be inspected; schema remains UNKNOWN"})
            results.append(row)
            continue

        try:
            source_path = romfs.joinpath(*relative.parts)
            source = ensure_inside(source_path, romfs)
            if source != source_path:
                raise ValueError("source path resolves through a symlink")
        except (OSError, ValueError) as exc:
            row.update({"status": "FAILED", "error": f"{type(exc).__name__}: {exc}"})
            failed += 1
            results.append(row)
            continue
        wrote_output = False
        existed_before = output.exists()
        temporary = output.with_name(output.name + ".partial")
        try:
            source_hash = sha256(source)
            source_bytes = source.read_bytes()
            if sha256(source) != source_hash:
                raise ValueError("source SHA256 changed during read")
            record = None
            if output.exists():
                prior = previous.get(rel.casefold(), {})
                output_hash = sha256(output)
                prior_matches = (
                    prior.get("source_sha256") == source_hash
                    and prior.get("output_sha256") == output_hash
                    and prior.get("output") == output.relative_to(project).as_posix()
                )
                prior_version = (prior.get("decoder") or {}).get("version")
                if prior_matches and prior_version == DECODER_VERSION:
                    validation = _validate_output(source, output, rel, source_hash)
                elif prior_matches and prior_version == 1:
                    _validate_legacy_output(source, output, rel, source_hash, prior, project)
                    record = _make_record(source_bytes, rel, source_hash)
                elif prior_matches and prior_version == 2:
                    _validate_v2_output(source, output, rel, source_hash, prior, project)
                    record = _make_record(source_bytes, rel, source_hash)
                else:
                    # Recover an interrupted version upgrade only when the current
                    # output itself fully validates against the source and v3 parser.
                    try:
                        validation = _validate_output(source, output, rel, source_hash)
                    except Exception as exc:
                        raise FileExistsError(f"unattributed or conflicting output exists: {output}") from exc
            else:
                try:
                    root_table_view(source_bytes)
                except ValueError as exc:
                    row.pop("output", None)
                    row.update({
                        "status": "UNKNOWN",
                        "structural_status": "ROOT_TABLE_ENVELOPE_UNVALIDATED",
                        "schema_status": "UNKNOWN",
                        "reason": f"generic FlatBuffers-compatible root table not validated: {exc}",
                        "source_sha256": source_hash,
                    })
                    schema_unknown += 1
                    results.append(row)
                    continue
                record = _make_record(source_bytes, rel, source_hash)

            if record is not None:
                output.parent.mkdir(parents=True, exist_ok=True)
                temporary.write_text(json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
                if sha256(source) != source_hash:
                    temporary.unlink(missing_ok=True)
                    raise ValueError("source SHA256 changed during conversion")
                validation = _validate_output(source, temporary, rel, source_hash)
                temporary.replace(output)
                wrote_output = not existed_before

            row.update({
                "status": "UNKNOWN",
                "structural_status": "ROOT_TABLE_ENVELOPE_DECODED",
                "schema_status": "UNKNOWN",
                "reason": "root table, child envelopes, and slot-0 string-shaped values indexed; field types and collision schema remain unresolved",
                "source_sha256": source_hash,
                "output_sha256": sha256(output),
                "output_bytes": output.stat().st_size,
                "validation": validation,
                "decoder": {"implementation": DECODER, "version": DECODER_VERSION},
            })
            root_decoded += 1
            string_shape_candidates += validation["slot0_string_shape_candidate_count"]
            schema_unknown += 1
            verified += 1
        except Exception as exc:
            temporary.unlink(missing_ok=True)
            if wrote_output:
                output.unlink(missing_ok=True)
            row.update({"status": "FAILED", "error": f"{type(exc).__name__}: {exc}"})
            failed += 1
        results.append(row)

    write_jsonl_selected(manifest_path, results, only_sources)
    merge_failures(
        project,
        [{"domain": "collision", "source": row["source"], "status": "FAILED", "error": row.get("error")}
         for row in results if row.get("status") == "FAILED"],
        resolved=[{"domain": "collision", "source": row["source"]}
                  for row in results if row.get("structural_status") == "ROOT_TABLE_ENVELOPE_DECODED"],
    )
    return {
        "catalogued": len(catalog),
        "selected": len(selected),
        "root_table_envelope_decoded": root_decoded,
        "slot0_string_shape_candidates": string_shape_candidates,
        "schema_unknown": schema_unknown,
        "failed": failed,
        "pending": pending,
        "outputs_verified": verified,
        "execute": execute,
        "manifest": str(manifest_path),
    }


def verify_collision_outputs(
    root: Path = PROJECT.parent,
    project: Path = PROJECT,
) -> dict:
    """Rehash and structurally verify every recorded GFBCol analysis output."""
    romfs = source_dirs(root)["romfs"]
    catalog = {
        row["relative_path"].replace("\\", "/").casefold()
        for row in _scan_catalog(project)
        if row["partition"] == "romfs" and row["suffix"].lower() == ".gfbcol"
    }
    manifest = project / "manifests" / "collisions.jsonl"
    if not manifest.is_file():
        return {"catalogued": len(catalog), "manifest_rows": 0, "outputs_verified": 0,
                "unknown": 0, "failed": 0, "pending": 0,
                "errors": [{"error": f"missing collision manifest: {manifest}"}]}

    rows = [json.loads(line) for line in manifest.read_text(encoding="utf-8").splitlines() if line.strip()]
    errors = []
    seen = set()
    counts = {name: 0 for name in (
        "root_views", "nested_structure_views", "table_envelopes",
        "slot0_string_shape_candidates",
        "outputs_verified", "unknown", "failed", "pending",
    )}
    decoded_root = project / "decoded"

    for row in rows:
        rel = str(row.get("source", "")).replace("\\", "/")
        key = rel.casefold()
        if key in seen:
            errors.append({"source": rel, "error": "duplicate source row"})
        seen.add(key)
        if key not in catalog:
            errors.append({"source": rel, "error": "source is absent from the current scan catalog"})
        status = row.get("status")
        if status == "UNKNOWN":
            counts["unknown"] += 1
        elif status == "FAILED":
            counts["failed"] += 1
        elif status == "PENDING":
            counts["pending"] += 1
        elif status != "UNKNOWN":
            errors.append({"source": rel, "error": f"unexpected collision status: {status}"})

        if row.get("structural_status") != "ROOT_TABLE_ENVELOPE_DECODED":
            if row.get("output"):
                errors.append({"source": rel, "error": "output recorded without a validated root-table view"})
            continue

        counts["root_views"] += 1
        try:
            source_rel = PurePosixPath(rel)
            if source_rel.is_absolute() or ".." in source_rel.parts or not source_rel.parts:
                raise ValueError("unsafe source path in collision manifest")
            source_path = romfs.joinpath(*source_rel.parts)
            source = ensure_inside(source_path, romfs)
            if source != source_path:
                raise ValueError("source path resolves through a symlink")
            expected_rel = Path("decoded") / VERSION / "romfs" / Path(*source_rel.parts).with_suffix(".json")
            if row.get("output") != expected_rel.as_posix():
                raise ValueError("output path does not mirror the source")
            output = ensure_inside(project / row["output"], decoded_root)
            if output != project / row["output"]:
                raise ValueError("output path resolves through a symlink")

            source_data = source.read_bytes()
            output_data = output.read_bytes()
            if int(row.get("source_bytes", -1)) != len(source_data):
                raise ValueError("source byte count mismatch")
            source_hash = hashlib.sha256(source_data).hexdigest()
            output_hash = hashlib.sha256(output_data).hexdigest()
            if source_hash != row.get("source_sha256"):
                raise ValueError("source SHA256 mismatch")
            if output_hash != row.get("output_sha256"):
                raise ValueError("output SHA256 mismatch")
            if int(row.get("output_bytes", -1)) != len(output_data):
                raise ValueError("output byte count mismatch")

            record = json.loads(output_data)
            if record.get("schema_status") != "UNKNOWN" or record.get("slot_semantics") != "UNKNOWN":
                raise ValueError("schema/slot UNKNOWN markers are missing")
            if record.get("source") != {
                "partition": "romfs", "relative_path": rel,
                "bytes": len(source_data), "sha256": source_hash,
            }:
                raise ValueError("output source identity differs from input")
            if record.get("root_table") != root_table_view(source_data):
                raise ValueError("serialized root-table view differs from source bytes")
            decoder_version = (row.get("decoder") or {}).get("version")
            if decoder_version == DECODER_VERSION:
                if (row.get("decoder") or {}).get("implementation") != DECODER:
                    raise ValueError("decoder implementation/version mismatch")
                expected_nested = root_reference_view(source_data)
                if record.get("nested_structure") != expected_nested:
                    raise ValueError("serialized root-reference view differs from source bytes")
                counts["slot0_string_shape_candidates"] += _slot0_string_candidate_count(expected_nested)
                counts["nested_structure_views"] += 1
                counts["table_envelopes"] += sum(
                    len(slot.get("elements", []))
                    for slot in expected_nested["slots"]
                    if slot.get("classification") == "VECTOR_OF_VALID_TABLE_ENVELOPES"
                )
            elif decoder_version == 2:
                if (row.get("decoder") or {}).get("implementation") != DECODER:
                    raise ValueError("decoder v2 implementation/version mismatch")
                expected_nested = _root_reference_view_v2(source_data)
                if record.get("nested_structure") != expected_nested:
                    raise ValueError("serialized v2 root-reference view differs from source bytes")
                counts["nested_structure_views"] += 1
                counts["table_envelopes"] += sum(
                    len(slot.get("elements", []))
                    for slot in expected_nested["slots"]
                    if slot.get("classification") == "VECTOR_OF_VALID_TABLE_ENVELOPES"
                )
            elif decoder_version == 1:
                if (row.get("decoder") or {}).get("implementation") != "lgpe_research.flatbuffer_structure.root_table_view":
                    raise ValueError("legacy decoder implementation/version mismatch")
            else:
                raise ValueError(f"unsupported collision decoder version: {decoder_version}")
            if status != "UNKNOWN" or row.get("schema_status") != "UNKNOWN":
                raise ValueError("semantic status must remain UNKNOWN")
            counts["outputs_verified"] += 1
        except Exception as exc:
            errors.append({"source": rel, "error": f"{type(exc).__name__}: {exc}"})

    missing = sorted(catalog - seen)
    if missing:
        errors.append({"error": f"{len(missing)} catalogued GFBCol sources are absent from the manifest", "examples": missing[:10]})
    extra = sorted(seen - catalog)
    if extra:
        errors.append({"error": f"{len(extra)} manifest sources are absent from the current catalog", "examples": extra[:10]})
    if counts["failed"] or counts["pending"]:
        errors.append({
            "error": "collision manifest contains nonterminal FAILED/PENDING rows",
            "failed": counts["failed"], "pending": counts["pending"],
        })

    summary = {
        "catalogued": len(catalog),
        "manifest_rows": len(rows),
        **counts,
        "errors": errors,
    }
    log = project / "logs" / "collision-output-validation.json"
    log.parent.mkdir(parents=True, exist_ok=True)
    temporary = log.with_name(log.name + ".partial")
    temporary.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(log)
    return summary
