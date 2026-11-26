"""Cross-check Python LGPE item/trainer JSON with pinned pkNX object getters."""
from __future__ import annotations

import json
from pathlib import Path


def main() -> int:
    project = Path(__file__).resolve().parents[2]
    source_root = project.parent / "1.0.2/2b7730a9e56498bbafac2002d4908c6b_NCA/1"
    decoded = project / "decoded/1.0.2/romfs/bin"
    pknx_path = project / "work/gamedata-crosscheck/pknx-trainer-item-sample.json"
    pknx = json.loads(pknx_path.read_text(encoding="utf-8"))

    def verify(rel: str, output_rel: str, pknx_raw: str, output: dict) -> bytes:
        source = source_root / Path(rel)
        raw = source.read_bytes()
        if raw.hex().upper() != pknx_raw:
            raise ValueError(f"pkNX harness source bytes differ: {rel}")
        if bytes.fromhex(output["raw_hex"]) != raw:
            raise ValueError(f"decoded output does not reassemble input: {rel}")
        if (decoded / Path(output_rel)).is_file() is False:
            raise FileNotFoundError(decoded / Path(output_rel))
        saved = json.loads((decoded / Path(output_rel)).read_text(encoding="utf-8"))
        if saved != output:
            raise ValueError(f"saved export differs from tested decoder result: {rel}")
        return raw

    item = json.loads((decoded / "pokelib/item/item001.json").read_text(encoding="utf-8"))
    verify(
        "bin/pokelib/item/item001.dat", "pokelib/item/item001.json",
        pknx["itemRaw"], item,
    )
    if item["properties"] != pknx["item"]:
        differences = sorted(
            key for key in set(item["properties"]) | set(pknx["item"])
            if item["properties"].get(key) != pknx["item"].get(key)
        )
        raise ValueError(f"item properties differ from pkNX Item.FromBytes: {differences}")

    trainer = json.loads((decoded / "trainer/trainer_data/trainer_data_001.json").read_text(encoding="utf-8"))
    verify(
        "bin/trainer/trainer_data/trainer_data_001.bin",
        "trainer/trainer_data/trainer_data_001.json", pknx["trainerDataRaw"], trainer,
    )
    trainer_fields = [
        "Class", "Mode", "NumPokemon", "Item1", "Item2", "Item3", "Item4",
        "AI", "HasAllyTrainer", "Heal", "Money", "Gift", "GiftQuantity",
    ]
    for key in trainer_fields:
        if trainer["properties"].get(key) != pknx["trainerData"].get(key):
            raise ValueError(f"trainer field {key} differs from pkNX TrainerData7b")

    party = json.loads((decoded / "trainer/trainer_poke/trainer_poke_001.json").read_text(encoding="utf-8"))
    verify(
        "bin/trainer/trainer_poke/trainer_poke_001.bin",
        "trainer/trainer_poke/trainer_poke_001.json", pknx["trainerPokeRaw"], party,
    )
    party_fields = [
        "Gender", "Ability", "Nature", "EV_HP", "EV_ATK", "EV_DEF", "EV_SPA",
        "EV_SPD", "EV_SPE", "AV_HP", "AV_ATK", "AV_DEF", "AV_SPA", "AV_SPD",
        "AV_SPE", "Friendship", "Rank", "IV32", "IV_HP", "IV_ATK", "IV_DEF",
        "IV_SPE", "IV_SPA", "IV_SPD", "Shiny", "CanMegaEvolve", "CanDynamax",
        "MegaFormChoice", "Level", "Species", "Form", "HeldItem", "Move1",
        "Move2", "Move3", "Move4",
    ]
    if len(party["entries"]) != len(pknx["trainerParty"]):
        raise ValueError("trainer party record counts differ from pkNX TrainerPoke7b.ReadTeam")
    for index, (actual, reference) in enumerate(zip(party["entries"], pknx["trainerParty"])):
        for key in party_fields:
            if actual["properties"].get(key) != reference.get(key):
                raise ValueError(f"trainer party {index} field {key} differs from pkNX")

    trainer_type = json.loads((decoded / "trainer/trainer_type/trainer_type_001.json").read_text(encoding="utf-8"))
    verify(
        "bin/trainer/trainer_type/trainer_type_001.bin",
        "trainer/trainer_type/trainer_type_001.json", pknx["trainerTypeRaw"], trainer_type,
    )
    for key in ["Unk_0x00", "Group", "BallID", "Unk_0x03"]:
        if trainer_type["properties"].get(key) != pknx["trainerClass"].get(key):
            raise ValueError(f"trainer class field {key} differs from pkNX TrainerClass7b")

    pknx2 = json.loads((project / "work/gamedata-crosscheck/pknx-trainer-item-sample-002.json").read_text(encoding="utf-8"))
    item2 = json.loads((decoded / "pokelib/item/item002.json").read_text(encoding="utf-8"))
    verify("bin/pokelib/item/item002.dat", "pokelib/item/item002.json", pknx2["itemRaw"], item2)
    if item2["properties"] != pknx2["item"]:
        raise ValueError("item002 properties differ from pkNX Item.FromBytes")

    trainer2 = json.loads((decoded / "trainer/trainer_data/trainer_data_002.json").read_text(encoding="utf-8"))
    verify("bin/trainer/trainer_data/trainer_data_002.bin", "trainer/trainer_data/trainer_data_002.json", pknx2["trainerDataRaw"], trainer2)
    for key in trainer_fields:
        if trainer2["properties"].get(key) != pknx2["trainerData"].get(key):
            raise ValueError(f"trainer 002 field {key} differs from pkNX TrainerData7b")

    party2 = json.loads((decoded / "trainer/trainer_poke/trainer_poke_002.json").read_text(encoding="utf-8"))
    verify("bin/trainer/trainer_poke/trainer_poke_002.bin", "trainer/trainer_poke/trainer_poke_002.json", pknx2["trainerPokeRaw"], party2)
    if len(party2["entries"]) != len(pknx2["trainerParty"]):
        raise ValueError("trainer 002 party count differs from pkNX TrainerPoke7b.ReadTeam")
    for index, (actual, reference) in enumerate(zip(party2["entries"], pknx2["trainerParty"])):
        for key in party_fields:
            if actual["properties"].get(key) != reference.get(key):
                raise ValueError(f"trainer 002 party {index} field {key} differs from pkNX")

    type2 = json.loads((decoded / "trainer/trainer_type/trainer_type_002.json").read_text(encoding="utf-8"))
    verify("bin/trainer/trainer_type/trainer_type_002.bin", "trainer/trainer_type/trainer_type_002.json", pknx2["trainerTypeRaw"], type2)
    for key in ["Unk_0x00", "Group", "BallID", "Unk_0x03"]:
        if type2["properties"].get(key) != pknx2["trainerClass"].get(key):
            raise ValueError(f"trainer class 002 field {key} differs from pkNX TrainerClass7b")

    print(json.dumps({
        "status": "CROSS_VALIDATED",
        "pkNX_commit": "d191cd0e5c05f2af81d9a41c1f1d82e6621b351a",
        "samples": [
            {"source": "bin/pokelib/item/item001.dat + item002.dat", "bytes": 72, "properties_per_item": len(item["properties"])},
            {"source": "bin/trainer/trainer_data/trainer_data_{001,002}.bin", "bytes": 46, "fields_per_record": len(trainer_fields)},
            {"source": "bin/trainer/trainer_poke/trainer_poke_{001,002}.bin", "bytes": len(bytes.fromhex(party["raw_hex"])) + len(bytes.fromhex(party2["raw_hex"])), "records": len(party["entries"]) + len(party2["entries"]), "fields_per_record": len(party_fields)},
            {"source": "bin/trainer/trainer_type/trainer_type_{001,002}.bin", "bytes": 72, "fields_per_record": 4},
        ],
        "mismatches": 0,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
