import struct
from collections import Counter, defaultdict


def assert_message_document_matches(existing: dict, redecoded: dict) -> None:
    if existing != redecoded:
        raise ValueError("decoded message reference differs from source DAT/TBL re-decode")


def inspect_candidate_table(table_data: bytes, message_lines: list[dict]) -> dict:
    """Cross-reference loader-proven rows to message indexes without naming semantics."""
    if len(table_data) < 4:
        raise ValueError("item-hash table is shorter than its 4-byte count header")

    count = struct.unpack_from("<I", table_data, 0)[0]
    expected_size = 4 + count * 0x10
    if len(table_data) != expected_size:
        raise ValueError(
            f"item-hash table count/stride mismatch: count={count}, "
            f"stride=0x10, expected={expected_size}, actual={len(table_data)}"
        )

    messages_by_index = defaultdict(list)
    for line in message_lines:
        if not isinstance(line, dict):
            raise ValueError("message lines must be objects")
        index = line.get("index")
        message_id = line.get("id")
        if isinstance(index, bool) or not isinstance(index, int) or not isinstance(message_id, str):
            raise ValueError("each message line needs an integer index and string id")
        messages_by_index[index].append(message_id)

    entries = []
    unmatched = []
    ambiguous = []
    loader_values = Counter()
    for record_index in range(count):
        offset = 4 + record_index * 0x10
        key_u64, value_u64 = struct.unpack_from("<QQ", table_data, offset)
        loader_value_u16 = value_u64 & 0xFFFF
        matching_ids = messages_by_index.get(loader_value_u16, [])
        loader_values[loader_value_u16] += 1
        if not matching_ids:
            unmatched.append(record_index)
        elif len(matching_ids) > 1:
            ambiguous.append(record_index)
        entries.append({
            "record_index": record_index,
            "file_offset": offset,
            "raw_hex": table_data[offset:offset + 0x10].hex(),
            "key_u64_at_0": f"{key_u64:016x}",
            "value_u64_at_8": f"{value_u64:016x}",
            "loader_value_u16": loader_value_u16,
            "matching_message_ids": list(matching_ids),
        })

    return {
        "format_status": "DECODED",
        "field_semantics_status": "UNKNOWN",
        "candidate_record_count": count,
        "record_stride_bytes": 0x10,
        "message_line_count": len(message_lines),
        "message_index_match_count": count - len(unmatched),
        "unreferenced_message_indexes": sorted(
            index for index in messages_by_index if not loader_values[index]
        ),
        "unmatched_record_indexes": unmatched,
        "ambiguous_record_indexes": ambiguous,
        "duplicate_loader_value_u16_values": sorted(
            value for value, occurrences in loader_values.items() if occurrences > 1
        ),
        "entries": entries,
        "interpretation": (
            "The exact 1.0.2 main establishes a count-prefixed 0x10-byte row, uses "
            "the qword at +0 as a hash-map key, and stores the low u16 of the qword "
            "at +8. The English itemname comparison is numeric only; key hash "
            "algorithm, label semantics, and runtime reachability remain unverified."
        ),
    }
