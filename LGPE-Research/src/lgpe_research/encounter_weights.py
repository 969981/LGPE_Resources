"""Evidence-backed candidate roll intervals for LGPE 1.0.2 wild encounters.

The interval calculation reflects one exact-build static candidate in main. It
does not claim that the candidate is reachable at runtime.
"""
from __future__ import annotations

import csv
import hashlib
import json
import subprocess
from collections import Counter, defaultdict
from pathlib import Path

from .core import NCA, VERSION, ensure_inside, source_dirs
from .gamedata_decode import FlatReader, encounters


SOURCE_RELATIVE = "bin/field/param/encount/encount_data_p.bin"
DECODED_RELATIVE = "bin/field/param/encount/encount_data_p.json"
SCHEMA_RELATIVE = "tools/src/pkNX/FlatBuffers/LGPE/Schemas/wild.fbs"
EXPECTED_SOURCE_SHA256 = "3dac771dffee508ff8fea41d255326640aefb67c88c2d96fd1ecda7b82b1ce46"
EXPECTED_DECODED_SHA256 = "23e429a0470a356cffe44e323e8977db0e29c94c09937758676051980df077a2"
EXPECTED_SCHEMA_SHA256 = "0f1e114b4ef92986bb674c341dfe75e418d257f5d4a2eb6997c8b9ca629e2a1b"
EXPECTED_PKNX_COMMIT = "d191cd0e5c05f2af81d9a41c1f1d82e6621b351a"
EXPECTED_MAIN_SHA256 = "1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8"

# Field indices are from the hash-pinned pkNX LGPE wild.fbs schema.
MODES = (
    {"name": "Ground", "vector_field": 10, "total_field": 9},
    {"name": "Water", "vector_field": 18, "total_field": 17},
    {"name": "Sky", "vector_field": 41, "total_field": 40},
)
SLOT_FIELDS = {"probability": 0, "species": 1, "form": 2}
ROLL_DOMAIN = 100
SELECTION_CANDIDATE_VA = 0x71002FDF90
SELECTION_CALLER_VA = 0x71002F8A50
SELECTION_CALLSITE_VA = 0x71002F8E2C
MAIN_IMAGE_BASE = 0x7100000000


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def probability_intervals(weights: list[int], declared_total: int) -> list[dict[str, int]]:
    """Return half-open cumulative intervals and reject inconsistent weights."""
    if not isinstance(declared_total, int) or isinstance(declared_total, bool):
        raise ValueError("declared probability total must be an integer")
    if not 0 <= declared_total <= ROLL_DOMAIN:
        raise ValueError(f"declared probability total must be between 0 and {ROLL_DOMAIN}")
    intervals = []
    cumulative = 0
    for index, weight in enumerate(weights):
        if not isinstance(weight, int) or isinstance(weight, bool):
            raise ValueError(f"slot {index} probability must be an integer")
        if weight < 0:
            raise ValueError(f"slot {index} probability is negative")
        start = cumulative
        cumulative += weight
        intervals.append({
            "slot_index": index,
            "roll_start_inclusive": start,
            "roll_end_exclusive": cumulative,
            "probability": weight,
        })
    if cumulative != declared_total:
        raise ValueError(
            f"slot probability sum {cumulative} does not match declared total {declared_total}"
        )
    return intervals


def _field_offset(reader: FlatReader, table: int, field_index: int) -> int | None:
    return reader.field(table, field_index)


def _vector(reader: FlatReader, table: int, field_index: int) -> tuple[int, int, list[int]]:
    field = reader.field(table, field_index)
    if field is None:
        raise ValueError(f"required vector field {field_index} is absent")
    vector_start = reader.target(field)
    count = reader.read("I", vector_start)
    if count > 100000 or vector_start + 4 + count * 4 > len(reader.data):
        raise ValueError(f"vector field {field_index} is out of bounds")
    entries = [vector_start + 4 + index * 4 for index in range(count)]
    return vector_start, field, [reader.target(entry) for entry in entries]


def _hex_offset(offset: int | None) -> str:
    return "" if offset is None else f"0x{offset:x}"


def _leaf_count(value) -> int:
    if isinstance(value, dict):
        return sum(_leaf_count(child) for child in value.values())
    if isinstance(value, list):
        return sum(_leaf_count(child) for child in value)
    return 1


def _verify_interval_csv(path: Path, expected_rows: int, expected_groups: int) -> int:
    grouped: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    count = 0
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        for row in reader:
            count += 1
            if row.get("candidate_reachability") != "UNVERIFIED_RUNTIME":
                raise ValueError(f"CSV row {count} lost the runtime-reachability caveat")
            grouped[(row["table_index"], row["mode"])].append(row)
    if count != expected_rows:
        raise ValueError(f"interval CSV row count mismatch: expected {expected_rows}, actual {count}")
    if len(grouped) != expected_groups:
        raise ValueError(f"interval CSV group count mismatch: expected {expected_groups}, actual {len(grouped)}")
    for key, rows in grouped.items():
        rows.sort(key=lambda row: int(row["slot_index"]))
        cumulative = 0
        declared_total = int(rows[0]["declared_total"])
        for index, row in enumerate(rows):
            probability = int(row["probability"])
            start = int(row["roll_start_inclusive"])
            end = int(row["roll_end_exclusive"])
            if int(row["slot_index"]) != index:
                raise ValueError(f"non-contiguous slot indexes in CSV group {key}")
            if row["declared_total"] != rows[0]["declared_total"]:
                raise ValueError(f"inconsistent declared totals in CSV group {key}")
            if start != cumulative or end - start != probability:
                raise ValueError(f"invalid interval boundary in CSV group {key} slot {index}")
            cumulative = end
        if cumulative != declared_total:
            raise ValueError(f"CSV probability sum does not match declared total in group {key}")
    return len(grouped)


def build_encounter_weight_report(project: Path, game_root: Path) -> tuple[list[dict], dict]:
    """Validate pinned local evidence and derive interval and offset records."""
    project = project.resolve()
    romfs = source_dirs(game_root)["romfs"]
    exefs = source_dirs(game_root)["exefs"]
    source_path = romfs / SOURCE_RELATIVE
    decoded_path = project / "decoded" / VERSION / "romfs" / DECODED_RELATIVE
    schema_path = project / SCHEMA_RELATIVE
    main_path = exefs / "main"
    for label, path in (
        ("encounter source", source_path), ("decoded encounter JSON", decoded_path),
        ("pinned pkNX schema", schema_path), ("1.0.2 main", main_path),
    ):
        if not path.is_file():
            raise FileNotFoundError(f"{label} missing: {path}")

    hashes = {
        "source_sha256": sha256_file(source_path),
        "decoded_json_sha256": sha256_file(decoded_path),
        "schema_sha256": sha256_file(schema_path),
        "main_sha256": sha256_file(main_path),
    }
    expected_hashes = {
        "source_sha256": EXPECTED_SOURCE_SHA256,
        "decoded_json_sha256": EXPECTED_DECODED_SHA256,
        "schema_sha256": EXPECTED_SCHEMA_SHA256,
        "main_sha256": EXPECTED_MAIN_SHA256,
    }
    for name, expected in expected_hashes.items():
        if hashes[name] != expected:
            raise ValueError(f"{name} mismatch: expected {expected}, actual {hashes[name]}")

    git = subprocess.run(
        ["git", "-C", str(project / "tools" / "src" / "pkNX"), "rev-parse", "HEAD"],
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    if git != EXPECTED_PKNX_COMMIT:
        raise ValueError(f"pinned pkNX commit mismatch: expected {EXPECTED_PKNX_COMMIT}, actual {git}")

    data = source_path.read_bytes()
    decoded_json = json.loads(decoded_path.read_text(encoding="utf-8"))
    source_decode = encounters(data)
    if source_decode != decoded_json:
        raise ValueError("source FlatBuffer parse does not exactly match the pinned JSON export")

    reader = FlatReader(data)
    root_table = reader.target(0)
    root_vector_start, root_vector_field, table_offsets = _vector(reader, root_table, 0)
    tables = decoded_json["tables"]
    if len(tables) != len(table_offsets):
        raise ValueError("source table vector count differs from decoded JSON")

    records: list[dict] = []
    mode_counts: dict[str, Counter[int]] = {mode["name"]: Counter() for mode in MODES}
    total_groups = 0
    inactive_groups = 0
    for table_index, (table, table_offset) in enumerate(zip(tables, table_offsets)):
        table_entry_offset = root_vector_start + 4 + table_index * 4
        zone_id = table["ZoneID"]
        zone_field_offset = _field_offset(reader, table_offset, 0)
        if zone_field_offset is None:
            raise ValueError(f"table {table_index} has no ZoneID field in source bytes")
        if reader.read("Q", zone_field_offset) != zone_id:
            raise ValueError(f"table {table_index} ZoneID source offset mismatch")

        for mode in MODES:
            name = mode["name"]
            vector_name = f"{name}Table"
            declared_total_name = f"{vector_name}RandChanceTotal"
            declared_total = table[declared_total_name]
            vector_start, vector_field_offset, slot_offsets = _vector(
                reader, table_offset, mode["vector_field"]
            )
            slots = table[vector_name]
            if len(slot_offsets) != len(slots):
                raise ValueError(f"table {table_index} {vector_name} slot count mismatch")
            weights = [slot["Probability"] for slot in slots]
            intervals = probability_intervals(weights, declared_total)
            if declared_total not in (0, ROLL_DOMAIN):
                raise ValueError(
                    f"table {table_index} {vector_name} total {declared_total} is outside observed 0/100 totals"
                )
            total_groups += 1
            inactive_groups += int(declared_total == 0)
            mode_counts[name][declared_total] += 1

            total_field_offset = _field_offset(reader, table_offset, mode["total_field"])
            vector_entry_offsets = [vector_start + 4 + index * 4 for index in range(len(slots))]
            for slot, slot_offset, vector_entry_offset, interval in zip(
                slots, slot_offsets, vector_entry_offsets, intervals
            ):
                offsets = {
                    key: _field_offset(reader, slot_offset, field_index)
                    for key, field_index in SLOT_FIELDS.items()
                }
                source_values = {
                    "probability": reader.scalar(slot_offset, SLOT_FIELDS["probability"], "i"),
                    "species": reader.scalar(slot_offset, SLOT_FIELDS["species"], "i"),
                    "form": reader.scalar(slot_offset, SLOT_FIELDS["form"], "h"),
                }
                expected_values = {
                    "probability": slot["Probability"],
                    "species": slot["Species"],
                    "form": slot["Form"],
                }
                if source_values != expected_values:
                    raise ValueError(
                        f"table {table_index} {vector_name} source slot differs at raw offset 0x{slot_offset:x}"
                    )
                records.append({
                    "source_relative_path": SOURCE_RELATIVE,
                    "source_sha256": hashes["source_sha256"],
                    "decoded_json_relative_path": f"decoded/{VERSION}/romfs/{DECODED_RELATIVE}",
                    "decoded_json_sha256": hashes["decoded_json_sha256"],
                    "schema_relative_path": SCHEMA_RELATIVE,
                    "schema_sha256": hashes["schema_sha256"],
                    "pknx_commit": git,
                    "main_sha256": hashes["main_sha256"],
                    "candidate_va": f"0x{SELECTION_CANDIDATE_VA:x}",
                    "caller_va": f"0x{SELECTION_CALLER_VA:x}",
                    "callsite_va": f"0x{SELECTION_CALLSITE_VA:x}",
                    "candidate_reachability": "UNVERIFIED_RUNTIME",
                    "table_index": table_index,
                    "table_vector_entry_offset": _hex_offset(table_entry_offset),
                    "table_offset": _hex_offset(table_offset),
                    "zone_id_field_offset": _hex_offset(zone_field_offset),
                    "zone_id": zone_id,
                    "zone_id_hex": f"0x{zone_id:x}",
                    "mode": name,
                    "mode_vector_field_index": mode["vector_field"],
                    "mode_vector_field_offset": _hex_offset(vector_field_offset),
                    "slot_vector_offset": _hex_offset(vector_start),
                    "declared_total_field_index": mode["total_field"],
                    "declared_total_field_offset": _hex_offset(total_field_offset),
                    "declared_total": declared_total,
                    "slot_index": interval["slot_index"],
                    "slot_vector_entry_offset": _hex_offset(vector_entry_offset),
                    "slot_table_offset": _hex_offset(slot_offset),
                    "probability_field_offset": _hex_offset(offsets["probability"]),
                    "species_field_offset": _hex_offset(offsets["species"]),
                    "form_field_offset": _hex_offset(offsets["form"]),
                    "probability": interval["probability"],
                    "roll_start_inclusive": interval["roll_start_inclusive"],
                    "roll_end_exclusive": interval["roll_end_exclusive"],
                    "species": slot["Species"],
                    "form": slot["Form"],
                })

    summary = {
        "format": "LGPE 1.0.2 static wild-encounter candidate roll intervals",
        "source_version": "Pokemon Let's Go Pikachu 1.0.2",
        "source_nca_folder": NCA,
        **hashes,
        "pknx_commit": git,
        "schema_fields": {
            "root_tables_vector": 0,
            "zone_id": 0,
            "mode_vectors": {mode["name"]: mode["vector_field"] for mode in MODES},
            "declared_probability_totals": {mode["name"]: mode["total_field"] for mode in MODES},
            "slot": SLOT_FIELDS,
        },
        "raw_offset_origin": "byte zero of source_relative_path",
        "roll_domain": f"[0,{ROLL_DOMAIN})",
        "candidate_selection_rule": (
            "candidate computes an RNG-derived value modulo 100, accumulates slot Probability, "
            "and selects the first cumulative value greater than the roll"
        ),
        "candidate_evidence": {
            "main_image_base": f"0x{MAIN_IMAGE_BASE:x}",
            "function_va": f"0x{SELECTION_CANDIDATE_VA:x}",
            "direct_caller_va": f"0x{SELECTION_CALLER_VA:x}",
            "callsite_va": f"0x{SELECTION_CALLSITE_VA:x}",
            "runtime_reachability": "UNVERIFIED",
            "limitation": (
                "the caller has no direct incoming references in the saved Ghidra database; "
                "the candidate's local root is not linked to the constructed encounter resource owner"
            ),
            "notes": "docs/research/T10-notes.md",
        },
        "cross_checks": {
            "source_parse_equals_pinned_json": True,
            "decoded_leaf_values_compared": _leaf_count(source_decode),
            "table_count": len(tables),
            "mode_table_groups": total_groups,
            "slot_rows": len(records),
            "inactive_zero_total_groups": inactive_groups,
            "probability_totals_by_mode": {
                name: {str(total): count for total, count in sorted(counter.items())}
                for name, counter in mode_counts.items()
            },
        },
        "outputs": {},
    }
    for label, path, expected in (
        ("encounter source", source_path, hashes["source_sha256"]),
        ("decoded encounter JSON", decoded_path, hashes["decoded_json_sha256"]),
        ("pinned pkNX schema", schema_path, hashes["schema_sha256"]),
        ("1.0.2 main", main_path, hashes["main_sha256"]),
    ):
        if sha256_file(path) != expected:
            raise ValueError(f"{label} changed while deriving the report")
    return records, summary


def write_encounter_weight_report(project: Path, game_root: Path, csv_path: Path, json_path: Path) -> dict:
    records, summary = build_encounter_weight_report(project, game_root)
    project = project.resolve()
    manifest_dir = (project / "manifests").resolve()
    csv_path = ensure_inside(csv_path, manifest_dir)
    json_path = ensure_inside(json_path, manifest_dir)
    if csv_path == json_path:
        raise ValueError("CSV and JSON outputs must use different paths")
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    columns = list(records[0]) if records else []
    temp_csv = csv_path.with_name(csv_path.name + ".lgpe.partial")
    if temp_csv.exists():
        raise FileExistsError(f"remove stale partial manually: {temp_csv}")
    try:
        with temp_csv.open("x", encoding="utf-8-sig", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=columns)
            writer.writeheader()
            writer.writerows(records)
        temp_csv.replace(csv_path)
    finally:
        if temp_csv.exists():
            temp_csv.unlink()
    verified_groups = _verify_interval_csv(
        csv_path, len(records), summary["cross_checks"]["mode_table_groups"]
    )
    summary["outputs"] = {
        "csv": csv_path.relative_to(project).as_posix(),
        "csv_sha256": sha256_file(csv_path),
        "csv_rows": len(records),
        "verified_csv_rows": len(records),
        "verified_mode_table_groups": verified_groups,
        "json": json_path.relative_to(project).as_posix(),
    }
    json_bytes = (json.dumps(summary, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    temp_json = json_path.with_name(json_path.name + ".lgpe.partial")
    if temp_json.exists():
        raise FileExistsError(f"remove stale partial manually: {temp_json}")
    try:
        with temp_json.open("xb") as stream:
            stream.write(json_bytes)
        temp_json.replace(json_path)
    finally:
        if temp_json.exists():
            temp_json.unlink()
    return summary
