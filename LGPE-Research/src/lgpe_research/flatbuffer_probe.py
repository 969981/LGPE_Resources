"""Schema-free probes for possible FlatBuffers relative targets."""
from __future__ import annotations

import struct

from .flatbuffer_structure import root_table_view


def probe_relative_targets(data: bytes) -> dict:
    """Record bounded forward-relative target candidates without typing fields.

    A table slot may be a scalar or a uoffset. This probe reports both the raw
    slot bytes and what the bytes would address if interpreted as a uoffset;
    it does not assert that the slot is an offset or that the target is a vector.
    """
    root = root_table_view(data)
    observations = []
    for slot in root["slots"]:
        observation = {
            "slot_index": slot["slot_index"],
            "present": slot["present"],
            "interpretation_status": "UNKNOWN",
        }
        if not slot["present"]:
            observations.append(observation)
            continue

        observation["field_offset"] = slot["field_offset"]
        observation["raw_prefix_hex"] = slot["raw_prefix_hex"]
        if slot["raw_prefix_bytes"] < 4:
            observation.update({
                "candidate_relative_target": None,
                "target_in_bounds": False,
                "reason": "slot has fewer than four bytes",
            })
            observations.append(observation)
            continue

        raw_value = struct.unpack("<I", bytes.fromhex(slot["raw_prefix_hex"][:8]))[0]
        source_location = root["root_offset"] + slot["field_offset"]
        target = source_location + raw_value
        target_in_bounds = 0 <= target <= len(data) - 4
        observation.update({
            "candidate_u32_relative_value": raw_value,
            "candidate_relative_target": target,
            "target_in_bounds": target_in_bounds,
            "target_is_4_byte_aligned": target % 4 == 0,
        })
        if target_in_bounds:
            candidate_word = struct.unpack_from("<I", data, target)[0]
            observation["candidate_u32_at_target"] = candidate_word
            observation["bytes_after_target_word"] = len(data) - (target + 4)
            # This is only the minimum extent if the target word were a length
            # and elements were one byte each; element size/type are unknown.
            observation["minimum_byte_extent_fits"] = (
                target + 4 + candidate_word <= len(data)
            )
        else:
            observation["minimum_byte_extent_fits"] = False
        observations.append(observation)

    return {
        "analysis_status": "HYPOTHESIS_ONLY",
        "classification": "UNKNOWN",
        "root_offset": root["root_offset"],
        "slots": observations,
        "interpretation_limit": (
            "Each relative target and target u32 is a candidate only; no slot is "
            "assigned an offset, vector, scalar, or Game Freak schema type."
        ),
    }
