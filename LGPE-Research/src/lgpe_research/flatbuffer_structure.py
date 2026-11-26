"""Schema-free FlatBuffers root-table inspection.

This module validates only the generic root/table/vtable envelope. A table's
slot bytes are preserved without assigning scalar, offset, or struct types.
"""
from __future__ import annotations

import struct


def root_table_view(data: bytes) -> dict:
    """Return a bounded, untyped view of a FlatBuffers-compatible root table.

    The format has no file identifier by default, so this is deliberately a
    structural candidate check rather than proof of a particular schema.
    """
    if len(data) < 8:
        raise ValueError("buffer is too short for root and table offsets")

    root_offset = struct.unpack_from("<I", data, 0)[0]
    if root_offset < 4 or root_offset % 4 or root_offset + 4 > len(data):
        raise ValueError("root table offset is outside the buffer")

    signed_vtable_delta = struct.unpack_from("<i", data, root_offset)[0]
    if signed_vtable_delta == 0:
        raise ValueError("root table has a zero vtable displacement")
    vtable_offset = root_offset - signed_vtable_delta
    if vtable_offset < 0 or vtable_offset + 4 > len(data):
        raise ValueError("vtable offset is outside the buffer")

    vtable_bytes, object_bytes = struct.unpack_from("<HH", data, vtable_offset)
    if vtable_bytes < 4 or vtable_bytes % 2:
        raise ValueError("vtable byte length is invalid")
    if vtable_offset + vtable_bytes > len(data):
        raise ValueError("vtable exceeds the buffer")
    if object_bytes < 4 or root_offset + object_bytes > len(data):
        raise ValueError("root object exceeds the buffer")
    if (
        vtable_offset < root_offset + object_bytes
        and vtable_offset + vtable_bytes > root_offset
    ):
        raise ValueError("root vtable overlaps the root object")

    field_count = (vtable_bytes - 4) // 2
    field_offsets = struct.unpack_from("<" + "H" * field_count, data, vtable_offset + 4) if field_count else ()
    slots = []
    for index, field_offset in enumerate(field_offsets):
        if field_offset == 0:
            slots.append({"slot_index": index, "present": False})
            continue
        if field_offset < 4 or field_offset >= object_bytes:
            raise ValueError(f"vtable slot {index} points outside the root object")
        prefix_bytes = min(4, object_bytes - field_offset)
        start = root_offset + field_offset
        slots.append({
            "slot_index": index,
            "present": True,
            "field_offset": field_offset,
            "raw_prefix_bytes": prefix_bytes,
            "raw_prefix_hex": data[start:start + prefix_bytes].hex(),
            "value_type": "UNKNOWN",
        })

    return {
        "root_offset": root_offset,
        "signed_vtable_delta": signed_vtable_delta,
        "vtable_offset": vtable_offset,
        "vtable_bytes": vtable_bytes,
        "object_bytes": object_bytes,
        "slots": slots,
    }
