#!/usr/bin/env python3
"""Build an auditable RTTI inventory with the pinned public PokeLDN parser.

This reads an already extracted LGPE 1.0.2 ExeFS main and the matching
decompressed NSO image. It emits offsets and pointer relationships only; it
does not copy game bytes into the report.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import subprocess
import sys
from collections import defaultdict
from pathlib import Path


EXPECTED_MAIN_SHA256 = "1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8"
EXPECTED_POKELDN_COMMIT = "0afe6f61f25464767e55b909eef6b260a372bb34"
EXPECTED_SEGMENTS = {
    "text": (0x00000000, 0xD32BA8),
    "rodata": (0x00D33000, 0x7F317C),
    "data": (0x01527000, 0x0E5030),
}
EXPECTED_INVENTORIES = {
    "nn::pia": (269, 2112),
    "nn::nex": (269, 1388),
}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_pokeldn(source_root: Path):
    tool_root = source_root / "tools" / "switch"
    parser_path = tool_root / "rtti_names.py"
    if not parser_path.is_file():
        raise FileNotFoundError(f"PokeLDN parser missing: {parser_path}")
    sys.path.insert(0, str(source_root))
    spec = importlib.util.spec_from_file_location("pokeldn_rtti_names", parser_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load parser: {parser_path}")
    parser = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(parser)
    from pokeldn.switch import nso

    return parser, nso


def main() -> int:
    project_root = Path(__file__).resolve().parents[2]
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("main", type=Path, help="read-only path to the extracted 0/main NSO")
    ap.add_argument("image", type=Path, help="expanded output from PokeLDN tools/switch/nso_read.py")
    ap.add_argument("--source-root", type=Path, default=project_root / "tools" / "src" / "pokeldn")
    ap.add_argument("--prefix", choices=EXPECTED_INVENTORIES, default="nn::pia")
    ap.add_argument("--jsonl", type=Path, required=True, help="output class inventory JSONL")
    ap.add_argument("--ghidra-tsv", type=Path, required=True, help="output pointer-check input for Ghidra")
    args = ap.parse_args()

    source_root = args.source_root.resolve()
    commit = subprocess.run(
        ["git", "-C", str(source_root), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if commit != EXPECTED_POKELDN_COMMIT:
        raise SystemExit(f"PokeLDN commit mismatch: expected {EXPECTED_POKELDN_COMMIT}, got {commit}")
    license_path = source_root / "LICENSE"
    if not license_path.is_file() or "GNU AFFERO GENERAL PUBLIC LICENSE" not in license_path.read_text(
        encoding="utf-8", errors="replace"
    ):
        raise SystemExit("PokeLDN root LICENSE does not identify GNU AGPL")

    main_bytes = args.main.read_bytes()
    main_sha256 = sha256(main_bytes)
    if main_sha256 != EXPECTED_MAIN_SHA256:
        raise SystemExit(f"main SHA-256 mismatch: expected {EXPECTED_MAIN_SHA256}, got {main_sha256}")

    parser, nso = load_pokeldn(source_root)
    segments = nso.segments(main_bytes)
    actual_segments = {name: (offset, len(data)) for name, (offset, data) in segments.items()}
    if actual_segments != EXPECTED_SEGMENTS:
        raise SystemExit(f"NSO segment mismatch: {actual_segments!r}")
    image = args.image.read_bytes()
    expected_size = max(offset + len(data) for offset, data in segments.values())
    expected_image = bytearray(expected_size)
    for offset, data in segments.values():
        expected_image[offset : offset + len(data)] = data
    if image != expected_image:
        raise SystemExit("expanded image differs from the decompressed segments of the hashed local main")

    text_end = EXPECTED_SEGMENTS["text"][1]
    labels, _classes, typeinfos = parser.build(image, text_end)
    selected_vfuncs = {
        offset: label for offset, label in labels.items() if label.startswith(args.prefix + "::")
    }
    selected_classes = sorted({label.rsplit("::vfunc", 1)[0] for label in selected_vfuncs.values()})
    if (len(selected_classes), len(selected_vfuncs)) != EXPECTED_INVENTORIES[args.prefix]:
        raise SystemExit(
            f"unexpected {args.prefix} inventory size: "
            f"classes={len(selected_classes)} vfuncs={len(selected_vfuncs)}"
        )

    relocations = nso.relatives(image)
    by_slot = dict(relocations)
    targets: dict[int, list[int]] = defaultdict(list)
    for slot, target in relocations:
        targets[target].append(slot)

    args.jsonl.parent.mkdir(parents=True, exist_ok=True)
    args.ghidra_tsv.parent.mkdir(parents=True, exist_ok=True)
    json_rows = []
    tsv_rows = []
    vtable_count = 0
    method_slot_count = 0
    for typeinfo_offset, class_name in sorted(typeinfos.items(), key=lambda item: (item[1], item[0])):
        if class_name not in selected_classes:
            continue
        name_offset = by_slot.get(typeinfo_offset + 8)
        if name_offset is None:
            raise SystemExit(f"missing type-name relocation for {class_name} at 0x{typeinfo_offset:x}")
        mangled_name = image[name_offset : image.find(b"\0", name_offset)].decode("ascii", "replace")
        vtables = []
        for vtable_offset in sorted(targets.get(typeinfo_offset, [])):
            methods = []
            slot = vtable_offset + 8
            while slot in by_slot and 0 < by_slot[slot] < text_end:
                method_offset = by_slot[slot]
                methods.append(
                    {
                        "vtable_index": len(methods),
                        "main_offset": f"0x{method_offset:x}",
                        "rtti_label": labels.get(method_offset),
                    }
                )
                slot += 8
            vtables.append({"offset": f"0x{vtable_offset:x}", "methods": methods})
            method_offsets = ",".join(method["main_offset"] for method in methods)
            tsv_rows.append(
                "\t".join(
                    (
                        "VTABLE",
                        class_name,
                        f"0x{vtable_offset:x}",
                        f"0x{typeinfo_offset:x}",
                        method_offsets,
                    )
                )
            )
            vtable_count += 1
            method_slot_count += len(methods)
        row = {
            "schema": "lgpe.pokeldn-rtti-class/v1",
            "game": "Pokemon Let's Go Pikachu 1.0.2",
            "namespace_prefix": args.prefix,
            "address_basis": "decompressed NSO memory offsets; add Ghidra image base 0x7100000000",
            "source_main_sha256": main_sha256,
            "expanded_image_sha256": sha256(image),
            "parser": {
                "name": "PokeLDN tools/switch/rtti_names.py",
                "commit": commit,
                "license": "AGPL-3.0",
            },
            "class_name": class_name,
            "type_info_offset": f"0x{typeinfo_offset:x}",
            "mangled_name_offset": f"0x{name_offset:x}",
            "mangled_name": mangled_name,
            "vtables": vtables,
        }
        json_rows.append(json.dumps(row, ensure_ascii=False, sort_keys=True))
        tsv_rows.append(
            "\t".join(
                (
                    "CLASS",
                    class_name,
                    f"0x{typeinfo_offset:x}",
                    f"0x{name_offset:x}",
                    mangled_name,
                )
            )
        )

    args.jsonl.write_text("\n".join(json_rows) + "\n", encoding="utf-8", newline="\n")
    args.ghidra_tsv.write_text("\n".join(tsv_rows) + "\n", encoding="utf-8", newline="\n")
    print(
        f"main_sha256={main_sha256} image_sha256={sha256(image)} "
        f"pokeldn={commit} prefix={args.prefix} classes={len(selected_classes)} "
        f"named_vfuncs={len(selected_vfuncs)} "
        f"typeinfo_rows={len(json_rows)} vtables={vtable_count} method_slots={method_slot_count}"
    )
    print(f"jsonl={args.jsonl} ghidra_tsv={args.ghidra_tsv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
