import json
import sys
from pathlib import Path, PurePosixPath

PROJECT = Path(__file__).resolve().parents[2]
ROOT = PROJECT / "decoded/1.0.2/romfs/bin/archive/waza_oboe.gfpak.contents"
CROSSCHECK = PROJECT / "work/gamedata-crosscheck/pknx-learnsets.json"
MANIFEST = PROJECT / "manifests/learnsets.jsonl"


def main() -> int:
    references = json.loads(CROSSCHECK.read_text(encoding="utf-8"))
    manifest = [
        json.loads(line) for line in MANIFEST.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    by_path = {row["source_internal_path"]: row for row in manifest}
    mismatches = []
    total_entries = 0
    for reference in references:
        internal_path = reference["internalPath"]
        raw_path = ROOT.joinpath(*PurePosixPath(internal_path).parts)
        output_path = raw_path.with_suffix(".json")
        value = json.loads(output_path.read_text(encoding="utf-8"))
        row = by_path.get(internal_path)
        moves = [entry["properties"]["Move"] for entry in value["entries"]]
        levels = [entry["properties"]["Level"] for entry in value["entries"]]
        total_entries += len(value["entries"])
        checks = {
            "manifest_status": bool(row and row.get("status") == "DECODED"),
            "entry_count": len(value["entries"]) == reference["count"],
            "moves": moves == reference["moves"],
            "levels": levels == reference["levels"],
            "raw_bytes": value["raw_hex"].upper() == reference["raw"],
            "round_trip": reference["roundTrip"] == reference["raw"],
            "trailing_word": value["trailing_word_hex"].upper() == reference["raw"][-8:].upper(),
        }
        for name, passed in checks.items():
            if not passed:
                mismatches.append({"internal_path": internal_path, "check": name})
    result = {
        "status": "CROSS_VALIDATED" if not mismatches and len(references) == 980 else "MISMATCH",
        "pkNX_commit": "d191cd0e5c05f2af81d9a41c1f1d82e6621b351a",
        "members": len(references), "learnset_entries": total_entries,
        "mismatches": mismatches,
    }
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "CROSS_VALIDATED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
