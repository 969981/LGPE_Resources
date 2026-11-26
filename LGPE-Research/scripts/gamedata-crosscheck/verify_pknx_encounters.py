"""Cross-check LGPE static/gift/trade exports against pinned pkNX objects."""
from __future__ import annotations

import json
from pathlib import Path


def main() -> int:
    project = Path(__file__).resolve().parents[2]
    source_root = project.parent / "1.0.2/2b7730a9e56498bbafac2002d4908c6b_NCA/1"
    decoded = project / "decoded/1.0.2/romfs/bin/script_event_data"
    ref_path = project / "work/gamedata-crosscheck/pknx-encounter-records-sample.json"
    reference = json.loads(ref_path.read_text(encoding="utf-8"))
    specs = [
        ("event_encount.bin", "staticRaw", "staticRecords", "LGPE EncounterStatic7b", [
            "Hash", "Species", "Form", "Level", "Shiny", "Gender", "Nature", "Ability",
            "Ptr0", "Ptr1", "Ptr2", "Ptr3", "RelearnMove1", "RelearnMove2",
            "RelearnMove3", "RelearnMove4", "RelearnMoves", "V1", "V2",
            "IV_HP", "IV_ATK", "IV_DEF", "IV_SPA", "IV_SPD", "IV_SPE",
            "EV_HP", "EV_ATK", "EV_DEF", "EV_SPA", "EV_SPD", "EV_SPE",
            "Boost_ATK", "Boost_DEF", "Boost_SPA", "Boost_SPD", "Boost_SPE",
            "UnknownFlag3D", "UnknownFlag3E", "UnknownFlag3F",
        ]),
        ("add_poke.bin", "giftRaw", "giftRecords", "LGPE EncounterGift7b", [
            "Hash", "Species", "Form", "Level", "Shiny", "Gender", "Nature", "Ability",
            "SpecialMove", "IV_HP", "IV_ATK", "IV_DEF", "IV_SPA", "IV_SPD", "IV_SPE",
            "AV_HP", "AV_ATK", "AV_DEF", "AV_SPA", "AV_SPD", "AV_SPE", "RelearnMoves",
        ]),
        ("field_trade_data.bin", "tradeRaw", "tradeRecords", "LGPE EncounterTrade7b", [
            "HashTradeID", "Species", "Form", "Level", "IV_HP", "IV_ATK", "IV_DEF",
            "IV_SPA", "IV_SPD", "IV_SPE", "AV_HP", "AV_ATK", "AV_DEF", "AV_SPA",
            "AV_SPD", "AV_SPE", "AV_HPRand", "AV_ATKRand", "AV_DEFRand", "AV_SPARand",
            "AV_SPDRand", "AV_SPERand", "AV_HPRandUpTo", "AV_ATKRandUpTo",
            "AV_DEFRandUpTo", "AV_SPARandUpTo", "AV_SPDRandUpTo", "AV_SPERandUpTo",
            "Gender", "Nature", "OT_Gender", "TrainerID", "HashTradeStringOTName",
            "RequiredSpecies", "RequiredForm", "UV_HP", "UV_ATK", "UV_DEF", "UV_SPA",
            "UV_SPD", "UV_SPE", "HashTradeStringNickname",
        ]),
    ]
    results = []
    for rel, raw_key, records_key, format_name, fields in specs:
        source = source_root / "bin/script_event_data" / rel
        raw = source.read_bytes()
        if raw.hex().upper() != reference[raw_key]:
            raise ValueError(f"pkNX harness source bytes differ: {rel}")
        output = json.loads((decoded / Path(rel).with_suffix(".json")).read_text(encoding="utf-8"))
        if output["format"] != format_name:
            raise ValueError(f"unexpected format label for {rel}: {output['format']}")
        if bytes.fromhex(output["raw_hex"]) != raw:
            raise ValueError(f"decoder raw_hex does not reassemble input: {rel}")
        refs = reference[records_key]
        if len(output["entries"]) != len(refs):
            raise ValueError(f"record count differs from pkNX: {rel}")
        for index, (actual, expected) in enumerate(zip(output["entries"], refs)):
            if bytes.fromhex(actual["raw_hex"]).hex().upper() != expected["raw"]:
                raise ValueError(f"entry raw bytes differ from pkNX: {rel}#{index}")
            for field in fields:
                if actual["properties"].get(field) != expected["record"].get(field):
                    raise ValueError(f"{rel} entry {index} field {field} differs from pkNX")
        results.append({"source": f"bin/script_event_data/{rel}", "bytes": len(raw), "records": len(refs), "fields_per_record": len(fields)})
    print(json.dumps({
        "status": "CROSS_VALIDATED", "pkNX_commit": "d191cd0e5c05f2af81d9a41c1f1d82e6621b351a",
        "samples": results, "mismatches": 0,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
