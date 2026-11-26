"""Schema-free probe of the eight raw words in candidate GFBCol root slot 3."""
from __future__ import annotations

import struct

from .gfbcol_structure import root_reference_view


def inspect_slot3_words(data: bytes) -> dict:
    """Preserve slot 3's raw words and check one explicitly hypothetical target.

    The first raw word is tested as a forward-relative uoffset candidate. This
    is a hypothesis-only observation and does not change the UNKNOWN schema
    status or assign any word a type or meaning.
    """
    structure = root_reference_view(data)
    try:
        slot = structure["slots"][3]
    except IndexError as exc:
        raise ValueError("root table has no slot 3") from exc
    if slot.get("classification") != "UNTYPED_4_BYTE_VECTOR_CANDIDATE":
        raise ValueError("root slot 3 is not an untyped four-byte vector candidate")

    count = slot.get("vector_count_candidate")
    if count != 8:
        raise ValueError(f"expected 8 candidate words in root slot 3, found {count}")
    vector_target = slot["target_offset"]
    words_start = vector_target + 4
    words = []
    for index in range(count):
        offset = words_start + 4 * index
        value = struct.unpack_from("<I", data, offset)[0]
        words.append({"index": index, "offset": offset, "u32": value, "hex": data[offset:offset + 4].hex()})

    first = words[0]
    candidate_target = first["offset"] + first["u32"]
    target_in_bounds = candidate_target % 4 == 0 and candidate_target + 4 <= len(data)
    target_u32 = struct.unpack_from("<I", data, candidate_target)[0] if target_in_bounds else None
    extent_in_bounds = None
    raw_words = None
    target_alias_index = None
    if target_in_bounds:
        raw_words_start = candidate_target + 4
        extent_in_bounds = target_u32 <= (len(data) - raw_words_start) // 4
        if extent_in_bounds:
            raw_words = [
                struct.unpack_from("<I", data, raw_words_start + 4 * index)[0]
                for index in range(target_u32)
            ]
        relative_to_vector = candidate_target - words_start
        if relative_to_vector >= 0 and relative_to_vector % 4 == 0:
            candidate_index = relative_to_vector // 4
            if candidate_index < count:
                target_alias_index = candidate_index

    return {
        "schema_status": "UNKNOWN",
        "interpretation_status": "HYPOTHESIS_ONLY",
        "slot_index": 3,
        "vector_count_candidate": count,
        "vector_target_offset": vector_target,
        "words": words,
        "first_word_relative_target_candidate": {
            "source_word_index": 0,
            "relative_u32_candidate": first["u32"],
            "target_offset": candidate_target,
            "target_in_bounds": target_in_bounds,
            "target_u32_candidate": target_u32,
            "extent_in_bounds": extent_in_bounds,
            "raw_words": raw_words,
            "target_aliases_slot3_word_index": target_alias_index,
        },
    }
