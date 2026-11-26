#!/usr/bin/env python3
"""Read-only, schema-free probe of GFBCol root-slot references.

This reports whether the root slots can be structurally interpreted as
FlatBuffers-style vectors and whether vector elements validate as table
envelopes. It assigns no field names or gameplay meanings.
"""
from __future__ import annotations

import argparse
import csv
import json
import struct
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath

from lgpe_research.core import PROJECT, source_dirs


def _table_layout(data: bytes, table_offset: int) -> tuple[int, int, tuple[int, ...]]:
    if table_offset < 0 or table_offset % 4 or table_offset + 4 > len(data):
        raise ValueError("table offset unaligned or outside buffer")
    delta = struct.unpack_from("<i", data, table_offset)[0]
    if delta == 0:
        raise ValueError("zero vtable displacement")
    vtable_offset = table_offset - delta
    if vtable_offset < 0 or vtable_offset % 2 or vtable_offset + 4 > len(data):
        raise ValueError("vtable offset unaligned or outside buffer")
    vtable_bytes, object_bytes = struct.unpack_from("<HH", data, vtable_offset)
    if vtable_bytes < 4 or vtable_bytes % 2 or vtable_offset + vtable_bytes > len(data):
        raise ValueError("invalid or out-of-bounds vtable")
    if object_bytes < 4 or table_offset + object_bytes > len(data):
        raise ValueError("table object outside buffer")
    if vtable_offset < table_offset + object_bytes and vtable_offset + vtable_bytes > table_offset:
        raise ValueError("vtable overlaps table object")
    count = (vtable_bytes - 4) // 2
    fields = struct.unpack_from("<" + "H" * count, data, vtable_offset + 4) if count else ()
    if any(field and (field < 4 or field >= object_bytes) for field in fields):
        raise ValueError("vtable field offset outside table object")
    return vtable_bytes, object_bytes, tuple(fields)


def inspect_source(data: bytes) -> dict:
    root_offset = struct.unpack_from("<I", data, 0)[0]
    root_layout = _table_layout(data, root_offset)
    root_fields = root_layout[2]
    slots = []
    for index, field_offset in enumerate(root_fields):
        result = {"slot_index": index, "field_offset": field_offset or None}
        if not field_offset:
            result["status"] = "ABSENT"
            slots.append(result)
            continue
        field_position = root_offset + field_offset
        if field_position + 4 > len(data):
            result["status"] = "FIELD_OUT_OF_BOUNDS"
            slots.append(result)
            continue
        relative = struct.unpack_from("<I", data, field_position)[0]
        target = field_position + relative
        result["relative_uoffset"] = relative
        result["target_offset"] = target
        if relative == 0 or target % 4 or target + 4 > len(data):
            result["status"] = "NOT_VALID_VECTOR_TARGET"
            slots.append(result)
            continue
        count = struct.unpack_from("<I", data, target)[0]
        result["vector_count"] = count
        if count > (len(data) - target - 4) // 4:
            result["status"] = "VECTOR_BOUNDS_INVALID"
            slots.append(result)
            continue
        layouts = []
        failures = []
        for item_index in range(count):
            element_position = target + 4 + 4 * item_index
            element_uoffset = struct.unpack_from("<I", data, element_position)[0]
            element_target = element_position + element_uoffset
            try:
                if element_uoffset == 0:
                    raise ValueError("zero element uoffset")
                layouts.append(_table_layout(data, element_target))
            except (ValueError, struct.error) as exc:
                failures.append({"index": item_index, "error": str(exc)})
        result["table_element_count"] = len(layouts)
        result["non_table_element_count"] = len(failures)
        result["table_layouts"] = [list(layout) for layout in sorted(set(layouts))]
        result["table_layout_counts"] = {
            json.dumps(layout, separators=(",", ":")): count
            for layout, count in Counter(layouts).items()
        }
        result["non_table_examples"] = failures[:3]
        result["status"] = "VECTOR_OF_VALID_TABLES" if count and not failures else "VECTOR_ELEMENTS_UNRESOLVED"
        slots.append(result)
    return {
        "bytes": len(data),
        "root_offset": root_offset,
        "root_layout": [root_layout[0], root_layout[1], list(root_layout[2])],
        "slots": slots,
    }


def run(root: Path, project: Path) -> dict:
    romfs = source_dirs(root)["romfs"]
    catalog_path = project / "manifests" / "files.csv"
    with catalog_path.open("r", encoding="utf-8-sig", newline="") as stream:
        sources = [
            row["relative_path"].replace("\\", "/")
            for row in csv.DictReader(stream)
            if row["partition"] == "romfs" and row["suffix"].lower() == ".gfbcol"
        ]

    root_layouts = Counter()
    slot_counts = defaultdict(Counter)
    slot_statuses = defaultdict(Counter)
    slot_table_layouts = defaultdict(Counter)
    source_failures = []
    examples = defaultdict(list)
    elements = defaultdict(Counter)
    for relative in sources:
        relpath = PurePosixPath(relative)
        if relpath.is_absolute() or ".." in relpath.parts:
            source_failures.append({"source": relative, "error": "unsafe catalog path"})
            continue
        source = romfs.joinpath(*relpath.parts)
        try:
            data = source.read_bytes()
            view = inspect_source(data)
        except (OSError, ValueError, struct.error) as exc:
            source_failures.append({"source": relative, "error": f"{type(exc).__name__}: {exc}"})
            continue
        root_layouts[json.dumps(view["root_layout"], separators=(",", ":"))] += 1
        for slot in view["slots"]:
            index = slot["slot_index"]
            status = slot["status"]
            slot_statuses[index][status] += 1
            if "vector_count" in slot:
                slot_counts[index][slot["vector_count"]] += 1
            if slot.get("table_layouts"):
                slot_table_layouts[index].update(slot["table_layout_counts"])
            elements[index]["table"] += slot.get("table_element_count", 0)
            elements[index]["unresolved"] += slot.get("non_table_element_count", 0)
            if len(examples[(index, status)]) < 2:
                examples[(index, status)].append({
                    "source": relative,
                    "target_offset": slot.get("target_offset"),
                    "vector_count": slot.get("vector_count"),
                    "table_layouts": slot.get("table_layouts", []),
                    "non_table_examples": slot.get("non_table_examples", []),
                })

    return {
        "format": "GFBCol schema-free nested-vector probe",
        "catalog": catalog_path.relative_to(project).as_posix(),
        "source_count": len(sources),
        "source_read_failures": source_failures,
        "root_layouts": dict(root_layouts),
        "slots": {
            str(index): {
                "statuses": dict(slot_statuses[index]),
                "vector_count_histogram": {str(k): v for k, v in sorted(slot_counts[index].items())},
                "table_element_count": elements[index]["table"],
                "unresolved_element_count": elements[index]["unresolved"],
                "child_table_layouts": dict(slot_table_layouts[index]),
                "examples": {
                    status: rows
                    for (slot_index, status), rows in examples.items()
                    if slot_index == index
                },
            }
            for index in sorted(slot_statuses)
        },
        "semantic_status": "UNKNOWN",
        "field_names_assigned": False,
        "element_types_beyond_validated_table_envelopes_assigned": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=PROJECT.parent, help="game root containing 1.0.2/NCA")
    parser.add_argument("--project", type=Path, default=PROJECT)
    args = parser.parse_args()
    print(json.dumps(run(args.root, args.project), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
