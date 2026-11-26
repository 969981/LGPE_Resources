# SPDX-License-Identifier: GPL-3.0-only
"""Bounded GFPAK v0x1000 / named SARC reader; see T04/T05 provenance.

GFPAK has hashed identifiers rather than stored plaintext paths. Unknown names
stay hash identifiers; never infer an extension from bytes and rename a member.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import struct
import zlib
from pathlib import Path, PurePosixPath

MAX_OUTPUT = 1 << 30
MAX_MEMBERS = 100000


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def span(data: bytes, start: int, size: int) -> bytes:
    if start < 0 or size < 0 or start + size > len(data):
        raise ValueError("archive range outside input")
    return data[start:start + size]


def unpack(fmt: str, data: bytes, start: int):
    return struct.unpack(fmt, span(data, start, struct.calcsize(fmt)))


def fnv(name: str) -> int:
    value = 0xcbf29ce484222645  # Game Freak variant; differs from standard FNV basis
    for b in name.encode("utf-8"):
        value = ((value ^ b) * 0x100000001b3) & 0xffffffffffffffff
    return value


def safe_path(name: str) -> str:
    if "\\" in name or ":" in name or "\x00" in name:
        raise ValueError("unsafe member name")
    path = PurePosixPath(name)
    if path.is_absolute() or not name or any(p in ("", ".", "..") for p in name.split("/")):
        raise ValueError("unsafe member path")
    # Windows has special device names and aliases even within ordinary paths.
    for part in path.parts:
        if part.endswith((" ", ".")) or re.fullmatch(r"(?i)(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?", part):
            raise ValueError("unsafe Windows member path")
    return path.as_posix()


def lz4_block(data: bytes, expected: int) -> bytes:
    """Raw LZ4 block with bounded output, including overlapping match copies."""
    if not 0 <= expected <= MAX_OUTPUT:
        raise ValueError("LZ4 output limit")
    out = bytearray()
    pos = 0
    def length(value):
        nonlocal pos
        if value == 15:
            while True:
                extension = span(data, pos, 1)[0]
                pos += 1
                value += extension
                if value > expected:
                    raise ValueError("LZ4 length exceeds output")
                if extension != 255:
                    break
        return value
    while pos < len(data):
        token = data[pos]
        pos += 1
        literal = length(token >> 4)
        if len(out) + literal > expected:
            raise ValueError("LZ4 literal limit")
        out.extend(span(data, pos, literal))
        pos += literal
        if pos == len(data):
            break
        offset, = unpack("<H", data, pos)
        pos += 2
        match = length(token & 15) + 4
        if offset == 0 or offset > len(out) or len(out) + match > expected:
            raise ValueError("invalid LZ4 match")
        for _ in range(match):
            out.append(out[-offset])
    if len(out) != expected:
        raise ValueError("LZ4 size mismatch")
    return bytes(out)


def decode_payload(payload: bytes, kind: int, size: int) -> bytes:
    if size > MAX_OUTPUT:
        raise ValueError("member output limit")
    if kind == 0:
        result = payload
    elif kind == 1:
        decoder = zlib.decompressobj()
        result = decoder.decompress(payload, size + 1)
        if not decoder.eof or decoder.unused_data:
            raise ValueError("invalid zlib stream")
    elif kind == 2:
        result = lz4_block(payload, size)
    else:
        raise NotImplementedError(f"UNSUPPORTED compression {kind}")
    if len(result) != size:
        raise ValueError("decompressed size mismatch")
    return result


def hash_names(corpus: Path | None, stem: str) -> dict[int, str]:
    names = {}
    if corpus is None:
        return names
    for line in corpus.read_text(encoding="utf-8-sig").splitlines():
        line = line.rstrip()
        variants = [line]
        if "XXXX" in line:
            number = stem[2:6] if stem.startswith("pm") else "0000"
            variants.append(line.replace("XXXX", number).replace("YY", "00").replace("ZZ", "00"))
        for name in variants:
            for candidate in [name, *name.split("/")]:
                if candidate:
                    names.setdefault(fnv(candidate), candidate)
    return names


def read_gfpak(data: bytes, names: dict[int, str] | None = None):
    names = names or {}
    magic, version, relocated, count, folders = unpack("<8sIIII", data, 0)
    if magic != b"GFLXPACK" or version != 0x1000 or relocated != 0:
        raise NotImplementedError("UNSUPPORTED GFPAK header/version/relocation")
    if count > MAX_MEMBERS or folders > MAX_MEMBERS:
        raise ValueError("GFPAK member limit")
    table, hashes = unpack("<QQ", data, 24)
    span(data, table, count * 24)
    span(data, hashes, count * 8)
    identities = {}
    for folder in range(folders):
        pointer, = unpack("<Q", data, 40 + folder * 8)
        folder_hash, file_count, _ = unpack("<QII", data, pointer)
        if file_count > count:
            raise ValueError("invalid folder count")
        for item in range(file_count):
            file_hash, index, _ = unpack("<QII", data, pointer + 16 + item * 16)
            if index >= count or index in identities:
                raise ValueError("duplicate or invalid GFPAK index")
            identities[index] = (folder_hash, file_hash)
    if len(identities) != count:
        raise ValueError("incomplete GFPAK folder mapping")
    total = 0
    for index in range(count):
        level, kind, size, packed, padding, offset = unpack("<HHIIIQ", data, table + index * 24)
        total += size
        if total > MAX_OUTPUT:
            raise ValueError("archive output limit")
        payload = span(data, offset, packed)
        decoded = decode_payload(payload, kind, size)
        full_hash, = unpack("<Q", data, hashes + index * 8)
        folder_hash, file_hash = identities[index]
        folder_name = names.get(folder_hash)
        file_name = names.get(file_hash)
        # Embedded binary names are candidates only after exact filename hash match.
        if file_name is None and decoded[:4] in (b"BNTX", b"BNSH"):
            name_offset, = unpack("<I", decoded, 16)
            if name_offset < len(decoded):
                end = decoded.find(b"\x00", name_offset)
                if end >= 0:
                    candidate = decoded[name_offset:end].decode("utf-8", errors="replace")
                    for suffix in ("", ".bntx", ".bnsh", ".bnsh_vsh", ".bnsh_fsh"):
                        if fnv(candidate + suffix) == file_hash:
                            file_name = candidate + suffix
        folder_id = folder_name.rstrip("/") if folder_name else f"{folder_hash:016X}"
        file_id = file_name if file_name else f"{file_hash:016X}"
        path = safe_path(folder_id + "/" + file_id)
        if folder_name and file_name and fnv(path) != full_hash:
            raise ValueError("GFPAK resolved full path hash mismatch")
        yield {"index": index, "internal_path": path, "folder_hash": f"{folder_hash:016X}",
               "filename_hash": f"{file_hash:016X}", "full_path_hash": f"{full_hash:016X}",
               "name_resolution": "hash_verified" if folder_name and file_name else "partial_or_hash_only",
               "compression": kind, "offset": offset, "packed_size": packed,
               "packed_sha256": sha(payload), "size": size, "sha256": sha(decoded)}, decoded


def read_sarc(data: bytes):
    if data[:4] != b"SARC":
        raise NotImplementedError("UNSUPPORTED ARC signature")
    endian = {b"\xff\xfe": "<", b"\xfe\xff": ">"}.get(span(data, 6, 2))
    if endian is None:
        raise ValueError("invalid SARC BOM")
    header, bom, size, payload_start, version, reserved = unpack(endian + "HHIIHH", data, 4)
    if header != 20 or size != len(data) or version != 0x100:
        raise ValueError("invalid SARC header")
    if span(data, header, 4) != b"SFAT":
        raise ValueError("missing SFAT")
    fat_size, count, multiplier = unpack(endian + "HHI", data, header + 4)
    if fat_size != 12 or count > MAX_MEMBERS:
        raise ValueError("invalid SFAT header")
    node_start = header + fat_size
    name_table = node_start + count * 16
    if span(data, name_table, 4) != b"SFNT":
        raise ValueError("missing SFNT")
    name_size, _ = unpack(endian + "HH", data, name_table + 4)
    if name_size != 8:
        raise ValueError("invalid SFNT header")
    names_start = name_table + name_size
    if not names_start <= payload_start <= len(data):
        raise ValueError("invalid data offset")
    total = 0
    for index in range(count):
        name_hash, attributes, start, end = unpack(endian + "IIII", data, node_start + index * 16)
        if attributes >> 24 != 1:
            raise NotImplementedError("UNSUPPORTED SARC unnamed member")
        offset = names_start + (attributes & 0xffffff) * 4
        if not names_start <= offset < payload_start:
            raise ValueError("invalid name offset")
        terminator = data.find(b"\x00", offset, payload_start)
        if terminator < 0:
            raise ValueError("unterminated SARC name")
        name = safe_path(data[offset:terminator].decode("utf-8"))
        calculated = 0
        for b in name.encode("utf-8"):
            calculated = (calculated * multiplier + b) & 0xffffffff
        if calculated != name_hash or end < start:
            raise ValueError("SARC filename hash/range mismatch")
        payload = span(data, payload_start + start, end - start)
        total += len(payload)
        if total > MAX_OUTPUT:
            raise ValueError("archive output limit")
        yield {"index": index, "internal_path": name, "filename_hash": f"{name_hash:08X}",
               "name_resolution": "stored", "offset": payload_start + start,
               "size": len(payload), "sha256": sha(payload)}, payload


def extract(source: Path, source_root: Path, output_root: Path, corpus: Path | None = None, execute: bool = False):
    relative = source.resolve().relative_to(source_root.resolve())
    target = (output_root / (relative.as_posix() + ".contents")).resolve()
    if target.resolve().is_relative_to(source_root.resolve()):
        raise ValueError("output cannot be inside immutable source")
    data = source.read_bytes()
    members = list(read_gfpak(data, hash_names(corpus, source.stem)) if data.startswith(b"GFLXPACK") else read_sarc(data))
    seen = set()
    for record, payload in members:
        key = record["internal_path"].casefold()
        if key in seen:
            raise ValueError("duplicate member output path")
        seen.add(key)
        path = target / record["internal_path"]
        if not path.resolve().is_relative_to(target.resolve()):
            raise ValueError("member output escapes container via symlink")
        if path.exists() and sha(path.read_bytes()) != record["sha256"]:
            raise FileExistsError(f"refusing changed output {path}")
    if execute:
        for record, payload in members:
            path = target / record["internal_path"]
            path.parent.mkdir(parents=True, exist_ok=True)
            if not path.exists():
                with path.open("xb") as stream:
                    stream.write(payload)
            if sha(path.read_bytes()) != record["sha256"]:
                raise ValueError("written output hash mismatch")
    return {"source": relative.as_posix(), "source_sha256": sha(data), "source_size": len(data),
            "method": "lgpe_research.archive_reader/v1",
            "source_references": {"pkNX": "d191cd0e5c05f2af81d9a41c1f1d82e6621b351a", "Switch-Toolbox": "3fcb87f1fea25ad56db139b0d9577db591f54118"},
            "hash_corpus_sha256": sha(corpus.read_bytes()) if corpus else None,
            "method": "lgpe_research.archive_reader/v1",
            "source_references": {"pkNX": "d191cd0e5c05f2af81d9a41c1f1d82e6621b351a", "Switch-Toolbox": "3fcb87f1fea25ad56db139b0d9577db591f54118"},
            "hash_corpus_sha256": sha(corpus.read_bytes()) if corpus else None,
            "header_hex": data[:64].hex(), "status": "DECODED" if execute else "DRY_RUN",
            "output": str(target), "member_count": len(members),
            "output_bytes": sum(record["size"] for record, _ in members),
            "members": [record for record, _ in members]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sources", nargs="+", type=Path)
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--hash-corpus", type=Path)
    parser.add_argument("--results", required=True, type=Path)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    args.results.parent.mkdir(parents=True, exist_ok=True)
    failures = 0
    with args.results.open("w", encoding="utf-8") as log:
        for source in args.sources:
            try:
                result = extract(source, args.source_root, args.output_root, args.hash_corpus, args.execute)
            except Exception as error:
                failures += 1
                result = {"source": str(source), "status": "UNSUPPORTED" if isinstance(error, NotImplementedError) else "FAILED", "error": f"{type(error).__name__}: {error}"}
            log.write(json.dumps(result, ensure_ascii=False) + "\n")
            print(json.dumps({k: v for k, v in result.items() if k != "members"}, ensure_ascii=False))
    return bool(failures)


if __name__ == "__main__":
    raise SystemExit(main())
