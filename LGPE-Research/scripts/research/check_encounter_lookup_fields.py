#!/usr/bin/env python3
"""Cross-check the LGPE 1.0.2 encounter fields read by two static helpers."""

from __future__ import annotations

import hashlib
import json
import re
import struct
from pathlib import Path


EXPECTED_SOURCE_SHA256 = "3dac771dffee508ff8fea41d255326640aefb67c88c2d96fd1ecda7b82b1ce46"
EXPECTED_JSON_SHA256 = "23e429a0470a356cffe44e323e8977db0e29c94c09937758676051980df077a2"
EXPECTED_SCHEMA_SHA256 = "0f1e114b4ef92986bb674c341dfe75e418d257f5d4a2eb6997c8b9ca629e2a1b"
FIELDS = {
    0: ("ZoneID", "<Q"),
    5: ("GroundSpawnDuration", "<i"),
    6: ("GroundTableEncounterRate", "<i"),
    13: ("WaterSpawnDuration", "<i"),
    14: ("WaterTableEncounterRate", "<i"),
    36: ("SkySpawnDuration", "<i"),
    37: ("SkyTableEncounterRate", "<i"),
}
ZONE_FIELDS = {
    7: ("GroundTableLevelMin", "<i"),
    8: ("GroundTableLevelMax", "<i"),
    15: ("WaterTableLevelMin", "<i"),
    16: ("WaterTableLevelMax", "<i"),
    38: ("SkyTableLevelMin", "<i"),
    39: ("SkyTableLevelMax", "<i"),
}
CHANCE_TOTAL_FIELDS = {
    9: ("GroundTableRandChanceTotal", "<i"),
    17: ("WaterTableRandChanceTotal", "<i"),
    40: ("SkyTableRandChanceTotal", "<i"),
}
SLOT_VECTORS = {
    10: "GroundTable",
    18: "WaterTable",
    41: "SkyTable",
}
SLOT_CHANCE_TOTALS = {
    10: 9,
    18: 17,
    41: 40,
}
SLOT_FIELDS = {
    0: ("Probability", "<i"),
    1: ("Species", "<i"),
    2: ("Form", "<h"),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    source = (
        root.parent
        / "1.0.2/2b7730a9e56498bbafac2002d4908c6b_NCA/1/bin/field/param/encount/encount_data_p.bin"
    )
    decoded = root / "decoded/1.0.2/romfs/bin/field/param/encount/encount_data_p.json"
    schema = root / "tools/src/pkNX/FlatBuffers/LGPE/Schemas/wild.fbs"
    source_hash = sha256(source)
    decoded_hash = sha256(decoded)
    schema_hash = sha256(schema)
    if source_hash != EXPECTED_SOURCE_SHA256:
        raise SystemExit(f"source SHA-256 mismatch: {source_hash}")
    if decoded_hash != EXPECTED_JSON_SHA256:
        raise SystemExit(f"decoded JSON SHA-256 mismatch: {decoded_hash}")
    if schema_hash != EXPECTED_SCHEMA_SHA256:
        raise SystemExit(f"pinned pkNX schema SHA-256 mismatch: {schema_hash}")

    schema_text = schema.read_text(encoding="utf-8")
    table_match = re.search(r"table\s+EncounterTable\s*\{([^}]*)\}", schema_text, re.S)
    if table_match is None:
        raise SystemExit("EncounterTable declaration missing from pinned schema")
    schema_fields: list[tuple[str, str]] = []
    for line in table_match.group(1).splitlines():
        field_match = re.match(r"\s*(\w+)\s*:\s*(\w+|\[\w+\])", line)
        if field_match:
            schema_fields.append((field_match.group(1), field_match.group(2)))
    schema_type = {"<Q": "ulong", "<i": "int", "<h": "short"}
    expected_fields = {**FIELDS, **ZONE_FIELDS, **CHANCE_TOTAL_FIELDS}
    for index, (name, value_format) in expected_fields.items():
        expected_schema_field = (name, schema_type[value_format])
        if index >= len(schema_fields) or schema_fields[index] != expected_schema_field:
            raise SystemExit(
                f"schema field {index} mismatch: expected={expected_schema_field}, "
                f"actual={schema_fields[index] if index < len(schema_fields) else None}"
            )
    for index, name in SLOT_VECTORS.items():
        expected_schema_field = (name, "[EncounterSlot]")
        if index >= len(schema_fields) or schema_fields[index] != expected_schema_field:
            raise SystemExit(
                f"schema vector field {index} mismatch: expected={expected_schema_field}, "
                f"actual={schema_fields[index] if index < len(schema_fields) else None}"
            )

    slot_schema_match = re.search(r"table\s+EncounterSlot\s*\{([^}]*)\}", schema_text, re.S)
    if slot_schema_match is None:
        raise SystemExit("EncounterSlot declaration missing from pinned schema")
    slot_schema_fields = []
    for line in slot_schema_match.group(1).splitlines():
        field_match = re.match(r"\s*(\w+)\s*:\s*(\w+|\[\w+\])", line)
        if field_match:
            slot_schema_fields.append((field_match.group(1), field_match.group(2)))
    for index, (name, value_format) in SLOT_FIELDS.items():
        expected_schema_field = (name, schema_type[value_format])
        if index >= len(slot_schema_fields) or slot_schema_fields[index] != expected_schema_field:
            raise SystemExit(
                f"EncounterSlot schema field {index} mismatch: expected={expected_schema_field}, "
                f"actual={slot_schema_fields[index] if index < len(slot_schema_fields) else None}"
            )

    data = source.read_bytes()
    tables = json.loads(decoded.read_text(encoding="utf-8"))["tables"]
    root_offset = struct.unpack_from("<I", data, 0)[0]
    root_vtable = root_offset - struct.unpack_from("<i", data, root_offset)[0]
    root_field0 = struct.unpack_from("<H", data, root_vtable + 4)[0]
    vector = root_offset + root_field0 + struct.unpack_from("<I", data, root_offset + root_field0)[0]
    count = struct.unpack_from("<I", data, vector)[0]
    if count != len(tables) or count != 70:
        raise SystemExit(f"table count mismatch: binary={count}, json={len(tables)}")

    def scalar_value(table: int, field_index: int, value_format: str) -> int:
        vtable = table - struct.unpack_from("<i", data, table)[0]
        vtable_size = struct.unpack_from("<H", data, vtable)[0]
        slot = 4 + 2 * field_index
        offset = (
            struct.unpack_from("<H", data, vtable + slot)[0]
            if slot + 2 <= vtable_size
            else 0
        )
        return struct.unpack_from(value_format, data, table + offset)[0] if offset else 0

    def table_vector(table: int, field_index: int) -> list[int]:
        vtable = table - struct.unpack_from("<i", data, table)[0]
        vtable_size = struct.unpack_from("<H", data, vtable)[0]
        slot = 4 + 2 * field_index
        offset = (
            struct.unpack_from("<H", data, vtable + slot)[0]
            if slot + 2 <= vtable_size
            else 0
        )
        if not offset:
            return []
        vector = table + offset
        vector += struct.unpack_from("<I", data, vector)[0]
        count = struct.unpack_from("<I", data, vector)[0]
        entries = []
        for index in range(count):
            entry = vector + 4 + index * 4
            entries.append(entry + struct.unpack_from("<I", data, entry)[0])
        return entries

    comparisons = 0
    slot_count = 0
    chance_total_checks = 0
    probability_sum_counts = {name: {} for name in SLOT_VECTORS.values()}
    for index, expected in enumerate(tables):
        entry = vector + 4 + index * 4
        table = entry + struct.unpack_from("<I", data, entry)[0]
        for field_index, (name, value_format) in expected_fields.items():
            value = scalar_value(table, field_index, value_format)
            json_value = expected.get(name, 0)
            if value != json_value:
                raise SystemExit(
                    f"table {index} {name}: source={value}, JSON={json_value}, "
                    f"schema_field_index={field_index}"
                )
            comparisons += 1
        for vector_index, vector_name in SLOT_VECTORS.items():
            actual_slots = table_vector(table, vector_index)
            expected_slots = expected.get(vector_name, [])
            if len(actual_slots) != len(expected_slots):
                raise SystemExit(
                    f"table {index} {vector_name}: binary slots={len(actual_slots)}, "
                    f"JSON slots={len(expected_slots)}"
                )
            probability_sum = 0
            for slot_index, (slot_table, json_slot) in enumerate(zip(actual_slots, expected_slots)):
                for slot_field_index, (name, value_format) in SLOT_FIELDS.items():
                    value = scalar_value(slot_table, slot_field_index, value_format)
                    json_value = json_slot.get(name, 0)
                    if value != json_value:
                        raise SystemExit(
                            f"table {index} {vector_name}[{slot_index}] {name}: "
                            f"source={value}, JSON={json_value}"
                        )
                    comparisons += 1
                    if slot_field_index == 0:
                        probability_sum += value
                slot_count += 1
            total_field_index = SLOT_CHANCE_TOTALS[vector_index]
            total_name, _ = expected_fields[total_field_index]
            declared_total = scalar_value(table, total_field_index, "<i")
            if probability_sum != declared_total:
                raise SystemExit(
                    f"table {index} {vector_name}: summed Probability={probability_sum}, "
                    f"{total_name}={declared_total}"
                )
            counts = probability_sum_counts[vector_name]
            counts[probability_sum] = counts.get(probability_sum, 0) + 1
            chance_total_checks += 1

    print(
        "encounter lookup-field cross-check passed: "
        f"tables={count} scalar_and_slot_comparisons={comparisons} slot_rows={slot_count} "
        f"chance_total_checks={chance_total_checks} "
        f"probability_sum_counts={probability_sum_counts} "
        f"source_sha256={source_hash} json_sha256={decoded_hash} "
        f"schema_sha256={schema_hash}"
    )


if __name__ == "__main__":
    main()
