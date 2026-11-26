"""Cross-check LGPE Move7 table exports against pinned pkNX objects."""
from __future__ import annotations

import json
from pathlib import Path


FIELDS = [
    "Type", "Quality", "Category", "Power", "Accuracy", "PP", "Priority",
    "HitMin", "HitMax", "Inflict", "InflictPercent", "InflictCount",
    "TurnMin", "TurnMax", "CritStage", "Flinch", "EffectSequence", "Recoil",
    "Healing", "Target", "Stat1", "Stat2", "Stat3", "Stat1Stage", "Stat2Stage",
    "Stat3Stage", "Stat1Percent", "Stat2Percent", "Stat3Percent", "ZMove",
    "ZPower", "ZEffect", "RefreshAfflictType", "RefreshAfflictPercent", "Flags",
]


def main() -> int:
    project = Path(__file__).resolve().parents[2]
    source_root = project.parent / "1.0.2/2b7730a9e56498bbafac2002d4908c6b_NCA/1"
    source_rel = "bin/pokelib/waza/waza_data.bin"
    raw = (source_root / source_rel).read_bytes()
    reference = json.loads((project / "work/gamedata-crosscheck/pknx-move-sample.json").read_text(encoding="utf-8"))
    output_path = project / "decoded/1.0.2/romfs/bin/pokelib/waza/waza_data.json"
    actual = json.loads(output_path.read_text(encoding="utf-8"))
    if raw.hex().upper() != reference["moveRaw"]:
        raise ValueError("pkNX harness source bytes differ from move file")
    if reference["identifier"] != actual["identifier"] or reference["identifier"] != "WD":
        raise ValueError("move BinLinker identifier differs from pkNX GameManagerGG mapping")
    if bytes.fromhex(actual["raw_hex"]) != raw:
        raise ValueError("decoded move table raw_hex does not reassemble input")
    if len(actual["entries"]) != reference["count"] or len(actual["entries"]) != len(reference["records"]):
        raise ValueError("move record count differs from pkNX BinLinkerAccessor")
    for index, (entry, pknx, raw_hex) in enumerate(zip(actual["entries"], reference["records"], reference["recordRaw"])):
        if entry["raw_hex"].upper() != raw_hex:
            raise ValueError(f"Move7 entry {index} raw bytes differ from pkNX")
        for field in FIELDS:
            if entry["properties"].get(field) != pknx.get(field):
                raise ValueError(f"Move7 entry {index} field {field} differs from pkNX")
    print(json.dumps({
        "status": "CROSS_VALIDATED", "pkNX_commit": "d191cd0e5c05f2af81d9a41c1f1d82e6621b351a",
        "source": source_rel, "bytes": len(raw), "identifier": "WD",
        "records": len(actual["entries"]), "fields_per_record": len(FIELDS), "mismatches": 0,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
