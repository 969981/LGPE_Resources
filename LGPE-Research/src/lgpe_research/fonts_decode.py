"""Read-only BFTTF/BFOTF decryption based on the pinned Switch-Toolbox reader."""
from __future__ import annotations

import struct


# Switch-Toolbox FileFormats/Font/BFTTF.cs reads these four-byte tags as a
# little-endian UInt32, then XORs each following big-endian word with the key.
BFOTF_KEYS = {
    0x1A879BD9: 2785117442,
    0x1E1AF836: 1231165446,
    0xC1DE68F3: 2364726489,
}
OPENTYPE_SIGNATURES = {b"OTTO", b"\x00\x01\x00\x00", b"true", b"typ1"}


def inspect_opentype(data: bytes) -> dict:
    """Validate an SFNT/OpenType header and its table directory ranges."""
    if len(data) < 12:
        raise ValueError("OpenType data is shorter than the 12-byte SFNT header")
    signature = data[:4]
    if signature not in OPENTYPE_SIGNATURES:
        raise ValueError(f"decoded payload has no supported OpenType signature: {signature!r}")

    table_count = struct.unpack_from(">H", data, 4)[0]
    if table_count == 0:
        raise ValueError("OpenType table directory is empty")
    directory_end = 12 + 16 * table_count
    if directory_end > len(data):
        raise ValueError("OpenType table directory extends outside the decoded file")

    table_tags: list[str] = []
    seen_tags: set[bytes] = set()
    for index in range(table_count):
        offset = 12 + 16 * index
        raw_tag = data[offset:offset + 4]
        if any(byte < 0x20 or byte > 0x7E for byte in raw_tag):
            raise ValueError(f"OpenType table tag at index {index} is not printable ASCII")
        if raw_tag in seen_tags:
            raise ValueError(f"OpenType table directory has duplicate tag {raw_tag!r}")
        seen_tags.add(raw_tag)
        table_offset, table_length = struct.unpack_from(">II", data, offset + 8)
        if table_offset < directory_end and table_length:
            raise ValueError(f"OpenType table {raw_tag!r} overlaps its directory")
        if table_offset > len(data) or table_length > len(data) - table_offset:
            raise ValueError(f"OpenType table {raw_tag!r} range extends outside the decoded file")
        table_tags.append(raw_tag.decode("ascii"))

    return {
        "signature": signature.decode("ascii", errors="replace"),
        "table_count": table_count,
        "table_tags": table_tags,
        "directory_bytes": directory_end - 12,
        "file_bytes": len(data),
    }


def decode_bfotf(data: bytes) -> tuple[bytes, dict]:
    """Decrypt a BFTTF/BFOTF file and validate the resulting SFNT directory.

    This follows the exact word transform in Switch-Toolbox's BFTTF.Load,
    while adding size and output-structure checks before accepting the bytes.
    """
    if len(data) < 8:
        raise ValueError("BFOTF input is shorter than its 8-byte header")
    magic = int.from_bytes(data[:4], "little")
    key = BFOTF_KEYS.get(magic)
    if key is None:
        raise ValueError(f"unsupported BFOTF magic 0x{magic:08X}")

    encrypted = data[8:]
    if len(encrypted) % 4:
        raise ValueError("BFOTF encrypted payload length is not a multiple of four")
    declared_length = int.from_bytes(data[4:8], "big") ^ key
    if declared_length != len(encrypted):
        raise ValueError(
            f"BFOTF declared output length {declared_length} does not match "
            f"payload length {len(encrypted)}"
        )

    output = b"".join(
        (int.from_bytes(encrypted[offset:offset + 4], "big") ^ key).to_bytes(4, "big")
        for offset in range(0, len(encrypted), 4)
    )
    font = inspect_opentype(output)
    return output, {
        "magic": f"0x{magic:08X}",
        "key": key,
        "declared_output_bytes": declared_length,
        "output_bytes": len(output),
        "font": font,
    }
