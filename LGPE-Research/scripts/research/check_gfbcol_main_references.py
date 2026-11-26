#!/usr/bin/env python3
"""Read-only string/address observations for the exact Pikachu 1.0.2 NSO.

Prints JSON to stdout; never writes decompressed segments or modifies inputs.
These checks do not identify a GFBCol loader, parser, or semantic field names.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path

from lgpe_research.archive_reader import lz4_block, span

MAIN_SHA256 = "1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8"
IMAGE_BASE = 0x7100000000
MAX_BYTES = 64 * 1024 * 1024
NEEDLES = (
    "gfbcol", ".gfbcol", ".col", "_floor", "_wall", "_zone", "_enc",
    "road023", "skyenc", "underground01", "bin/field/model", "collisions",
    "collision", "gfb",
)
EXPECTED_ABSENT = (
    "gfbcol", ".gfbcol", ".col", "_floor", "_zone", "road023", "skyenc", "underground01",
)
# Label, image-relative string address, image-relative first instruction address.
EXACT_LINKS = (
    ("col_wall", 0xF03218, 0x24F480),
    ("col_water", 0xF03221, 0x24F4D8),
    ("col_jump", 0xF0322B, 0x24F528),
    ("col_sky", 0xF03234, 0x24F578),
    ("col_sekichiku", 0xF0323C, 0x24F5C8),
    ("col_safety", 0xF0324A, 0x24F618),
)


def address(offset: int) -> str:
    return f"0x{IMAGE_BASE + offset:x}"


def parse_nso_segments(data: bytes) -> list[dict]:
    """Validate bounded NSO0 segments and each decompressed header hash."""
    if len(data) < 0x100 or len(data) > MAX_BYTES or data[:4] != b"NSO0":
        raise ValueError("invalid NSO0 header or input size")
    flags = struct.unpack_from("<I", data, 0xC)[0]
    segments = []
    total = 0
    for index, name in enumerate(("text", "rodata", "data")):
        file_offset, memory_offset, size = struct.unpack_from("<III", data, 0x10 + 0x10 * index)
        packed_size = struct.unpack_from("<I", data, 0x60 + 4 * index)[0]
        compressed = bool(flags & (1 << index))
        if not flags & (1 << (index + 3)):
            raise ValueError(f"{name}: segment header hash is not enabled")
        total += size
        if file_offset < 0x100 or size == 0 or total > MAX_BYTES:
            raise ValueError(f"{name}: invalid segment offset or decompressed size")
        payload = span(data, file_offset, packed_size if compressed else size)
        decoded = lz4_block(payload, size) if compressed else payload
        digest = hashlib.sha256(decoded).hexdigest()
        expected = data[0xA0 + index * 32:0xC0 + index * 32].hex()
        if digest != expected:
            raise ValueError(f"{name}: segment header SHA-256 mismatch")
        segments.append({
            "name": name, "file_offset": file_offset, "memory_offset": memory_offset,
            "bytes": size, "stored_bytes": len(payload), "compressed": compressed,
            "sha256": digest, "header_sha256_verified": True, "data": decoded,
        })
    return segments


def scan_strings(segments: list[dict], needles=NEEDLES) -> dict:
    """Search every byte position, including odd UTF-16LE starts; cap address samples."""
    result = {}
    for needle in needles:
        encodings = {}
        for encoding in ("ascii", "utf-16le"):
            pattern = needle.encode(encoding)
            count = 0
            samples = []
            for segment in segments:
                lowered = segment["data"].lower()
                offset = lowered.find(pattern)
                while offset >= 0:
                    count += 1
                    if len(samples) < 32:
                        samples.append(address(segment["memory_offset"] + offset))
                    offset = lowered.find(pattern, offset + 1)
            encodings[encoding] = {"count": count, "address_samples": samples}
        result[needle] = encodings
    return result


def decode_link_words(words: tuple[int, ...], instruction_offset: int) -> dict:
    """Decode only adjacent ADRP x1 / ADD x1,x1 / ADD x0,sp,#8 / BL."""
    if len(words) != 4:
        raise ValueError("four AArch64 instruction words required")
    adrp, add, stack_add, branch = words
    if adrp & 0x9F00001F != 0x90000001:
        raise ValueError("expected ADRP x1")
    if add & 0xFFC003FF != 0x91000021:
        raise ValueError("expected unshifted ADD x1,x1 immediate")
    if stack_add != 0x910023E0 or branch & 0xFC000000 != 0x94000000:
        raise ValueError("expected ADD x0,sp,#8 followed by BL")
    immediate = ((adrp >> 29) & 3) | (((adrp >> 5) & 0x7FFFF) << 2)
    if immediate & (1 << 20):
        immediate -= 1 << 21
    page = (instruction_offset & ~0xFFF) + (immediate << 12)
    displacement = branch & 0x3FFFFFF
    if displacement & (1 << 25):
        displacement -= 1 << 26
    return {
        "string_offset": page + ((add >> 10) & 0xFFF),
        "branch_target_offset": instruction_offset + 12 + 4 * displacement,
    }


def inspect_exact_links(segments: list[dict]) -> list[dict]:
    def read_memory(offset: int, size: int) -> bytes:
        for segment in segments:
            relative = offset - segment["memory_offset"]
            if relative >= 0 and relative + size <= segment["bytes"]:
                return span(segment["data"], relative, size)
        raise ValueError(f"address outside NSO segments: {offset:#x}")

    rows = []
    for label, string_offset, instruction_offset in EXACT_LINKS:
        raw = read_memory(instruction_offset, 16)
        words = struct.unpack("<IIII", raw)
        decoded = decode_link_words(words, instruction_offset)
        if decoded != {"string_offset": string_offset, "branch_target_offset": 0xB660}:
            raise ValueError(f"{label}: exact address link mismatch")
        if read_memory(string_offset, len(label) + 1) != label.encode("ascii") + b"\0":
            raise ValueError(f"{label}: exact NUL-terminated token mismatch")
        rows.append({
            "token": label, "string_address": address(string_offset),
            "adrp_address": address(instruction_offset),
            "add_address": address(instruction_offset + 4),
            "bl_address": address(instruction_offset + 12),
            "bl_target_address": address(decoded["branch_target_offset"]),
            "instruction_words": [f"0x{word:08x}" for word in words],
            "raw_instruction_bytes": raw.hex(" "), "status": "ADDRESS_BYTES_MATCH",
        })
    return rows


def inspect_qwords(segments: list[dict]) -> list[dict]:
    """Raw qword observations; includes relocation records, not database xrefs."""
    targets = [(label, offset) for label, offset, _ in EXACT_LINKS] + [
        ("collisions", 0xF2286B),
        ("SetFieldObjectActiveDynamicCollision_", 0xF00A5C),
        ("SetFieldObjectActiveStaticCollision_", 0xF00A82),
    ]
    rows = []
    for label, target in targets:
        for segment in segments:
            for mode, value in (("image_offset", target), ("absolute_address", IMAGE_BASE + target)):
                pattern = struct.pack("<Q", value)
                offset = segment["data"].find(pattern)
                while offset >= 0:
                    location = segment["memory_offset"] + offset
                    rows.append({"token": label, "segment": segment["name"],
                                 "address": address(location), "stored_value": f"0x{value:x}",
                                 "mode": mode, "aligned_8": location % 8 == 0})
                    offset = segment["data"].find(pattern, offset + 1)
    return rows


def inspect_main(path: Path) -> dict:
    if path.stat().st_size > MAX_BYTES:
        raise ValueError("main input exceeds size limit")
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest != MAIN_SHA256:
        raise ValueError(f"exact Pikachu 1.0.2 main SHA-256 mismatch: {digest}")
    segments = parse_nso_segments(data)
    strings = scan_strings(segments)
    absent = all(strings[token][encoding]["count"] == 0
                 for token in EXPECTED_ABSENT for encoding in ("ascii", "utf-16le"))
    links = inspect_exact_links(segments)
    return {
        "schema": "lgpe-gfbcol-main-address-observations-v1",
        "source": {"path": str(path), "bytes": len(data), "sha256": digest},
        "image_base": f"0x{IMAGE_BASE:x}",
        "scope": "Three decompressed NSO segments; per-segment case-insensitive ASCII and UTF-16LE searches at every byte position; no search across segment boundaries or synthesized runtime strings.",
        "semantics": "UNKNOWN; label/data/code address observations do not establish a GFBCol loader, parser, field names, or runtime execution.",
        "segments": [{key: value for key, value in s.items() if key != "data"} for s in segments],
        "total_decompressed_bytes": sum(s["bytes"] for s in segments),
        "strings": strings, "expected_absent_tokens": list(EXPECTED_ABSENT),
        "expected_absence_verified": absent, "exact_instruction_links": links,
        "raw_qword_observations": inspect_qwords(segments),
        "checks_passed": absent and len(links) == 6,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--main", type=Path, required=True, help="Original Pikachu 1.0.2 ExeFS 0/main")
    args = parser.parse_args()
    try:
        report = inspect_main(args.main)
    except (OSError, ValueError, struct.error) as exc:
        parser.exit(2, f"error: {exc}\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
