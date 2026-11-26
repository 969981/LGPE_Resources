"""Bounded Nintendo Switch FFNT/BFFNT structural reader.

Section field order and offset bases follow the pinned Switch-Toolbox BXFNT
reader at tools/src/Switch-Toolbox/File_Format_Library/FileFormats/Font/BXFNT.
For the common header, its adjacent FFNT.Write method writes a 32-bit file
size and 16-bit block count; FFNT.Read currently reads the file size as 16-bit,
which shifts the latter fields. This adapter follows the writer layout and
checks the 32-bit size against the actual local file. It intentionally accepts
only the little-endian NX FFNT variant observed in the local LGPE sample.
"""
from __future__ import annotations

import hashlib
import struct


NX_FFNT_VERSION = 0x04010000
HEADER_SIZE = 20
FONT_TYPES = {1: "Glyph", 2: "Texture", 3: "PackedTexture"}
CHARACTER_ENCODINGS = {0: "UTF8", 1: "Unicode", 2: "ShiftJIS", 3: "CP1252"}
CMAP_METHODS = {0: "Direct", 1: "Table", 2: "Scan"}


def _unpack(data: bytes, offset: int, fmt: str, label: str):
    size = struct.calcsize(fmt)
    if offset < 0 or size > len(data) - offset:
        raise ValueError(f"{label} at 0x{offset:X} extends outside the BFFNT")
    return struct.unpack_from(fmt, data, offset)


def _section(data: bytes, offset: int, expected: bytes, known: dict[int, dict]) -> dict:
    if offset not in known:
        raise ValueError(f"section pointer targets non-section offset 0x{offset:X}")
    block = known[offset]
    if block["signature"].encode("ascii") != expected:
        raise ValueError(
            f"section pointer at 0x{offset:X} names {block['signature']}, "
            f"expected {expected.decode('ascii')}"
        )
    return block


def _linked_sections(data: bytes, first: dict, known: dict[int, dict], signature: bytes) -> list[dict]:
    result = []
    visited = set()
    current = first
    while current is not None:
        offset = current["offset"]
        if offset in visited:
            raise ValueError(f"cyclic {signature.decode('ascii')} linked section at 0x{offset:X}")
        visited.add(offset)
        start = current["offset"]
        size = current["size"]
        if size < 16:
            raise ValueError(f"{signature.decode('ascii')} at 0x{start:X} is shorter than 16 bytes")
        if signature == b"CWDH":
            first_index, last_index, next_reference = _unpack(
                data, start + 8, "<HHI", "CWDH header",
            )
            if last_index < first_index:
                raise ValueError(f"CWDH index range is reversed at 0x{start:X}")
            count = last_index - first_index + 1
            payload_size = count * 3
            if payload_size > size - 16:
                raise ValueError(f"CWDH entries exceed section at 0x{start:X}")
            entries = []
            for index in range(count):
                left, glyph_width, char_width = _unpack(
                    data, start + 16 + index * 3, "<bBB", "CWDH entry",
                )
                entries.append({
                    "glyph_index": first_index + index,
                    "left": left,
                    "glyph_width": glyph_width,
                    "char_width": char_width,
                })
            result.append({
                "section_index": current["index"],
                "offset": start,
                "size": size,
                "start_index": first_index,
                "end_index": last_index,
                "entry_count": count,
                "entries": entries,
                "next_reference": next_reference,
            })
            current = (
                _section(data, next_reference - 8, signature, known)
                if next_reference else None
            )
            continue

        begin, end, method_code, padding, next_reference = _unpack(
            data, start + 8, "<IIHHI", "CMAP header",
        )
        method = CMAP_METHODS.get(method_code)
        if method is None:
            raise NotImplementedError(f"unsupported CMAP method {method_code} at 0x{start:X}")
        record = {
            "section_index": current["index"],
            "offset": start,
            "size": size,
            "code_begin": begin,
            "code_end": end,
            "mapping_method": method,
            "mapping_method_code": method_code,
            "padding": padding,
            "next_reference": next_reference,
        }
        payload = start + 24
        if method_code == 0:
            if end < begin or size < 26:
                raise ValueError(f"CMAP direct range or payload is invalid at 0x{start:X}")
            (glyph_offset,) = _unpack(data, payload, "<H", "CMAP direct offset")
            record["mapping"] = {
                "glyph_offset": glyph_offset,
                "index_formula": "glyph_index = codepoint - code_begin + glyph_offset",
            }
        elif method_code == 1:
            if end < begin:
                raise ValueError(f"CMAP table range is reversed at 0x{start:X}")
            count = end - begin + 1
            if count * 2 > size - 24:
                raise ValueError(f"CMAP table exceeds section at 0x{start:X}")
            values = [
                _unpack(data, payload + index * 2, "<h", "CMAP table entry")[0]
                for index in range(count)
            ]
            record["mapping"] = {"glyph_indexes": values}
        else:
            (count,) = _unpack(data, payload, "<H", "CMAP scan count")
            if _unpack(data, payload + 2, "<H", "CMAP scan padding")[0] != 0:
                raise ValueError(f"NX CMAP scan padding is nonzero at 0x{start:X}")
            if count * 8 > size - 28:
                raise ValueError(f"CMAP scan entries exceed section at 0x{start:X}")
            mappings = []
            for index in range(count):
                code, glyph_index, entry_padding = _unpack(
                    data, payload + 4 + index * 8, "<IhH", "CMAP scan entry",
                )
                if entry_padding != 0:
                    raise ValueError(f"NX CMAP scan entry padding is nonzero at 0x{start:X}")
                mappings.append({"codepoint": code, "glyph_index": glyph_index})
            record["mapping"] = {"entry_count": count, "entries": mappings}
        result.append(record)
        current = _section(data, next_reference - 8, signature, known) if next_reference else None
    return result


def parse_bffnt(data: bytes) -> tuple[dict, list[bytes]]:
    """Parse the observed NX FFNT header, font sections, and embedded BNTX sheets."""
    if len(data) < HEADER_SIZE:
        raise ValueError("BFFNT is shorter than the 20-byte FFNT header")
    signature = data[:4]
    if signature != b"FFNT":
        raise NotImplementedError(f"unsupported font signature {signature!r}; NX FFNT required")
    if data[4:6] != b"\xFF\xFE":
        raise NotImplementedError(f"unsupported BFFNT byte order mark {data[4:6].hex()}")
    # FFNT.Write uses the 32-bit size and 16-bit block-count fields here.
    header_size, version, declared_size, block_count, padding = _unpack(
        data, 6, "<HIIHH", "FFNT header",
    )
    if header_size != HEADER_SIZE:
        raise NotImplementedError(f"unsupported NX FFNT header size {header_size}")
    if version != NX_FFNT_VERSION:
        raise NotImplementedError(f"unsupported NX FFNT version 0x{version:08X}")
    if declared_size != len(data):
        raise ValueError(f"FFNT declared size {declared_size} differs from input size {len(data)}")
    if block_count < 3:
        raise ValueError(f"FFNT block count {block_count} is too small")

    blocks = []
    offset = header_size
    for index in range(block_count):
        if offset > len(data) - 8:
            raise ValueError(f"FFNT block {index} header is truncated at 0x{offset:X}")
        raw_signature = data[offset:offset + 4]
        try:
            name = raw_signature.decode("ascii")
        except UnicodeDecodeError as exc:
            raise NotImplementedError(f"non-ASCII FFNT block signature at 0x{offset:X}") from exc
        (size,) = _unpack(data, offset + 4, "<I", f"{name} section size")
        if size < 8 or size > len(data) - offset:
            raise ValueError(f"{name} section size {size} is invalid at 0x{offset:X}")
        blocks.append({
            "index": index,
            "signature": name,
            "offset": offset,
            "size": size,
            "end_offset": offset + size,
            "sha256": hashlib.sha256(data[offset:offset + size]).hexdigest(),
        })
        offset += size
    if offset != len(data):
        raise ValueError(f"FFNT sections end at 0x{offset:X}, input ends at 0x{len(data):X}")
    known = {block["offset"]: block for block in blocks}
    signatures = [block["signature"] for block in blocks]
    if signatures[0] != "FINF" or "TGLP" not in signatures or "CWDH" not in signatures or "CMAP" not in signatures:
        raise NotImplementedError(f"unsupported NX FFNT section sequence {signatures!r}")
    for block in blocks:
        if block["signature"] not in {"FINF", "TGLP", "CWDH", "CMAP", "KRNG", "GLGR", "HTGL"}:
            raise NotImplementedError(f"unsupported NX FFNT section {block['signature']}")
        if block["signature"] in {"KRNG", "GLGR", "HTGL"}:
            raise NotImplementedError(f"NX FFNT {block['signature']} section parsing is not implemented")

    finf = blocks[0]
    if finf["size"] < 32:
        raise ValueError("NX FINF section is shorter than 32 bytes")
    (font_type, height, width, ascent, line_feed, alter_char_index,
     default_left, default_glyph, default_char, encoding,
     tglp_reference, cwdh_reference, cmap_reference) = _unpack(
        data, finf["offset"] + 8, "<BBBBHHBBBBIII", "NX FINF payload",
    )
    if font_type not in FONT_TYPES:
        raise NotImplementedError(f"unsupported NX FINF font type {font_type}")
    if encoding not in CHARACTER_ENCODINGS:
        raise NotImplementedError(f"unsupported NX FINF character encoding {encoding}")
    tglp = _section(data, tglp_reference - 8, b"TGLP", known)
    cwdh_first = _section(data, cwdh_reference - 8, b"CWDH", known)
    cmap_first = _section(data, cmap_reference - 8, b"CMAP", known)

    if tglp["size"] < 32:
        raise ValueError("NX TGLP section is shorter than 32 bytes")
    (cell_width, cell_height, sheet_count, max_char_width, sheet_size,
     baseline_position, format_code, row_count, column_count,
     sheet_width, sheet_height, sheet_data_offset) = _unpack(
        data, tglp["offset"] + 8, "<BBBBIHHHHHHI", "NX TGLP payload",
    )
    if not sheet_count or not sheet_size or not sheet_width or not sheet_height:
        raise ValueError("NX TGLP has an empty sheet count, sheet size, or sheet dimension")
    sheet_payload_size = sheet_count * sheet_size
    if sheet_data_offset < tglp["offset"] + 32 or sheet_data_offset > tglp["end_offset"]:
        raise ValueError("NX TGLP sheet-data offset is outside its section")
    if sheet_payload_size > tglp["end_offset"] - sheet_data_offset:
        raise ValueError("NX TGLP sheet data exceeds its section")

    sheet_data = []
    sheet_records = []
    for index in range(sheet_count):
        start = sheet_data_offset + index * sheet_size
        payload = data[start:start + sheet_size]
        if payload[:4] != b"BNTX":
            raise NotImplementedError(
                f"NX TGLP sheet {index} does not contain the BNTX signature"
            )
        sheet_data.append(payload)
        sheet_records.append({
            "index": index,
            "internal_path": f"Sheet_{index}.bntx",
            "offset": start,
            "size": len(payload),
            "signature": "BNTX",
            "sha256": hashlib.sha256(payload).hexdigest(),
        })

    widths = _linked_sections(data, cwdh_first, known, b"CWDH")
    maps = _linked_sections(data, cmap_first, known, b"CMAP")
    report = {
        "format": "NintendoWare NX FFNT/BFFNT",
        "platform": "NX",
        "header": {
            "signature": "FFNT",
            "byte_order": "little",
            "bom_hex": data[4:6].hex(),
            "header_size": header_size,
            "version": version,
            "version_hex": f"0x{version:08X}",
            "declared_file_size": declared_size,
            "block_count": block_count,
            "padding": padding,
        },
        "font_info": {
            "section_index": finf["index"],
            "offset": finf["offset"],
            "size": finf["size"],
            "font_type": FONT_TYPES[font_type],
            "font_type_code": font_type,
            "height": height,
            "width": width,
            "ascent": ascent,
            "line_feed": line_feed,
            "alternate_character_index": alter_char_index,
            "default_left_width": default_left,
            "default_glyph_width": default_glyph,
            "default_character_width": default_char,
            "character_encoding": CHARACTER_ENCODINGS[encoding],
            "character_encoding_code": encoding,
            "tglp_reference": tglp_reference,
            "cwdh_reference": cwdh_reference,
            "cmap_reference": cmap_reference,
        },
        "texture_glyph": {
            "section_index": tglp["index"],
            "offset": tglp["offset"],
            "size": tglp["size"],
            "cell_width": cell_width,
            "cell_height": cell_height,
            "sheet_count": sheet_count,
            "max_character_width": max_char_width,
            "sheet_size": sheet_size,
            "baseline_position": baseline_position,
            "format_code": format_code,
            "row_count": row_count,
            "column_count": column_count,
            "sheet_width": sheet_width,
            "sheet_height": sheet_height,
            "sheet_data_offset": sheet_data_offset,
            "sheets": sheet_records,
        },
        "character_width_sections": widths,
        "character_map_sections": maps,
        "sections": blocks,
    }
    return report, sheet_data
