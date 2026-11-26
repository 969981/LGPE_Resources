"""Conservative nested structure views for LGPE GFBCol candidates.

The code validates FlatBuffers-compatible table/vector envelopes only. It does
not assign field names, scalar types, collision concepts, or runtime semantics.
"""
from __future__ import annotations

import struct

from .flatbuffer_structure import root_table_view


def table_view_at(data: bytes, table_offset: int) -> dict:
    """Validate one table envelope at an absolute buffer offset."""
    if table_offset < 0 or table_offset % 4 or table_offset + 4 > len(data):
        raise ValueError("table offset is unaligned or outside the buffer")
    signed_delta = struct.unpack_from("<i", data, table_offset)[0]
    if signed_delta == 0:
        raise ValueError("table has a zero vtable displacement")
    vtable_offset = table_offset - signed_delta
    if vtable_offset < 0 or vtable_offset % 2 or vtable_offset + 4 > len(data):
        raise ValueError("vtable offset is unaligned or outside the buffer")
    vtable_bytes, object_bytes = struct.unpack_from("<HH", data, vtable_offset)
    if vtable_bytes < 4 or vtable_bytes % 2 or vtable_offset + vtable_bytes > len(data):
        raise ValueError("vtable length is invalid or out of bounds")
    if object_bytes < 4 or table_offset + object_bytes > len(data):
        raise ValueError("table object is out of bounds")
    if vtable_offset < table_offset + object_bytes and vtable_offset + vtable_bytes > table_offset:
        raise ValueError("vtable overlaps table object")

    count = (vtable_bytes - 4) // 2
    field_offsets = struct.unpack_from("<" + "H" * count, data, vtable_offset + 4) if count else ()
    slots = []
    for index, field_offset in enumerate(field_offsets):
        if field_offset == 0:
            slots.append({"slot_index": index, "present": False})
            continue
        if field_offset < 4 or field_offset >= object_bytes:
            raise ValueError(f"vtable slot {index} points outside the table object")
        prefix_bytes = min(4, object_bytes - field_offset)
        start = table_offset + field_offset
        slots.append({
            "slot_index": index,
            "present": True,
            "field_offset": field_offset,
            "raw_prefix_bytes": prefix_bytes,
            "raw_prefix_hex": data[start:start + prefix_bytes].hex(),
            "value_type": "UNKNOWN",
        })

    return {
        "table_offset": table_offset,
        "signed_vtable_delta": signed_delta,
        "vtable_offset": vtable_offset,
        "vtable_bytes": vtable_bytes,
        "vtable_hex": data[vtable_offset:vtable_offset + vtable_bytes].hex(),
        "object_bytes": object_bytes,
        "object_hex": data[table_offset:table_offset + object_bytes].hex(),
        "slots": slots,
    }


def table_string_candidate(data: bytes, table: dict) -> dict:
    """Check whether one table field has a bounded FlatBuffers string shape.

    This is deliberately a candidate classifier: it assigns neither a field
    type nor application semantics. It requires a full four-byte field inside
    the table object, an aligned forward target, an in-bounds length and NUL,
    strict UTF-8, and no overlap with the table object or vtable.
    """
    present = [slot for slot in table["slots"] if slot.get("present")]
    if len(present) != 1:
        return {
            "classification": "UNRESOLVED",
            "reason": f"expected one present child field, found {len(present)}",
        }

    field = present[0]
    field_offset = field["field_offset"]
    if field.get("raw_prefix_bytes") != 4 or field_offset + 4 > table["object_bytes"]:
        return {
            "classification": "UNRESOLVED",
            "reason": "candidate field does not contain a complete four-byte value inside its table object",
            "field_slot_index": field["slot_index"],
            "field_offset": field_offset,
            "raw_prefix_bytes": field.get("raw_prefix_bytes"),
            "object_bytes": table["object_bytes"],
        }

    field_position = table["table_offset"] + field_offset
    relative = struct.unpack_from("<I", data, field_position)[0]
    target = field_position + relative
    details = {
        "field_slot_index": field["slot_index"],
        "field_offset": field_offset,
        "relative_uoffset_candidate": relative,
        "target_offset": target,
    }
    if relative == 0 or target % 4 or target + 4 > len(data):
        return {
            "classification": "UNRESOLVED",
            "reason": "candidate string target is zero, unaligned, or outside the buffer",
            **details,
        }

    length = struct.unpack_from("<I", data, target)[0]
    start = target + 4
    end = start + length
    details.update({"length": length, "raw_bytes_hex": data[start:min(end, len(data))].hex()})
    if end >= len(data):
        return {
            "classification": "UNRESOLVED",
            "reason": "candidate string payload or NUL terminator is outside the buffer",
            **details,
        }
    if data[end] != 0:
        return {
            "classification": "UNRESOLVED",
            "reason": "candidate string payload is not followed by NUL",
            **details,
        }

    candidate_end = end + 1
    structural_ranges = (
        (table["table_offset"], table["table_offset"] + table["object_bytes"]),
        (table["vtable_offset"], table["vtable_offset"] + table["vtable_bytes"]),
    )
    if any(target < range_end and candidate_end > range_start
           for range_start, range_end in structural_ranges):
        return {
            "classification": "UNRESOLVED",
            "reason": "candidate string extent overlaps the child table object or vtable",
            **details,
        }

    try:
        text = data[start:end].decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        return {
            "classification": "UNRESOLVED",
            "reason": "candidate string payload is not valid UTF-8",
            **details,
        }
    return {
        "classification": "UTF8_NUL_TERMINATED_LENGTH_PREFIX_CANDIDATE",
        **details,
        "decoded_text": text,
        "terminator_hex": "00",
    }


def root_reference_view(data: bytes) -> dict:
    """Inspect root vectors and child tables without assigning field semantics."""
    root = root_table_view(data)
    root_offset = root["root_offset"]
    slots = []
    for slot in root["slots"]:
        entry = {
            "slot_index": slot["slot_index"],
            "field_offset": slot.get("field_offset"),
            "root_field_hex": slot.get("raw_prefix_hex"),
            "schema_status": "UNKNOWN",
        }
        if not slot.get("present"):
            entry["classification"] = "ABSENT"
            slots.append(entry)
            continue

        if slot.get("raw_prefix_bytes") != 4:
            entry.update({
                "classification": "UNRESOLVED",
                "reason": "root slot does not contain a complete four-byte value inside the root object",
            })
            slots.append(entry)
            continue

        field_position = root_offset + slot["field_offset"]
        relative = struct.unpack_from("<I", data, field_position)[0]
        target = field_position + relative
        entry.update({"relative_uoffset": relative, "target_offset": target})
        if relative == 0 or target % 4 or target + 4 > len(data):
            entry.update({
                "classification": "UNRESOLVED",
                "reason": "root slot does not point to an aligned in-bounds vector candidate",
            })
            slots.append(entry)
            continue

        count = struct.unpack_from("<I", data, target)[0]
        if count > (len(data) - target - 4) // 4:
            entry.update({
                "classification": "UNRESOLVED",
                "vector_count_candidate": count,
                "reason": "candidate vector extent exceeds the source buffer",
            })
            slots.append(entry)
            continue

        payload_start = target + 4
        payload_end = payload_start + count * 4
        item_views = []
        failures = []
        for index in range(count):
            item_position = payload_start + index * 4
            item_relative = struct.unpack_from("<I", data, item_position)[0]
            item_target = item_position + item_relative
            try:
                if item_relative == 0:
                    raise ValueError("zero element uoffset")
                item_view = table_view_at(data, item_target)
                if slot["slot_index"] == 0:
                    item_view["slot0_string_candidate"] = table_string_candidate(data, item_view)
                item_views.append({"index": index, "relative_uoffset": item_relative, "table": item_view})
            except (ValueError, struct.error) as exc:
                failures.append({"index": index, "error": str(exc)})

        entry["vector_count_candidate"] = count
        entry["vector_payload_bytes"] = count * 4
        if count > 0 and not failures:
            entry.update({
                "classification": "VECTOR_OF_VALID_TABLE_ENVELOPES",
                "elements": item_views,
            })
        elif count == 0:
            entry.update({
                "classification": "EMPTY_VECTOR_CANDIDATE",
                "elements": [],
            })
        else:
            entry.update({
                "classification": "UNTYPED_4_BYTE_VECTOR_CANDIDATE",
                "raw_entries_hex": [data[payload_start + i * 4:payload_start + (i + 1) * 4].hex()
                                    for i in range(count)],
                "table_envelope_candidate_failures": failures,
            })
        slots.append(entry)

    return {
        "analysis_scope": "root-slot vector extents, child table envelopes, and slot-0 string-shaped candidates",
        "schema_status": "UNKNOWN",
        "slot_semantics": "UNKNOWN",
        "field_names_assigned": False,
        "scalar_or_struct_types_assigned": False,
        "slots": slots,
    }
