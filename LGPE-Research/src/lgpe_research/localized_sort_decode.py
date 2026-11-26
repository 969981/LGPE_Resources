"""Lossless structure decoders for LGPE 1.0.2 localized sort resources."""
from __future__ import annotations

SCHEMA = "lgpe-localized-sort-v1"


def decode_sort_table(data: bytes) -> dict:
    """Decode the indexed u16 values read from each *_sort_table.dat."""
    if not data:
        raise ValueError("empty sort table")
    if len(data) % 2:
        raise ValueError(f"sort table byte length is not divisible by 2: {len(data)}")
    entries = [
        {
            "index": index,
            "byte_offset": offset,
            "value_u16le": int.from_bytes(data[offset:offset + 2], "little"),
        }
        for index, offset in enumerate(range(0, len(data), 2))
    ]
    return {
        "schema": SCHEMA,
        "format": "u16le-index-table",
        "element_width": 2,
        "byte_order": "little",
        "entry_count": len(entries),
        "entries": entries,
        "raw_byte_length": len(data),
        "raw_hex": data.hex(),
    }


def decode_initial_to_sort(data: bytes) -> dict:
    """Decode the two-u16 records read from each *_initial_to_sort.dat."""
    if not data:
        raise ValueError("empty initial-to-sort table")
    if len(data) % 4:
        raise ValueError(
            f"initial-to-sort byte length is not divisible by 4: {len(data)}"
        )
    entries = []
    for index, offset in enumerate(range(0, len(data), 4)):
        entries.append({
            "index": index,
            "byte_offset": offset,
            "first_u16le": int.from_bytes(data[offset:offset + 2], "little"),
            "second_u16le": int.from_bytes(data[offset + 2:offset + 4], "little"),
        })
    return {
        "schema": SCHEMA,
        "format": "u16le-pair-table",
        "element_width": 4,
        "field_width": 2,
        "byte_order": "little",
        "entry_count": len(entries),
        "entries": entries,
        "raw_byte_length": len(data),
        "raw_hex": data.hex(),
    }
