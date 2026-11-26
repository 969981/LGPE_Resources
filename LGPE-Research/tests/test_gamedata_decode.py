import struct
import sys
import unittest
from pathlib import Path
from lgpe_research import gamedata_decode
from lgpe_research.gamedata_decode import (
    FlatReader, battle_pocket, encounters, field_pocket, grammar_data, item, message, personal, tbl_labels,
    encounter_gift_7b, encounter_static_7b, encounter_trade_7b,
    evolution_set_7, mega_evolution_7, move_data_7, trainer_class_7b,
    trainer_data_7b, trainer_poke_7b, learnset_6,
)

class GameDataTests(unittest.TestCase):
    def test_unlabeled_lgpe_text_decoder_keeps_indices_without_fabricated_labels(self):
        decoder = getattr(gamedata_decode, "unlabeled_message", None)
        self.assertTrue(callable(decoder), "unlabeled LGPE message decoder is not implemented")
        if not callable(decoder):
            return

        pokedat = Path(__file__).resolve().parents[1] / "tools/src/pokedat"
        sys.path.insert(0, str(pokedat))
        try:
            from text_file import TextFile
            from text_config import TextConfig

            data = bytes(TextFile.from_lines(["A", "B"], [3, 5], TextConfig("LGPE")).data)
        finally:
            sys.path.remove(str(pokedat))

        result = decoder(data, pokedat)

        self.assertEqual({key: value for key, value in result.items() if key != "raw_hex"}, {
            "schema": "lgpe-gamedata-v1",
            "format": "LGPE-unlabeled-message",
            "entry_count": 2,
            "entries": [{"index": 0, "text": "A"}, {"index": 1, "text": "B"}],
        })
        self.assertEqual(bytes.fromhex(result.get("raw_hex", "")), data)

    def test_unlabeled_lgpe_text_decoder_rejects_truncated_header(self):
        with self.assertRaisesRegex(ValueError, "truncated message header"):
            gamedata_decode.unlabeled_message(b"not text", Path("tools/src/pokedat"))

    def test_grammar_table_keeps_offsets_opaque_block_and_utf16_fragments(self):
        data = bytearray(24)
        data[:2] = bytes((2, 3))
        struct.pack_into("<HH", data, 2, 12, 20)
        data[6:12] = bytes.fromhex("010203040506")
        data[12:20] = "A\0B\0".encode("utf-16-le")
        data[20:24] = "x\0".encode("utf-16-le")

        result = grammar_data(bytes(data))

        self.assertEqual(result["format"], "LGPE grammar offset table with UTF-16LE text segments")
        self.assertEqual(result["offset_count"], 2)
        self.assertEqual(result["header_byte_1"], 3)
        self.assertEqual(result["offsets"], [12, 20])
        self.assertEqual(result["interstitial_region"], {
            "file_offset": 6,
            "byte_length": 6,
            "raw_hex": "010203040506",
            "semantics": "UNKNOWN",
        })
        self.assertEqual(result["entries"][0]["utf16le_strings"], ["A", "B"])
        self.assertEqual(result["entries"][1]["utf16le_strings"], ["x"])
        self.assertEqual(bytes.fromhex(result["raw_hex"]), bytes(data))

    def test_grammar_table_accepts_exact_empty_two_byte_form(self):
        result = grammar_data(b"\x00\x00")

        self.assertEqual(result["offset_count"], 0)
        self.assertEqual(result["header_byte_1"], 0)
        self.assertEqual(result["offsets"], [])
        self.assertEqual(result["interstitial_region"]["byte_length"], 0)
        self.assertEqual(result["entries"], [])

    def test_grammar_table_rejects_bad_offset_extent_and_unterminated_text(self):
        malformed = bytearray(24)
        malformed[:2] = bytes((2, 3))
        struct.pack_into("<HH", malformed, 2, 12, 20)
        malformed[6:12] = bytes(6)
        malformed[12:20] = "A\0B\0".encode("utf-16-le")
        malformed[20:24] = "x\0".encode("utf-16-le")

        bad_offset = bytearray(malformed)
        struct.pack_into("<H", bad_offset, 2, 14)
        with self.assertRaisesRegex(ValueError, "payload start"):
            grammar_data(bytes(bad_offset))

        bad_region = bytes((1, 8, 4, 0))
        with self.assertRaisesRegex(ValueError, "interstitial region"):
            grammar_data(bad_region)

        unterminated = bytearray(malformed)
        unterminated[-2:] = b"x\x00"
        with self.assertRaisesRegex(ValueError, "NUL terminator"):
            grammar_data(bytes(unterminated))

    def test_lgpe_item_hash_table_preserves_rows_and_models_loader_projection(self):
        data = (
            struct.pack("<I", 2)
            + struct.pack("<QQ", 0xAABBCCDDEEFF0011, 1)
            + struct.pack("<QQ", 0x1234567890ABCDEF, 0x1234)
        )
        decoder = getattr(gamedata_decode, "item_hash_to_index", None)
        self.assertIsNotNone(decoder, "exact-build item-hash reader is not implemented")

        result = decoder(data)

        self.assertEqual(result["format"], "LGPE item_hash_to_index count-prefixed table")
        self.assertEqual(result["entry_count"], 2)
        self.assertEqual(result["record_size"], 0x10)
        self.assertEqual(result["entries"][0], {
            "record_index": 0,
            "file_offset": 4,
            "key_u64_at_0": "aabbccddeeff0011",
            "value_u64_at_8": "0000000000000001",
            "loader_value_u16": 1,
            "raw_hex": "1100ffeeddccbbaa0100000000000000",
        })
        self.assertEqual(result["entries"][1]["loader_value_u16"], 0x1234)
        self.assertEqual(result["entries"][1]["raw_hex"], "efcdab90785634123412000000000000")
        self.assertEqual(bytes.fromhex(result["raw_hex"]), data)
        self.assertEqual(
            b"".join(bytes.fromhex(row["raw_hex"]) for row in result["entries"]),
            data[4:],
        )

    def test_lgpe_item_hash_table_rejects_count_stride_mismatch(self):
        decoder = getattr(gamedata_decode, "item_hash_to_index", None)
        self.assertIsNotNone(decoder, "exact-build item-hash reader is not implemented")
        for data in (
            struct.pack("<I", 1) + bytes(15),
            struct.pack("<I", 0) + b"x",
        ):
            with self.assertRaisesRegex(ValueError, "count/stride"):
                decoder(data)

    def test_zukan_sort_u16_array_keeps_only_verified_access_and_raw_values(self):
        data = struct.pack("<4H", 0x0001, 0x0137, 0x02ff, 0xffff)
        decoder = getattr(gamedata_decode, "zukan_sort_data", None)
        self.assertTrue(callable(decoder), "exact-main zukan_sort u16 reader is not implemented")

        result = decoder(data)

        self.assertEqual(result["format"], "LGPE 1.0.2 zukan_sort u16le array")
        self.assertEqual(result["entry_count"], 4)
        self.assertEqual(result["entries"], [
            {"index": 0, "file_offset": 0, "value_u16le": 1, "raw_hex": "0100"},
            {"index": 1, "file_offset": 2, "value_u16le": 0x137, "raw_hex": "3701"},
            {"index": 2, "file_offset": 4, "value_u16le": 0x2ff, "raw_hex": "ff02"},
            {"index": 3, "file_offset": 6, "value_u16le": 0xffff, "raw_hex": "ffff"},
        ])
        self.assertEqual(bytes.fromhex(result["raw_hex"]), data)
        self.assertEqual(b"".join(bytes.fromhex(row["raw_hex"]) for row in result["entries"]), data)
        self.assertEqual(result["element_semantics"], "UNKNOWN")

    def test_zukan_sort_u16_array_rejects_odd_byte_count(self):
        decoder = getattr(gamedata_decode, "zukan_sort_data", None)
        self.assertTrue(callable(decoder), "exact-main zukan_sort u16 reader is not implemented")
        with self.assertRaisesRegex(ValueError, "even byte count"):
            decoder(b"\x01\x02\x03")

    def test_battle_pocket_preserves_indexed_bytes_and_numeric_projection(self):
        data = bytes((index * 11) & 0x1F for index in range(0x422))

        result = battle_pocket(data)

        self.assertEqual(result["format"], "LGPE battle_pocket.dat byte map")
        self.assertEqual(result["entry_count"], 0x422)
        self.assertEqual(result["entries"][1], {
            "item_index": 1, "raw_byte": data[1], "pocket_battle": data[1],
        })
        self.assertEqual(sum(result["pocket_battle_value_counts"].values()), 0x422)
        self.assertEqual(bytes.fromhex(result["raw_hex"]), data)

    def test_field_pocket_preserves_bytes_and_emits_pocket_field(self):
        data = bytearray((index * 37) & 0xFF for index in range(0x422))
        data[0] = 0x41
        data[1] = 0x86
        data[2] = 0x07

        result = field_pocket(bytes(data))

        self.assertEqual(result["format"], "LGPE field_pocket.dat byte map")
        self.assertEqual(result["entry_count"], 0x422)
        self.assertEqual(result["entries"][0], {
            "item_index": 0, "raw_byte": 0x41,
            "pocket_field": 1, "high_bit_set": False,
        })
        self.assertEqual(result["entries"][1], {
            "item_index": 1, "raw_byte": 0x86,
            "pocket_field": 6, "high_bit_set": True,
        })
        self.assertEqual(result["entries"][2]["pocket_field"], 7)
        self.assertEqual(sum(result["pocket_field_counts"]), 0x422)
        self.assertEqual(bytes.fromhex(result["raw_hex"]), bytes(data))
        self.assertEqual(bytes(row["raw_byte"] for row in result["entries"]), bytes(data))

    def test_field_pocket_rejects_wrong_table_length(self):
        for data in (bytes(0x421), bytes(0x423)):
            with self.assertRaisesRegex(ValueError, "0x422"):
                field_pocket(data)

    def test_ahtb_label_table_keeps_index_hash_and_original_label_bytes(self):
        data = (
            b"AHTB" + struct.pack("<I", 2)
            + struct.pack("<QH", 0x0123456789ABCDEF, 4) + b"A\0x\0"
            + struct.pack("<QH", 0xFEDCBA9876543210, 3) + b"B\0!"
        )
        result = tbl_labels(data)
        self.assertEqual(result["format"], "AHTB-label-table")
        self.assertEqual(result["entry_count"], 2)
        self.assertEqual(result["entries"][0], {
            "index": 0, "hash": "0123456789abcdef", "label_length": 4,
            "raw_label_hex": "41007800", "label": "A\0x",
        })
        self.assertEqual(result["entries"][1]["raw_label_hex"], "420021")

    def test_ahtb_rejects_wrong_magic_truncation_and_trailing_bytes(self):
        with self.assertRaisesRegex(ValueError, "truncated"):
            tbl_labels(b"AHTB")
        with self.assertRaisesRegex(ValueError, "magic"):
            tbl_labels(b"NOPE" + bytes(4))
        truncated = b"AHTB" + struct.pack("<I", 1) + struct.pack("<QH", 4, 3) + b"ab"
        with self.assertRaisesRegex(ValueError, "truncated AHTB label"):
            tbl_labels(truncated)
        trailing = b"AHTB" + struct.pack("<I", 0) + b"x"
        with self.assertRaisesRegex(ValueError, "length/count mismatch"):
            tbl_labels(trailing)

    def test_personal_rejects_incomplete_record(self):
        for data in [b"",bytes(83),bytes(85)]:
            with self.assertRaises(ValueError): personal(data)

    def test_personal_preserves_uninterpreted_bytes(self):
        data=bytes(range(84))*2
        result=personal(data)
        self.assertEqual(b"".join(bytes.fromhex(r["raw_hex"]) for r in result["entries"]),data)
        self.assertEqual(result["entries"][0]["FormStatsIndex"],0x1d1c)
        self.assertEqual(result["entries"][1]["index"],1)

    def test_pknx_item_properties_preserve_all_36_bytes(self):
        data=bytearray(range(0x24))
        result=item(data)
        p=result["properties"]
        self.assertEqual(p["BuyPrice"],0x0100*10)
        self.assertEqual(p["SellPrice"],0x0100*5)
        self.assertEqual(p["NaturalGiftType"],(0x0908&0x1F))
        self.assertEqual(p["PocketField"],(0x0908>>7)&0xF)
        self.assertEqual(p["PocketBattle"],0x0908>>11)
        self.assertEqual(bytes.fromhex(result["raw_hex"]),data)
        with self.assertRaisesRegex(ValueError,"0x24"):
            item(bytes(0x23))

    def test_pknx_trainer_data_header_fields_and_raw_bytes(self):
        data=bytearray(range(0x17))
        result=trainer_data_7b(data)
        p=result["properties"]
        self.assertEqual(p["Class"],0x0100)
        self.assertEqual(p["Mode"],2)
        self.assertEqual(p["NumPokemon"],3)
        self.assertEqual(p["Item1"],0x0504)
        self.assertEqual(p["AI"],0x0F0E0D0C)
        self.assertEqual(p["Gift"],0x1514)
        self.assertEqual(bytes.fromhex(result["raw_hex"]),data)
        with self.assertRaisesRegex(ValueError,"0x17"):
            trainer_data_7b(bytes(0x16))

    def test_pknx_trainer_party_iv_fields_and_raw_bytes(self):
        record=bytearray(range(0x28))
        record[0]=0x31
        record[0x10:0x14]=(0xE1234567).to_bytes(4,"little")
        data=bytes(record)*2
        result=trainer_poke_7b(data)
        p=result["entries"][0]["properties"]
        self.assertEqual((p["Gender"],p["Ability"]),(1,3))
        self.assertEqual(p["IV32"],0xE1234567)
        self.assertTrue(p["Shiny"])
        self.assertTrue(p["CanMegaEvolve"])
        self.assertEqual(bytes.fromhex(result["raw_hex"]),data)
        with self.assertRaisesRegex(ValueError,"multiple of 0x28"):
            trainer_poke_7b(bytes(0x29))

    def test_pknx_trainer_class_keeps_unnamed_tail_opaque(self):
        data=bytes(range(0x24))
        result=trainer_class_7b(data)
        self.assertEqual(result["properties"],{"Unk_0x00":0,"Group":1,"BallID":2,"Unk_0x03":3})
        self.assertEqual(result["opaque_tail_hex"],data[4:].hex())
        self.assertEqual(bytes.fromhex(result["raw_hex"]),data)

    def test_pknx_evolution_set_uses_signed_form_and_preserves_all_bytes(self):
        data=bytearray(range(0x40))
        data[6]=0xff
        result=evolution_set_7(data)
        first=result["entries"][0]["properties"]
        self.assertEqual(first,{"Method":0,"Argument":0x0302,"Species":0x0504,"Form":0,"Level":7,"HasData":True})
        self.assertEqual(bytes.fromhex(result["raw_hex"]),data)
        self.assertEqual(b"".join(bytes.fromhex(row["raw_hex"]) for row in result["entries"]),data)
        with self.assertRaisesRegex(ValueError,"0x40"):
            evolution_set_7(bytes(0x3f))

    def test_pknx_mega_evolution_preserves_unmapped_tail_and_bounds(self):
        data=bytes(range(16))
        result=mega_evolution_7(data)
        self.assertEqual(result["entries"][0]["properties"],{"ToForm":0x0100,"Method":0x0302,"Argument":0x0504})
        self.assertEqual(result["entries"][0]["opaque_tail_hex"],"0607")
        self.assertEqual(bytes.fromhex(result["raw_hex"]),data)
        with self.assertRaisesRegex(ValueError,"multiple of 8"):
            mega_evolution_7(bytes(9))

    def test_pknx_static_encounter_named_fields_and_raw_bytes(self):
        data=bytearray(range(0x40))
        result=encounter_static_7b(data)
        p=result["entries"][0]["properties"]
        self.assertEqual(p["Species"],0x0908)
        self.assertEqual(p["RelearnMoves"],[0x2120,0x2322,0x2524,0x2726])
        self.assertEqual(p["IV_HP"],44)
        self.assertEqual(p["UnknownFlag3F"],63)
        self.assertEqual(bytes.fromhex(result["raw_hex"]),data)
        with self.assertRaisesRegex(ValueError,"multiple of 0x40"):
            encounter_static_7b(bytes(0x41))

    def test_pknx_gift_encounter_retains_overlapping_class_views(self):
        data=bytearray(range(0x20))
        result=encounter_gift_7b(data)
        p=result["entries"][0]["properties"]
        self.assertEqual(p["Species"],0x0908)
        self.assertEqual(p["SpecialMove"],0x1110)
        self.assertEqual(p["IV_HP"],0x12)
        self.assertEqual(p["AV_HP"],0x18)
        self.assertEqual(p["RelearnMoves"],[0x1918,0x1B1A,0x1D1C,0x1F1E])
        self.assertEqual(bytes.fromhex(result["raw_hex"]),data)
        with self.assertRaisesRegex(ValueError,"multiple of 0x20"):
            encounter_gift_7b(bytes(0x21))

    def test_pknx_trade_encounter_signed_random_flags_and_raw_bytes(self):
        data=bytearray(0x58)
        data[0x0E:0x10]=(0x8000).to_bytes(2,"little")
        data[0x10:0x12]=(17).to_bytes(2,"little")
        data[0x1A:0x1C]=(0x4007).to_bytes(2,"little")
        data[0x26:0x28]=(0xFFFF).to_bytes(2,"little")
        data[0x28:0x2A]=(0xFFFF).to_bytes(2,"little")
        result=encounter_trade_7b(data)
        p=result["entries"][0]["properties"]
        self.assertEqual((p["IV_HP"],p["IV_ATK"]),(-1,17))
        self.assertEqual((p["AV_HP"],p["AV_HPRandUpTo"]),(7,True))
        self.assertEqual((p["Gender"],p["Nature"]),(0,-1))
        self.assertEqual(bytes.fromhex(result["raw_hex"]),data)
        with self.assertRaisesRegex(ValueError,"multiple of 0x58"):
            encounter_trade_7b(bytes(0x59))

    def test_pknx_move7_and_wd_binlinker_bounds(self):
        record=bytes(range(0x28))
        table_end=12
        data=b"WD"+struct.pack("<HII",1,table_end,table_end+len(record))+record
        result=move_data_7(data)
        properties=result["entries"][0]["properties"]
        self.assertEqual(result["identifier"],"WD")
        self.assertEqual(properties["HitMin"],7)
        self.assertEqual(properties["HitMax"],0)
        self.assertEqual(properties["Inflict"],0x0908)
        self.assertEqual(properties["Flags"],0x27262524)
        self.assertEqual(bytes.fromhex(result["raw_hex"]),data)
        bad=bytearray(data);bad[:2]=b"ZZ"
        with self.assertRaisesRegex(ValueError,"identifier"):
            move_data_7(bad)
        bad=bytearray(data);struct.pack_into("<I",bad,8,len(data)-1)
        with self.assertRaisesRegex(ValueError,"offset"):
            move_data_7(bad)

    def test_pknx_learnset6_pairs_and_trailing_word_preserve_bytes(self):
        data = struct.pack("<hh", 0x1234, 35) + struct.pack("<hh", -1, -1)
        result = learnset_6(data)
        self.assertEqual(result["format"], "LGPE Learnset6")
        self.assertEqual(result["entries"][0]["properties"], {"Move": 0x1234, "Level": 35})
        self.assertEqual(result["trailing_word_hex"], "ffffffff")
        self.assertEqual(result["trailing_word_signed"], -1)
        self.assertEqual(bytes.fromhex(result["raw_hex"]), data)
        with self.assertRaisesRegex(ValueError, "multiple of 4"):
            learnset_6(bytes(6))
        with self.assertRaisesRegex(ValueError, "at least 4"):
            learnset_6(b"")

    def test_message_rejects_header_and_line_bounds_before_external_import(self):
        with self.assertRaisesRegex(ValueError,"truncated"):
            message(bytes(12),b"",Path("missing"))
        data=struct.pack("<HHIIII IHH",1,1,12,0,16,12,100,2,0)
        with self.assertRaisesRegex(ValueError,"outside"):
            message(data,b"",Path("missing"))

    def test_flatbuffer_empty_archive_and_missing_vector(self):
        # Root=12, vtable at 4, root table at 12, empty vector at 20.
        data=struct.pack("<IHHHH iII",12,6,8,4,0,8,4,0)
        self.assertEqual(encounters(data)["tables"],[])
        bad=bytearray(data);struct.pack_into("<H",bad,8,0)
        with self.assertRaisesRegex(ValueError,"required"):
            encounters(bad)

    def test_flatbuffer_rejects_targets_and_vector_bombs(self):
        with self.assertRaises(ValueError): encounters(struct.pack("<I",0xffffffff))
        data=struct.pack("<IHHHH iII",12,6,8,4,0,8,4,100001)
        with self.assertRaisesRegex(ValueError,"vector"):
            encounters(data)
        with self.assertRaises(ValueError): FlatReader(bytes(4)).read("Q",0)

if __name__=="__main__": unittest.main()
