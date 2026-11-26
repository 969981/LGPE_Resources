"""Read-only LGPE sample decoders; layouts traced to pinned pkNX/pokedat sources.

Invoke as python -m lgpe_research.gamedata_decode --project ROOT --execute.
Without --execute, only the selected source paths are printed.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys

SCHEMA = "lgpe-gamedata-v1"

def sha(data):
    return hashlib.sha256(data).hexdigest()

def read_at(data, fmt, pos):
    size = struct.calcsize("<" + fmt)
    if pos < 0 or pos + size > len(data):
        raise ValueError(f"out of bounds {fmt} at {pos}")
    return struct.unpack_from("<" + fmt, data, pos)[0]

def tbl_labels(data):
    """Decode the validated AHTB index/hash/byte-label records without semantics."""
    if len(data) < 8:
        raise ValueError("truncated AHTB header")
    if data[:4] != b"AHTB":
        raise ValueError("unsupported AHTB magic")
    count = read_at(data, "I", 4)
    rows = []
    pos = 8
    for index in range(count):
        value_hash = read_at(data, "Q", pos)
        label_size = read_at(data, "H", pos + 8)
        pos += 10
        if pos + label_size > len(data):
            raise ValueError(f"truncated AHTB label at index {index}")
        raw_label = data[pos:pos + label_size]
        pos += label_size
        rows.append({
            "index": index,
            "hash": f"{value_hash:016x}",
            "label_length": label_size,
            "raw_label_hex": raw_label.hex(),
            "label": raw_label.rstrip(b"\0").decode("cp1252"),
        })
    if pos != len(data):
        raise ValueError(f"AHTB length/count mismatch: parsed {pos}, actual {len(data)}")
    return {
        "schema": SCHEMA,
        "format": "AHTB-label-table",
        "entry_count": count,
        "entries": rows,
    }

def message(data, tbl, pokedat):
    if len(data) < 20:
        raise ValueError("truncated message header")
    sections, count, length, key, section = struct.unpack_from("<HHIII", data)
    if sections != 1 or key or section + length != len(data):
        raise ValueError("invalid LGPE text header")
    if read_at(data, "I", section) != length or section + 4 + count * 8 > len(data):
        raise ValueError("invalid message section")
    offsets=[]
    for i in range(count):
        off, size, flag = struct.unpack_from("<IHH", data, section+4+i*8)
        if off < 4 + count * 8 or section + off + size*2 > len(data):
            raise ValueError(f"line {i} outside message section")
        offsets.append((off,size,flag))
    if tbl[:4] != b"AHTB":
        raise ValueError("unsupported TBL magic")
    labels=[]; pos=8
    for i in range(read_at(tbl,"I",4)):
        h=read_at(tbl,"Q",pos); n=read_at(tbl,"H",pos+8); pos+=10
        if pos+n>len(tbl):
            raise ValueError("truncated TBL label")
        label=tbl[pos:pos+n].rstrip(b"\0").decode("cp1252"); pos+=n
        labels.append({"id":label,"hash":f"{h:016x}"})
    if pos!=len(tbl) or len(labels)<count:
        raise ValueError("TBL length/count mismatch")
    # Use inspected external source rather than vendor GPL code into this repository.
    sys.path.insert(0,str(pokedat))
    try:
        from text_file import TextFile
        from text_config import TextConfig
        text=TextFile(data,TextConfig("LGPE"))
        lines=text.lines
    finally:
        sys.path.pop(0)
    if len(lines)!=count:
        raise ValueError("decoder line count mismatch")
    return {"schema":SCHEMA,"format":"LGPE-message","lines":[dict(index=i,**labels[i],flags=offsets[i][2],text=line) for i,line in enumerate(lines)],"unpaired_labels":labels[count:]}

def unlabeled_message(data, pokedat):
    """Decode LGPE text lines when no paired AHTB label table exists."""
    if len(data) < 20:
        raise ValueError("truncated message header")
    sections, count, length, key, section = struct.unpack_from("<HHIII", data)
    if sections != 1 or key or section + length != len(data):
        raise ValueError("invalid LGPE text header")
    if read_at(data, "I", section) != length or section + 4 + count * 8 > len(data):
        raise ValueError("invalid message section")
    for index in range(count):
        offset, size, _flags = struct.unpack_from("<IHH", data, section + 4 + index * 8)
        if offset < 4 + count * 8 or section + offset + size * 2 > len(data):
            raise ValueError(f"line {index} outside message section")

    sys.path.insert(0, str(pokedat))
    try:
        from text_file import TextFile
        from text_config import TextConfig
        lines = TextFile(data, TextConfig("LGPE")).lines
    finally:
        sys.path.pop(0)
    if len(lines) != count:
        raise ValueError("decoder line count mismatch")
    return {
        "schema": SCHEMA,
        "format": "LGPE-unlabeled-message",
        "entry_count": count,
        "raw_hex": data.hex(),
        "entries": [
            {"index": index, "text": line}
            for index, line in enumerate(lines)
        ],
    }

def personal(data):
    if not data or len(data)%0x54:
        raise ValueError("personal length is not a multiple of LGPE 0x54")
    rows=[]
    byte_fields="HP ATK DEF SPE SPA SPD Type1 Type2 CatchRate EvoStage".split()
    tail_fields="Gender HatchCycles BaseFriendship EXPGrowth EggGroup1 EggGroup2 Ability1 Ability2 AbilityH EscapeRate".split()
    for index in range(len(data)//0x54):
        b=data[index*0x54:(index+1)*0x54]
        r={"index":index,**dict(zip(byte_fields,b[:10])),**dict(zip(tail_fields,b[0x12:0x1c]))}
        for name,off in [("FormStatsIndex",0x1c),("FormSprite",0x1e),("BaseEXP",0x22),("Height",0x24),("Weight",0x26),("GoSpecies",0x48),("SpecialZ_Item",0x4c),("SpecialZ_BaseMove",0x4e),("SpecialZ_ZMove",0x50)]:
            r[name]=read_at(b,"H",off)
        r.update(FormCount=b[0x20],Color=b[0x21]&63,SpriteFlip=bool(b[0x21]&64),SpriteForm=bool(b[0x21]&128),IsRegionalForm=b[0x52]==1)
        ev=read_at(b,"H",10)
        r["EVYield"]=[(ev>>(i*2))&3 for i in range(6)]
        r["TMHM"]=[bool(b[0x28+i//8]&(1<<(i%8))) for i in range(64)]
        r["TypeTutors"]=[bool(b[0x38]&(1<<i)) for i in range(8)]
        r["raw_hex"]=b.hex()
        rows.append(r)
    return {"schema":SCHEMA,"format":"LGPE-personal","entry_size":84,"entries":rows}

def item(data):
    """Decode one 0x24-byte Item record exactly as consumed by EditorGG.EditItems."""
    if len(data) != 0x24:
        raise ValueError("pkNX GameManagerGG item records must be exactly 0x24 bytes")
    packed = read_at(data, "H", 0x08)
    boost0, boost1, boost2, boost3 = data[0x11:0x15]
    price = read_at(data, "H", 0)
    properties = {
        "HeldEffect": data[0x02], "HeldArgument": data[0x03],
        "NaturalGiftEffect": data[0x04], "FlingEffect": data[0x05],
        "FlingPower": data[0x06], "NaturalGiftPower": data[0x07],
        "EffectField": data[0x0A], "EffectBattle": data[0x0B],
        "Unk_0xC": data[0x0C], "Unk_0xD": data[0x0D],
        "SortIndex": data[0x0F], "CureInflict": data[0x10],
        "FunctionFlags0": data[0x15], "FunctionFlags1": data[0x16],
        "EVHP": struct.unpack_from("<b", data, 0x17)[0],
        "EVATK": struct.unpack_from("<b", data, 0x18)[0],
        "EVDEF": struct.unpack_from("<b", data, 0x19)[0],
        "EVSPE": struct.unpack_from("<b", data, 0x1A)[0],
        "EVSPA": struct.unpack_from("<b", data, 0x1B)[0],
        "EVSPD": struct.unpack_from("<b", data, 0x1C)[0],
        "HealAmount": data[0x1D], "PPGain": data[0x1E],
        "Friendship1": struct.unpack_from("<b", data, 0x1F)[0],
        "Friendship2": struct.unpack_from("<b", data, 0x20)[0],
        "Friendship3": struct.unpack_from("<b", data, 0x21)[0],
        "_0x22": data[0x22], "_0x23": data[0x23],
        "BuyPrice": price * 10, "SellPrice": price * 5,
        "NaturalGiftType": packed & 0x1F,
        "Flag1": bool((packed >> 5) & 1), "Flag2": bool((packed >> 6) & 1),
        "PocketField": (packed >> 7) & 0xF, "PocketBattle": packed >> 11,
        "Revive": (boost0 & 1) == 0, "ReviveAll": bool((boost0 >> 1) & 1),
        "LevelUp": bool((boost0 >> 2) & 1), "EvoStone": bool((boost0 >> 3) & 1),
        "BoostATK": boost0 >> 4, "BoostDEF": boost1 & 0xF,
        "BoostSPA": boost1 >> 4, "BoostSPD": boost2 & 0xF,
        "BoostSPE": boost2 >> 4, "BoostACC": boost3 & 0xF,
        "BoostCRIT": (boost3 >> 4) & 3, "BoostPP1": (boost3 >> 6) & 1,
        "BoostPPMax": (boost3 >> 7) & 1, "HealValue": data[0x1D],
        "UseConsume": (data[0x0E] & 0x0F) != 0,
        "UseKeep": (data[0x0E] & 0xF0) != 0,
    }
    return {
        "schema": SCHEMA, "format": "LGPE Item",
        "source_class": "pkNX.Structures.Item (EditorGG.EditItems)",
        "record_size": 0x24, "properties": properties, "raw_hex": data.hex(),
    }

def field_pocket(data):
    """Decode the 1.0.2 item-indexed byte table using only observed accesses."""
    if len(data) != 0x422:
        raise ValueError("LGPE field_pocket.dat must be exactly 0x422 bytes")
    entries = []
    pocket_field_counts = [0] * 8
    for item_index, raw_byte in enumerate(data):
        pocket_field = raw_byte & 0x07
        pocket_field_counts[pocket_field] += 1
        entries.append({
            "item_index": item_index,
            "raw_byte": raw_byte,
            "pocket_field": pocket_field,
            "high_bit_set": bool(raw_byte & 0x80),
        })
    return {
        "schema": SCHEMA,
        "format": "LGPE field_pocket.dat byte map",
        "entry_count": len(data),
        "source_class": "Let's Go Pikachu 1.0.2 main+0x71d1b0 / main+0x71d210",
        "observed_access": {
            "index": "item index; both helpers reject indices >= 0x422",
            "pocket_field": "raw_byte & 0x07; cross-validated with pkNX GameManagerGG Item.PocketField on the exact source",
            "high_bit_set": "raw_byte bit 7, observed through a signed-byte test",
        },
        "pocket_field_counts": pocket_field_counts,
        "entries": entries,
        "raw_hex": data.hex(),
    }

def battle_pocket(data):
    """Preserve the item-indexed bytes independently matched to GameManagerGG."""
    if len(data) != 0x422:
        raise ValueError("LGPE battle_pocket.dat must be exactly 0x422 bytes")
    entries = []
    pocket_battle_counts = {}
    for item_index, raw_byte in enumerate(data):
        key = str(raw_byte)
        pocket_battle_counts[key] = pocket_battle_counts.get(key, 0) + 1
        entries.append({
            "item_index": item_index,
            "raw_byte": raw_byte,
            "pocket_battle": raw_byte,
        })
    return {
        "schema": SCHEMA,
        "format": "LGPE battle_pocket.dat byte map",
        "entry_count": len(data),
        "source_class": "Pinned pkNX GameManagerGG Item.PocketBattle exact-source value match",
        "analysis_basis": "Each byte matches Item.FromBytes(itemNNN.dat).PocketBattle for item000.dat through item1057.dat; no exact-build main loader/accessor is established",
        "pocket_battle_value_counts": dict(sorted(pocket_battle_counts.items(), key=lambda entry: int(entry[0]))),
        "entries": entries,
        "raw_hex": data.hex(),
    }

def item_hash_to_index(data):
    """Decode the count and row accesses observed in the exact LGPE 1.0.2 main."""
    if len(data) < 4:
        raise ValueError("truncated item_hash_to_index count header")
    count = read_at(data, "I", 0)
    if 4 + count * 0x10 != len(data):
        raise ValueError("item_hash_to_index count/stride length mismatch")
    entries = []
    for record_index in range(count):
        offset = 4 + record_index * 0x10
        key = read_at(data, "Q", offset)
        value = read_at(data, "Q", offset + 8)
        entries.append({
            "record_index": record_index,
            "file_offset": offset,
            "key_u64_at_0": f"{key:016x}",
            "value_u64_at_8": f"{value:016x}",
            "loader_value_u16": value & 0xFFFF,
            "raw_hex": data[offset:offset + 0x10].hex(),
        })
    return {
        "schema": SCHEMA,
        "format": "LGPE item_hash_to_index count-prefixed table",
        "entry_count": count,
        "record_size": 0x10,
        "source_class": "Pokemon Let's Go Pikachu 1.0.2 main+0x1d4510",
        "reader_evidence": {
            "main_sha256": "1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8",
            "path_xref": "main+0xf02a31 -> main+0x1d4510",
            "count": "u32 little-endian at file offset 0",
            "record_stride": "0x10 bytes",
            "key": "u64 little-endian at record+0; used by the loader's hash-map lookup and insertion",
            "mapped_value": "u64 little-endian at record+8; low 16 bits are stored by the loader",
            "runtime_reachability": "static call references only; execution was not verified",
        },
        "entries": entries,
        "raw_hex": data.hex(),
    }

def zukan_sort_data(data):
    """Expose only the u16 array access proven for the ten zukan_sort resources."""
    if len(data) % 2:
        raise ValueError("zukan_sort source must have an even byte count for u16 access")
    entries = []
    for index in range(len(data) // 2):
        offset = index * 2
        raw = data[offset:offset + 2]
        entries.append({
            "index": index,
            "file_offset": offset,
            "value_u16le": read_at(data, "H", offset),
            "raw_hex": raw.hex(),
        })
    return {
        "schema": SCHEMA,
        "format": "LGPE 1.0.2 zukan_sort u16le array",
        "element_size": 2,
        "entry_count": len(entries),
        "element_semantics": "UNKNOWN",
        "reader_evidence": {
            "source_version": "Pokemon Let's Go Pikachu 1.0.2",
            "main_sha256": "1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8",
            "resource_loader": "main+0x3775e0",
            "path_pointer_table": "main+0x15520b8; ten indexed bin/app/zukan_data/bin/zukan_sort_*.bin paths",
            "count_projection": "loaded byte length at resource object +0x160, shifted right by one",
            "u16_access": "main+0x377800 reads *(u16 *)(resource object +0x1a0 + index*2)",
            "semantic_names": "UNKNOWN",
        },
        "entries": entries,
        "raw_hex": data.hex(),
    }

def grammar_data(data):
    """Decode observed grammar offsets and UTF-16LE segments losslessly.

    The exact-build main contains paths and resource requests for these files,
    but the consumer/parser is not recovered. The second header byte and the
    interstitial bytes therefore remain opaque; only bounds, offsets, and text
    segment encoding are described here.
    """
    if len(data) < 2:
        raise ValueError("truncated grammar header")
    offset_count = data[0]
    header_byte_1 = data[1]
    offset_table_end = 2 + offset_count * 2
    if offset_table_end > len(data):
        raise ValueError("grammar offset table exceeds source")
    interstitial_bytes = offset_count * header_byte_1
    payload_start = offset_table_end + interstitial_bytes
    if payload_start > len(data):
        raise ValueError("grammar interstitial region exceeds source")
    offsets = [read_at(data, "H", 2 + index * 2) for index in range(offset_count)]
    if offset_count and offsets[0] != payload_start:
        raise ValueError(
            f"grammar first offset {offsets[0]} does not match payload start {payload_start}"
        )
    if any(offset % 2 for offset in offsets):
        raise ValueError("grammar text offset is not UTF-16LE aligned")
    if any(offset < payload_start or offset >= len(data) for offset in offsets):
        raise ValueError("grammar text offset is outside the payload")
    if any(left >= right for left, right in zip(offsets, offsets[1:])):
        raise ValueError("grammar text offsets are not strictly increasing")
    if not offset_count and payload_start != len(data):
        raise ValueError("zero-entry grammar table has trailing payload")

    entries = []
    for index, offset in enumerate(offsets):
        end = offsets[index + 1] if index + 1 < len(offsets) else len(data)
        segment = data[offset:end]
        if len(segment) % 2:
            raise ValueError(f"grammar text segment {index} has odd byte length")
        try:
            text = segment.decode("utf-16-le")
        except UnicodeDecodeError as exc:
            raise ValueError(f"grammar text segment {index} is invalid UTF-16LE: {exc}") from exc
        if not text.endswith("\0"):
            raise ValueError(f"grammar text segment {index} is missing a UTF-16LE NUL terminator")
        entries.append({
            "index": index,
            "offset_table_file_offset": 2 + index * 2,
            "file_offset": offset,
            "byte_length": len(segment),
            "raw_hex": segment.hex(),
            "utf16le_strings": text[:-1].split("\0"),
        })

    return {
        "schema": SCHEMA,
        "format": "LGPE grammar offset table with UTF-16LE text segments",
        "format_status": "STRUCTURE_DECODED",
        "field_semantics_status": "UNKNOWN",
        "offset_count": offset_count,
        "header_byte_1": header_byte_1,
        "offset_table": {
            "file_offset": 2,
            "entry_count": offset_count,
            "entry_size": 2,
            "encoding": "u16 little-endian absolute file offsets",
        },
        "offsets": offsets,
        "interstitial_region": {
            "file_offset": offset_table_end,
            "byte_length": interstitial_bytes,
            "raw_hex": data[offset_table_end:payload_start].hex(),
            "semantics": "UNKNOWN",
        },
        "entries": entries,
        "reader_evidence": {
            "main_sha256": "1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8",
            "path_xref_function": "main+0x1ae750",
            "resource_request_helper": "main+0x00adc70",
            "parser": "not recovered; text/offset structure is based on actual 1.0.2 files",
        },
        "raw_hex": data.hex(),
    }

def trainer_data_7b(data):
    """Decode one trainer header using pkNX TrainerData7b property offsets."""
    if len(data) != 0x17:
        raise ValueError("pkNX TrainerData7b records must be exactly 0x17 bytes")
    ai = read_at(data, "I", 0x0C)
    return {
        "schema": SCHEMA, "format": "LGPE TrainerData7b",
        "source_class": "pkNX.Structures.TrainerData7b / EditorGG.EditTrainers",
        "record_size": 0x17,
        "properties": {
            "Class": read_at(data, "H", 0),
            # The pinned upstream class exposes this byte as BattleMode, but its own source marks it unsure.
            "Mode": data[2], "NumPokemon": data[3],
            "Item1": read_at(data, "H", 4), "Item2": read_at(data, "H", 6),
            "Item3": read_at(data, "H", 8), "Item4": read_at(data, "H", 0x0A),
            "AI": ai, "HasAllyTrainer": bool(ai & 8),
            "Heal": data[0x10] == 1, "HealRaw": data[0x10],
            "Money": data[0x11], "Unused_0x12": data[0x12],
            "Gift": read_at(data, "H", 0x14), "GiftQuantity": data[0x16],
        },
        "raw_hex": data.hex(),
    }

def trainer_poke_7b(data):
    """Decode 0x28-byte LGPE party slots using pkNX TrainerPoke7b."""
    entry_size = 0x28
    if len(data) % entry_size:
        raise ValueError("TrainerPoke7b byte length must be a multiple of 0x28")
    entries = []
    for index, start in enumerate(range(0, len(data), entry_size)):
        b = data[start:start + entry_size]
        iv32 = read_at(b, "I", 0x10)
        entries.append({
            "index": index,
            "properties": {
                "Gender": b[0] & 3, "Ability": (b[0] >> 4) & 3,
                "Nature": b[1],
                "EV_HP": b[2], "EV_ATK": b[3], "EV_DEF": b[4],
                "EV_SPA": b[5], "EV_SPD": b[6], "EV_SPE": b[7],
                "AV_HP": b[8], "AV_ATK": b[9], "AV_DEF": b[10],
                "AV_SPA": b[11], "AV_SPD": b[12], "AV_SPE": b[13],
                "Friendship": b[0x0E], "Rank": b[0x0F], "IV32": iv32,
                "IV_HP": iv32 & 0x1F, "IV_ATK": (iv32 >> 5) & 0x1F,
                "IV_DEF": (iv32 >> 10) & 0x1F, "IV_SPE": (iv32 >> 15) & 0x1F,
                "IV_SPA": (iv32 >> 20) & 0x1F, "IV_SPD": (iv32 >> 25) & 0x1F,
                "Shiny": bool((iv32 >> 30) & 1),
                "CanMegaEvolve": bool((iv32 >> 31) & 1),
                "CanDynamax": False,
                "MegaFormChoice": read_at(b, "H", 0x14),
                "Level": read_at(b, "H", 0x16),
                "Species": read_at(b, "H", 0x18),
                "Form": read_at(b, "H", 0x1A),
                "HeldItem": read_at(b, "H", 0x1C),
                "Move1": read_at(b, "H", 0x20), "Move2": read_at(b, "H", 0x22),
                "Move3": read_at(b, "H", 0x24), "Move4": read_at(b, "H", 0x26),
            },
            "raw_hex": b.hex(),
        })
    return {
        "schema": SCHEMA, "format": "LGPE TrainerPoke7b",
        "source_class": "pkNX.Structures.TrainerPoke7b / EditorGG.EditTrainers",
        "record_size": entry_size, "entries": entries, "raw_hex": data.hex(),
    }

def trainer_class_7b(data):
    """Decode only the fields named by pkNX TrainerClass7b; keep the rest opaque."""
    if len(data) != 0x24:
        raise ValueError("pkNX TrainerClass7b records must be exactly 0x24 bytes")
    return {
        "schema": SCHEMA, "format": "LGPE TrainerClass7b",
        "source_class": "pkNX.Structures.TrainerClass7b / EditorGG.EditTrainers",
        "record_size": 0x24,
        "properties": {
            "Unk_0x00": data[0], "Group": data[1],
            "BallID": data[2], "Unk_0x03": data[3],
        },
        "opaque_tail_hex": data[4:].hex(), "raw_hex": data.hex(),
    }

def evolution_set_7(data):
    """Decode the fixed 8 x 8-byte table consumed by pkNX EvolutionSet7."""
    if len(data) != 0x40:
        raise ValueError("pkNX EvolutionSet7 records must be exactly 0x40 bytes")
    entries = []
    for index in range(8):
        offset = index * 8
        form_signed = struct.unpack_from("<b", data, offset + 6)[0]
        species = read_at(data, "H", offset + 4)
        entries.append({
            "index": index,
            "properties": {
                "Method": data[offset],
                "Argument": read_at(data, "H", offset + 2),
                "Species": species,
                # EvolutionSet7 clamps negative raw forms to zero.
                "Form": max(form_signed, 0),
                "Level": data[offset + 7],
                "HasData": species != 0,
            },
            "raw_hex": data[offset:offset + 8].hex(),
        })
    return {
        "schema": SCHEMA, "format": "LGPE EvolutionSet7",
        "source_class": "pkNX.Structures.EvolutionSet7 / GameManagerGG",
        "entry_size": 8, "entries": entries, "raw_hex": data.hex(),
    }

def mega_evolution_7(data):
    """Decode the 8-byte records consumed by pkNX MegaEvolutionSet."""
    if len(data) % 8:
        raise ValueError("pkNX MegaEvolutionSet data must be a multiple of 8 bytes")
    entries = []
    for index in range(len(data) // 8):
        offset = index * 8
        entries.append({
            "index": index,
            "properties": {
                "ToForm": read_at(data, "H", offset),
                "Method": read_at(data, "H", offset + 2),
                "Argument": read_at(data, "H", offset + 4),
            },
            "opaque_tail_hex": data[offset + 6:offset + 8].hex(),
            "raw_hex": data[offset:offset + 8].hex(),
        })
    return {
        "schema": SCHEMA, "format": "LGPE MegaEvolutionSet",
        "source_class": "pkNX.Structures.MegaEvolutionSet / GameManagerGG",
        "entry_size": 8, "entries": entries, "raw_hex": data.hex(),
    }

def encounter_static_7b(data):
    """Decode EncounterStatic7b rows selected by EditorGG.EditStatic."""
    size = 0x40
    if len(data) % size:
        raise ValueError("pkNX EncounterStatic7b data must be a multiple of 0x40 bytes")
    entries = []
    signed_fields = {
        "IV_HP": 0x2C, "IV_ATK": 0x2D, "IV_DEF": 0x2E,
        "IV_SPA": 0x2F, "IV_SPD": 0x30, "IV_SPE": 0x31,
        "EV_HP": 0x32, "EV_ATK": 0x33, "EV_DEF": 0x34,
        "EV_SPA": 0x35, "EV_SPD": 0x36, "EV_SPE": 0x37,
        "Boost_ATK": 0x38, "Boost_DEF": 0x39, "Boost_SPA": 0x3A,
        "Boost_SPD": 0x3B, "Boost_SPE": 0x3C,
    }
    for index in range(len(data) // size):
        row = data[index * size:(index + 1) * size]
        relearn_moves = [read_at(row, "H", 0x20 + i * 2) for i in range(4)]
        properties = {
            "Hash": read_at(row, "Q", 0), "Species": read_at(row, "H", 8),
            "Form": row[0x0A], "Level": row[0x0B], "Shiny": row[0x0C] & 3,
            "Gender": row[0x0D] & 3,
            "Nature": struct.unpack_from("<b", row, 0x0E)[0], "Ability": row[0x0F],
            **{f"Ptr{i}": read_at(row, "I", 0x10 + i * 4) for i in range(4)},
            **{f"RelearnMove{i + 1}": move for i, move in enumerate(relearn_moves)},
            "RelearnMoves": relearn_moves,
            "V1": read_at(row, "H", 0x28), "V2": read_at(row, "H", 0x2A),
            **{name: struct.unpack_from("<b", row, offset)[0] for name, offset in signed_fields.items()},
            "UnknownFlag3D": row[0x3D], "UnknownFlag3E": row[0x3E],
            "UnknownFlag3F": row[0x3F],
        }
        entries.append({"index": index, "properties": properties, "raw_hex": row.hex()})
    return {
        "schema": SCHEMA, "format": "LGPE EncounterStatic7b",
        "source_class": "pkNX.Structures.EncounterStatic7b / EditorGG.EditStatic",
        "entry_size": size, "entries": entries, "raw_hex": data.hex(),
    }

def encounter_gift_7b(data):
    """Decode EncounterGift7b rows selected by EditorGG.EditGift."""
    size = 0x20
    if len(data) % size:
        raise ValueError("pkNX EncounterGift7b data must be a multiple of 0x20 bytes")
    entries = []
    for index in range(len(data) // size):
        row = data[index * size:(index + 1) * size]
        properties = {
            "Hash": read_at(row, "Q", 0), "Species": read_at(row, "H", 8),
            "Form": row[0x0A], "Level": row[0x0B], "Shiny": row[0x0C] & 3,
            "Gender": row[0x0D] & 3,
            "Nature": struct.unpack_from("<b", row, 0x0E)[0], "Ability": row[0x0F],
            "SpecialMove": read_at(row, "H", 0x10),
            **{name: struct.unpack_from("<b", row, offset)[0] for name, offset in {
                "IV_HP": 0x12, "IV_ATK": 0x13, "IV_DEF": 0x14,
                "IV_SPA": 0x15, "IV_SPD": 0x16, "IV_SPE": 0x17,
                "AV_HP": 0x18, "AV_ATK": 0x19, "AV_DEF": 0x1A,
                "AV_SPA": 0x1B, "AV_SPD": 0x1C, "AV_SPE": 0x1D,
            }.items()},
            # pkNX exposes these move getters over bytes also named AV_HP..AV_SPE.
            "RelearnMoves": [read_at(row, "H", 0x18 + i * 2) for i in range(4)],
        }
        entries.append({"index": index, "properties": properties, "raw_hex": row.hex()})
    return {
        "schema": SCHEMA, "format": "LGPE EncounterGift7b",
        "source_class": "pkNX.Structures.EncounterGift7b / EditorGG.EditGift",
        "entry_size": size, "entries": entries, "raw_hex": data.hex(),
    }

def encounter_trade_7b(data):
    """Decode EncounterTrade7b rows selected by EditorGG.EditTrade."""
    size = 0x58
    if len(data) % size:
        raise ValueError("pkNX EncounterTrade7b data must be a multiple of 0x58 bytes")
    entries = []
    stat_names = ("HP", "ATK", "DEF", "SPA", "SPD", "SPE")
    for index in range(len(data) // size):
        row = data[index * size:(index + 1) * size]
        av_words = [read_at(row, "h", 0x1A + 2 * i) for i in range(6)]
        gender_raw = read_at(row, "h", 0x26)
        nature_raw = read_at(row, "h", 0x28)
        properties = {
            "HashTradeID": read_at(row, "Q", 0), "Species": read_at(row, "H", 8),
            "Form": row[0x0A], "Level": row[0x0C],
            **{f"IV_{name}": (-1 if read_at(row, "H", 0x0E + 2 * i) == 0x8000 else read_at(row, "H", 0x0E + 2 * i)) for i, name in enumerate(stat_names)},
            **{f"AV_{name}": word & 0xFF for name, word in zip(stat_names, av_words)},
            **{f"AV_{name}Rand": word == -0x8000 for name, word in zip(stat_names, av_words)},
            **{f"AV_{name}RandUpTo": (word & 0x4000) != 0 for name, word in zip(stat_names, av_words)},
            "Gender": 0 if gender_raw < 0 else gender_raw + 1,
            "Nature": -1 if nature_raw < 0 else nature_raw,
            "OT_Gender": read_at(row, "h", 0x2A), "TrainerID": read_at(row, "I", 0x2C),
            "HashTradeStringOTName": read_at(row, "Q", 0x30),
            "RequiredSpecies": read_at(row, "H", 0x42),
            "RequiredForm": read_at(row, "H", 0x44),
            **{f"UV_{name}": struct.unpack_from("<b", row, 0x46 + i)[0] for i, name in enumerate(stat_names)},
            "HashTradeStringNickname": read_at(row, "Q", 0x50),
        }
        entries.append({"index": index, "properties": properties, "raw_hex": row.hex()})
    return {
        "schema": SCHEMA, "format": "LGPE EncounterTrade7b",
        "source_class": "pkNX.Structures.EncounterTrade7b / EditorGG.EditTrade",
        "entry_size": size, "entries": entries, "raw_hex": data.hex(),
    }

def move_data_7(data):
    """Decode the WD BinLinker table consumed as Move7 by GameManagerGG."""
    if len(data) < 8 or data[:2] != b"WD":
        raise ValueError("LGPE move data must use the pkNX WD BinLinker identifier")
    count = read_at(data, "H", 2)
    table_end = 4 + (count + 1) * 4
    if not count or table_end > len(data):
        raise ValueError("invalid WD BinLinker entry count")
    offsets = [read_at(data, "I", 4 + index * 4) for index in range(count + 1)]
    if offsets[0] < table_end or offsets[-1] != len(data):
        raise ValueError("WD BinLinker offset table does not cover the input")
    if any(left > right for left, right in zip(offsets, offsets[1:])):
        raise ValueError("WD BinLinker offsets are not monotonic")
    entries = []
    for index, (start, end) in enumerate(zip(offsets, offsets[1:])):
        if start < table_end or end - start != 0x28:
            raise ValueError(f"Move7 entry {index} must be exactly 0x28 bytes")
        row = data[start:end]
        properties = {
            "Type": row[0x00], "Quality": row[0x01], "Category": row[0x02],
            "Power": row[0x03], "Accuracy": row[0x04], "PP": row[0x05],
            "Priority": row[0x06], "HitMin": row[0x07] & 0x0F,
            "HitMax": row[0x07] >> 4, "Inflict": read_at(row, "H", 0x08),
            "InflictPercent": row[0x0A], "InflictCount": row[0x0B],
            "TurnMin": row[0x0C], "TurnMax": row[0x0D],
            "CritStage": row[0x0E], "Flinch": row[0x0F],
            "EffectSequence": read_at(row, "H", 0x10), "Recoil": row[0x12],
            "Healing": row[0x13], "Target": row[0x14],
            "Stat1": row[0x15], "Stat2": row[0x16], "Stat3": row[0x17],
            "Stat1Stage": row[0x18], "Stat2Stage": row[0x19], "Stat3Stage": row[0x1A],
            "Stat1Percent": row[0x1B], "Stat2Percent": row[0x1C],
            "Stat3Percent": row[0x1D], "ZMove": read_at(row, "H", 0x1E),
            "ZPower": row[0x20], "ZEffect": row[0x21],
            "RefreshAfflictType": row[0x22], "RefreshAfflictPercent": row[0x23],
            "Flags": read_at(row, "I", 0x24),
        }
        entries.append({"index": index, "properties": properties, "raw_hex": row.hex()})
    return {
        "schema": SCHEMA, "format": "LGPE Move7 BinLinker",
        "source_class": "pkNX.Structures.Move7 / GameManagerGG",
        "identifier": "WD", "entry_size": 0x28,
        "entries": entries, "raw_hex": data.hex(),
    }

def learnset_6(data):
    """Decode Learnset6 Move/Level pairs while retaining its trailing word."""
    if len(data) < 4 or len(data) % 4:
        raise ValueError("pkNX Learnset6 data must be at least 4 bytes and a multiple of 4")
    count = len(data) // 4 - 1
    entries = []
    for index in range(count):
        offset = index * 4
        row = data[offset:offset + 4]
        move, level = struct.unpack_from("<hh", row)
        entries.append({
            "index": index,
            "properties": {"Move": move, "Level": level},
            "raw_hex": row.hex(),
        })
    trailing = data[-4:]
    return {
        "schema": SCHEMA, "format": "LGPE Learnset6",
        "source_class": "pkNX.Structures.Learnset6 / GameManagerGG",
        "entry_size": 4, "entries": entries,
        "trailing_word_hex": trailing.hex(),
        "trailing_word_signed": struct.unpack("<i", trailing)[0],
        "raw_hex": data.hex(),
    }

class FlatReader:
    def __init__(self,data): self.data=data
    def read(self,fmt,pos): return read_at(self.data,fmt,pos)
    def target(self,pos):
        dest=pos+self.read("I",pos)
        if dest<0 or dest+4>len(self.data): raise ValueError("invalid FlatBuffer target")
        return dest
    def field(self,table,index):
        vt=table-self.read("i",table)
        n=self.read("H",vt); size=self.read("H",vt+2)
        if n<4 or n%2 or vt+n>len(self.data) or table+size>len(self.data): raise ValueError("invalid FlatBuffer vtable")
        off=self.read("H",vt+4+index*2) if 4+index*2<n else 0
        if off and off>=size: raise ValueError("field outside table")
        return table+off if off else None
    def scalar(self,table,index,fmt):
        f=self.field(table,index)
        return self.read(fmt,f) if f is not None else 0
    def vector(self,table,index):
        f=self.field(table,index)
        if f is None: raise ValueError("missing required vector")
        pos=self.target(f); n=self.read("I",pos)
        if n>100000 or pos+4+n*4>len(self.data): raise ValueError("vector out of bounds")
        return [self.target(pos+4+i*4) for i in range(n)]

def encounters(data):
    f=FlatReader(data); root=f.target(0); rows=[]
    # Field order comes exclusively from pkNX FlatBuffers/LGPE/Schemas/wild.fbs.
    fields=[("ZoneID","Q"),("TrainerRankMin","i"),("TrainerRankMax","i")]
    for medium in ["Ground","Water","OldRod","GoodRod","SuperRod","Sky"]:
        if medium in ["Ground","Water","Sky"]:
            fields += [(medium+"SpawnAllowed","?"),(medium+"SpawnCountMax","i"),(medium+"SpawnDuration","i")]
        fields += [(medium+"Table"+s,"i") for s in ["EncounterRate","LevelMin","LevelMax","RandChanceTotal"]]
        fields += [(medium+"Table","vector")]
    for table in f.vector(root,0):
        row={}
        for i,(name,fmt) in enumerate(fields):
            if fmt=="vector":
                row[name]=[{"Probability":f.scalar(t,0,"i"),"Species":f.scalar(t,1,"i"),"Form":f.scalar(t,2,"h")} for t in f.vector(table,i)]
            else: row[name]=f.scalar(table,i,fmt)
        rows.append(row)
    return {"schema":SCHEMA,"format":"LGPE-EncounterArchive","tables":rows}

def run(project,execute=False):
    project=Path(project).resolve()
    source=project.parent/"1.0.2/2b7730a9e56498bbafac2002d4908c6b_NCA/1"
    samples=[f"bin/message/{lang}/{name}.dat" for lang in ["English","Simp_Chinese"] for name in ["common/bag","script/master_trainer"]]
    samples += ["bin/pokelib/personal/personal_total.bin","bin/field/param/encount/encount_data_p.bin","bin/field/param/encount/encount_data_e.bin"]
    results=[]
    git="D:/Tool/Git/cmd/git.exe"
    versions={name:subprocess.check_output([git,"-C",str(project/"tools/src"/name),"rev-parse","HEAD"],text=True).strip() for name in ["pkNX","pokedat"]}
    for rel in samples:
        src=source/rel; out=project/"decoded/1.0.2/romfs"/Path(rel).with_suffix(".json")
        if not execute:
            print(json.dumps({"source":str(src),"output":str(out),"status":"DRY_RUN"})); continue
        rec={"source":rel,"tool_commits":versions}
        try:
            data=src.read_bytes(); rec.update(input_sha256=sha(data),input_bytes=len(data),header_hex=data[:32].hex())
            if src.suffix==".dat":
                tbl=src.with_suffix(".tbl").read_bytes(); rec.update(tbl_sha256=sha(tbl),tbl_bytes=len(tbl))
                value=message(data,tbl,project/"tools/src/pokedat"); rec["count"]=len(value["lines"]); rec["unpaired_labels"]=len(value["unpaired_labels"])
                rec["escaped_newline_lines"]=sum("\\n" in r["text"] for r in value["lines"])
                rec["variable_lines"]=sum("[VAR" in r["text"] for r in value["lines"])
            elif "personal_total" in rel:
                value=personal(data); rec["count"]=len(value["entries"])
            else:
                value=encounters(data); rec["count"]=len(value["tables"])
                rec["slot_count"]=sum(len(v) for row in value["tables"] for v in row.values() if isinstance(v,list))
            payload=(json.dumps(value,ensure_ascii=False,indent=2)+"\n").encode("utf-8")
            if out.exists() and out.read_bytes()!=payload: raise FileExistsError("conflicting output exists")
            out.parent.mkdir(parents=True,exist_ok=True)
            if not out.exists():
                with out.open("xb") as stream: stream.write(payload)
            rec.update(status="DECODED",output=str(out.relative_to(project)),output_sha256=sha(payload),output_bytes=len(payload))
            if sha(src.read_bytes())!=rec["input_sha256"]: raise ValueError("source changed during decode")
        except Exception as exc:
            rec.update(status="ERROR",error=f"{type(exc).__name__}: {exc}")
        print(json.dumps(rec,ensure_ascii=False)); results.append(rec)
    if execute:
        log=project/"decoded/gamedata-sample-evidence.json"
        log.write_text(json.dumps(results,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return 1 if any(r["status"]=="ERROR" for r in results) else 0

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project",required=True); parser.add_argument("--execute",action="store_true")
    args=parser.parse_args(); raise SystemExit(run(args.project,args.execute))

if __name__=="__main__": main()
