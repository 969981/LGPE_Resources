"""Cross-check LGPE evolution exports against pinned pkNX C# objects."""
from __future__ import annotations

import json
from pathlib import Path


def main() -> int:
    project = Path(__file__).resolve().parents[2]
    source_root = project.parent / "1.0.2/2b7730a9e56498bbafac2002d4908c6b_NCA/1"
    decoded = project / "decoded/1.0.2/romfs/bin/pokelib"
    pknx_path = project / "work/gamedata-crosscheck/pknx-evolution-sample.json"
    pknx = json.loads(pknx_path.read_text(encoding="utf-8"))
    evo_fields = ["Method", "Argument", "Species", "Form", "Level", "HasData"]
    mega_fields = ["ToForm", "Method", "Argument"]

    def verify(rel: str, suffix: str, pknx_raw: str, reference: list[dict], fields: list[str]) -> dict:
        source = source_root / Path(rel)
        raw = source.read_bytes()
        if raw.hex().upper() != pknx_raw:
            raise ValueError(f"pkNX harness source bytes differ: {rel}")
        output_path = decoded / Path(rel).with_suffix(".json").relative_to("bin/pokelib")
        actual = json.loads(output_path.read_text(encoding="utf-8"))
        if bytes.fromhex(actual["raw_hex"]) != raw:
            raise ValueError(f"decoder raw_hex does not reassemble input: {rel}")
        if len(actual["entries"]) != len(reference):
            raise ValueError(f"record count differs from pkNX: {rel}")
        if actual["format"] != suffix:
            raise ValueError(f"unexpected format label: {rel}")
        for index, (entry, expected) in enumerate(zip(actual["entries"], reference)):
            props = entry["properties"]
            for field in fields:
                if props.get(field) != expected.get(field):
                    raise ValueError(f"{rel} entry {index} field {field} differs from pkNX")
        return actual

    samples = []
    for index in (1, 2):
        key = f"evolution{index:03d}"
        rel = f"bin/pokelib/evolution/evo_{index:03d}.bin"
        result = verify(rel, "LGPE EvolutionSet7", pknx[key + "Raw"], pknx[key], evo_fields)
        samples.append({"source": rel, "bytes": len(bytes.fromhex(result["raw_hex"])), "entries": len(result["entries"])})
    for index in (1, 2):
        key = f"mega{index:03d}"
        rel = f"bin/pokelib/mega_evolution/mega_{index:03d}.bin"
        result = verify(rel, "LGPE MegaEvolutionSet", pknx[key + "Raw"], pknx[key], mega_fields)
        samples.append({"source": rel, "bytes": len(bytes.fromhex(result["raw_hex"])), "entries": len(result["entries"])})

    print(json.dumps({
        "status": "CROSS_VALIDATED", "pkNX_commit": "d191cd0e5c05f2af81d9a41c1f1d82e6621b351a",
        "samples": samples, "mismatches": 0,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
