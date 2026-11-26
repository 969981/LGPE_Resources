"""Schema-free view of GFBCol root-slot-zero child-field candidates."""
from __future__ import annotations

from .gfbcol_structure import root_reference_view


def inspect_slot0_string_candidates(data: bytes) -> dict:
    """Decode valid string-shaped child fields without asserting their schema.

    A value is reported as a string candidate only when the root slot is a
    validated vector of table envelopes and the child field's hypothetical
    forward uoffset reaches a bounded, aligned, length-prefixed UTF-8 byte
    sequence followed by NUL. The field type and meaning remain UNKNOWN.
    """
    structure = root_reference_view(data)
    try:
        root_slot = structure["slots"][0]
    except IndexError as exc:
        raise ValueError("root table has no slot 0") from exc
    classification = root_slot.get("classification")
    if classification != "VECTOR_OF_VALID_TABLE_ENVELOPES":
        raise ValueError("root slot 0 is not a validated vector of table envelopes")

    elements = [
        {
            "element_index": item["index"],
            "table_offset": item["table"]["table_offset"],
            "string_candidate": item["table"].get("slot0_string_candidate", {
                "classification": "UNRESOLVED",
                "reason": "slot-0 string candidate was not produced",
            }),
        }
        for item in root_slot.get("elements", [])
    ]

    return {
        "schema_status": "UNKNOWN",
        "field_types_assigned": False,
        "root_slot_index": 0,
        "root_slot_classification": classification,
        "child_element_count": len(elements),
        "elements": elements,
    }
