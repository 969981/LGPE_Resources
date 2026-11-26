#!/usr/bin/env python3
"""Record opaque candidate rows and cross-reference their numeric indexes."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from lgpe_research.gamedata_decode import message
from lgpe_research.itemhash_crossref import (
    assert_message_document_matches,
    inspect_candidate_table,
)


NCA_DIRECTORY = "2b7730a9e56498bbafac2002d4908c6b_NCA"
POKEDAT_COMMIT = "bd423b2cad9aa852fddb796bbba3c5e7b381289b"
TABLE_RELATIVE = Path("bin/pokelib/item/item_hash_to_index.dat")
MESSAGE_RELATIVE = Path("bin/message/English/common/itemname.dat")
LABELS_RELATIVE = Path("bin/message/English/common/itemname.tbl")
MESSAGE_JSON_RELATIVE = Path(
    "decoded/1.0.2/romfs/bin/message/English/common/itemname.json"
)


def receipt(path: Path, relative_to: Path) -> dict:
    data = path.read_bytes()
    return {
        "path": path.relative_to(relative_to).as_posix(),
        "size": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def main() -> int:
    project_root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--game-root",
        type=Path,
        default=project_root.parent / "1.0.2" / NCA_DIRECTORY / "1",
        help="extracted RomFS root (defaults to the sibling local 1.0.2 dump)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=project_root / "work" / "item-hash-index-crossref.json",
        help="ignored research report path",
    )
    args = parser.parse_args()

    game_root = args.game_root.resolve()
    source_table = game_root / TABLE_RELATIVE
    source_message = game_root / MESSAGE_RELATIVE
    source_labels = game_root / LABELS_RELATIVE
    decoded_message = project_root / MESSAGE_JSON_RELATIVE
    pokedat_path = project_root / "tools" / "src" / "pokedat"
    for path in (source_table, source_message, source_labels, decoded_message):
        if not path.is_file():
            parser.error(f"required local research input is missing: {path}")
    if not (pokedat_path / "text_file.py").is_file():
        parser.error(f"pinned pokedat source is missing: {pokedat_path}")
    try:
        actual_pokedat_commit = subprocess.run(
            ["git", "-C", str(pokedat_path), "rev-parse", "HEAD"],
            check=True, capture_output=True, text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        parser.error(f"cannot identify local pokedat checkout: {exc}")
    if actual_pokedat_commit != POKEDAT_COMMIT:
        parser.error(
            f"pokedat commit mismatch: expected {POKEDAT_COMMIT}, got {actual_pokedat_commit}"
        )

    table_data = source_table.read_bytes()
    message_doc = json.loads(decoded_message.read_text(encoding="utf-8"))
    if message_doc.get("format") != "LGPE-message" or not isinstance(message_doc.get("lines"), list):
        parser.error(f"decoded message input has an unexpected structure: {decoded_message}")
    redecoded_message = message(
        source_message.read_bytes(), source_labels.read_bytes(), pokedat_path,
    )
    try:
        assert_message_document_matches(message_doc, redecoded_message)
    except ValueError as exc:
        parser.error(str(exc))

    report = inspect_candidate_table(table_data, message_doc["lines"])
    report.update({
        "schema": "lgpe-item-hash-index-cross-reference-v2",
        "game_version": "Pokemon Let's Go Pikachu 1.0.2",
        "source_table": receipt(source_table, game_root),
        "message_sources": [
            receipt(source_message, game_root),
            receipt(source_labels, game_root),
        ],
        "decoded_message_reference": receipt(decoded_message, project_root),
        "message_decode_validation": {
            "status": "MATCH",
            "pokedat_commit": actual_pokedat_commit,
        },
        "loader_layout_provenance": {
            "source": "Pokemon Let's Go Pikachu 1.0.2 main",
            "main_sha256": "1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8",
            "ghidra_version": "12.2 PUBLIC",
            "path_string": "bin/pokelib/item/item_hash_to_index.dat",
            "path_string_address": "main+0xf02a31",
            "reader_function": "main+0x1d4510",
            "accesses": {
                "count": "u32 little-endian at offset 0",
                "record_stride": "0x10 bytes",
                "key": "u64 at record+0 used by hash-map lookup/insertion",
                "mapped_value": "low u16 of u64 at record+8 stored by the loader",
            },
        },
        "cross_version_candidate_provenance": {
            "source": "pkNX ItemHash8 candidate parser",
            "source_path": "tools/src/pkNX/pkNX.Structures/Item/ItemHash8.cs",
            "commit": "d191cd0e5c05f2af81d9a41c1f1d82e6621b351a",
            "license": "GPL-3.0",
            "applicability": "SWSH mapping only; corroborating candidate shape, not the LGPE proof",
        },
    })

    output_path = args.output.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({
        "format_status": report["format_status"],
        "field_semantics_status": report["field_semantics_status"],
        "candidate_records": report["candidate_record_count"],
        "message_line_matches": report["message_index_match_count"],
        "unmatched_records": len(report["unmatched_record_indexes"]),
        "ambiguous_records": len(report["ambiguous_record_indexes"]),
        "output": output_path.as_posix(),
    }, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
