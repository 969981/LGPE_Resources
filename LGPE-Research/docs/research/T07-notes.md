# T07: actual LGPE sample decoding and cross-validation

Research updates: 2026-10-28–2026-10-29. Real source root: `../1.0.2/2b7730a9e56498bbafac2002d4908c6b_NCA/1/`.

References pinned locally:
- [pkNX](https://github.com/kwsch/pkNX/tree/d191cd0e5c05f2af81d9a41c1f1d82e6621b351a), commit `d191cd0e5c05f2af81d9a41c1f1d82e6621b351a`, GPLv3 LICENSE. No proprietary SDK needed. Source was read before build.
- `tools/src/pokedat`, commit `bd423b2cad9aa852fddb796bbba3c5e7b381289b`, GPL-3.0-only per upstream README/LICENSE. Imported as an external dependency, not vendored. Exact remote is recorded below.

Implementation: `src/lgpe_research/gamedata_decode.py`, schema `lgpe-gamedata-v1`. Decoders use bounds validation, reject conflicting outputs, isolate per-input failures, preserve raw bytes where applicable, and accept identical repeat runs. The `run_gamedata_batch` scheduler in `src/lgpe_research/batch.py` applies those decoders to actual source files with an explicit execute flag and hashes every source/output. Outputs retain source-relative hierarchy and stem and replace only the extension with `.json`. Sample evidence: `decoded/gamedata-sample-evidence.json`; independent checks: `work/gamedata-crosscheck/`.

Reproduction (Windows Python 3.13 used; .NET 10 SDK for cross-check):

Pokedat origin: `https://github.com/Digote/pokedat.git`.

```powershell
$P = 'X:\ROMS\Nintendo Switch\Pokemon\Pokemon Lets Go Pikachu\LGPE-Research'
uv run --project $P python -m lgpe_research.gamedata_decode --project $P # dry-run
uv run --project $P python -m lgpe_research.gamedata_decode --project $P --execute
dotnet build "$P/tools/src/pkNX/pkNX.Structures/pkNX.Structures.csproj" -c Release --nologo -v quiet
dotnet build "$P/tools/src/pkNX/FlatBuffers/LGPE/pkNX.Structures.FlatBuffers.LGPE.csproj" -c Release --nologo -v quiet
dotnet run --project "$P/scripts/gamedata-crosscheck/crosscheck.csproj" -c Release -- $P
uv run --project $P python -m lgpe_research.gamedata_validate --project $P
uv run --project $P python -m unittest discover -s "$P/tests" -p test_gamedata_decode.py -v
```

Initial result: **CROSS_VALIDATED for selected personal and both wild encounter archives**: personal 82,320 bytes = 980 entries × 0x54, both encounters 70 tables and 1,820 slots including padding. Three of three files decoded, zero errors. This was the first sample stage; later full game-data batches are recorded below.

Proof chain: `GameManagerGG.Initialize` selects `personal_total` and constructs `PersonalTable7GG`. `PersonalInfo7GG.SIZE=0x54` supplies field offsets and bitfields. The decoder preserves `raw_hex` for every complete record; concatenating these reproduces the exact source SHA-256. It exports only explicitly sourced offsets and leaves uninterpreted bytes in `raw_hex`. The upstream `PersonalTable7GG` contains base species up to 809 plus extra form records; 980 is a record count, not 980 in-game species. For valid nonzero forms, `IPersonalFormInfoExtensions.FormIndex` returns `FormStatsIndex + form - 1`, otherwise the base species record; `IsSpeciesInGame` permits species 1–151, 808, 809 (upstream also accepts dummy species 0). `IsPresentInGame` special-cases Pikachu form 8. No out-of-range form pointers in base records 0–809.

`EditorGG.PopWildEdit` uses `FlatBufferConverter.DeserializeFrom<EncounterArchive>`, selecting WildData1 for Pikachu and WildData2 for Eevee. The exact LGPE schema `FlatBuffers/LGPE/Schemas/wild.fbs` supplies 42 table fields: ZoneID ulong, trainer ranks, ground/water/rod/sky parameter groups, required slot vectors, and per-slot Probability int / Species int / Form short. File header `0c000000000006000800040006000000...` is a root offset/vtable layout, not an assumed universal BIN signature. Both versions are present even in this Pikachu extraction; no runtime version selection was changed.

The independent C# harness builds upstream `pkNX.Structures` and the LGPE FlatSharp 7.9.0 schemas, then invokes the same `PersonalTable7GG` and `FlatBufferConverter` used by the editor. **41,160 personal scalar/bitfield checks agree**, including EV yields, TMHM and tutor bits. **All fields and every slot in both encounter archives agree as whole objects**, including absent/default fields. Unexported personal fields (held item slots, Telekenesis bit, etc.) are retained as bytes and are not included in the count of compared named properties. Builds succeeded; structures 0 warnings/errors, shared FlatBuffers source emitted unused-constructor-parameter warnings only.

These are static tables. Encounter rates/slots do not prove PID, EC, shiny rolls, capture RNG or spawn timing behavior. Species 0 slots are padding/empty slots by source convention; retain them. No source ROM files were modified.

## Exact sample evidence

```json
[
  {
    "source": "bin/pokelib/personal/personal_total.bin",
    "tool_commits": {
      "pkNX": "d191cd0e5c05f2af81d9a41c1f1d82e6621b351a",
      "pokedat": "bd423b2cad9aa852fddb796bbba3c5e7b381289b"
    },
    "input_sha256": "0bd93e9122b1148f5ea844a5fe35334d17680430d9164bce799dd08f6cf3cddf",
    "input_bytes": 82320,
    "header_hex": "000000000000000000000000000000000000ff00000000000000000000000000",
    "count": 980,
    "status": "DECODED",
    "output": "decoded\\1.0.2\\romfs\\bin\\pokelib\\personal\\personal_total.json",
    "output_sha256": "80e4b1a7674146e07b864a1c48ac4101fce18bf9ab3306b049d80d2a1668ad9a",
    "output_bytes": 2143519
  },
  {
    "source": "bin/field/param/encount/encount_data_p.bin",
    "tool_commits": {
      "pkNX": "d191cd0e5c05f2af81d9a41c1f1d82e6621b351a",
      "pokedat": "bd423b2cad9aa852fddb796bbba3c5e7b381289b"
    },
    "input_sha256": "3dac771dffee508ff8fea41d255326640aefb67c88c2d96fd1ecda7b82b1ce46",
    "input_bytes": 27848,
    "header_hex": "0c0000000000060008000400060000000400000046000000006b00004c690000",
    "count": 70,
    "slot_count": 1820,
    "status": "DECODED",
    "output": "decoded\\1.0.2\\romfs\\bin\\field\\param\\encount\\encount_data_p.json",
    "output_sha256": "23e429a0470a356cffe44e323e8977db0e29c94c09937758676051980df077a2",
    "output_bytes": 269778
  },
  {
    "source": "bin/field/param/encount/encount_data_e.bin",
    "tool_commits": {
      "pkNX": "d191cd0e5c05f2af81d9a41c1f1d82e6621b351a",
      "pokedat": "bd423b2cad9aa852fddb796bbba3c5e7b381289b"
    },
    "input_sha256": "bea24bbbb4197681354e21f213cfde0148f9ea50cef60ef14ded333192fa80da",
    "input_bytes": 27848,
    "header_hex": "0c0000000000060008000400060000000400000046000000006b00004c690000",
    "count": 70,
    "slot_count": 1820,
    "status": "DECODED",
    "output": "decoded\\1.0.2\\romfs\\bin\\field\\param\\encount\\encount_data_e.json",
    "output_sha256": "c367918195863e36d8fe8ed8ce0943cc2383738cdeafa6bd3ea96f5a1db66bdd",
    "output_bytes": 269788
  }
]
```

## Quality and cross-check evidence

```json
{
  "personal": {
    "records": 980,
    "byte_exact_reassembly_sha256": "0bd93e9122b1148f5ea844a5fe35334d17680430d9164bce799dd08f6cf3cddf",
    "base_species_limit": 809,
    "form_index_out_of_bounds": []
  },
  "encount_p": {
    "tables": 70,
    "slots_including_padding": 1820,
    "nonzero_species_slots": 563,
    "species_range": [
      10,
      148
    ],
    "negative_probabilities": 0,
    "duplicate_zone_ids": 0
  },
  "encount_e": {
    "tables": 70,
    "slots_including_padding": 1820,
    "nonzero_species_slots": 563,
    "species_range": [
      10,
      148
    ],
    "negative_probabilities": 0,
    "duplicate_zone_ids": 0
  },
  "message_alignment": {
    "common/bag": {
      "same_ids_hashes": true,
      "replacement_character_lines": 0,
      "extra_labels": [
        {
          "id": "msg_bag_max",
          "hash": "1152562ed8b2b446"
        }
      ]
    },
    "script/master_trainer": {
      "same_ids_hashes": true,
      "replacement_character_lines": 0,
      "extra_labels": [
        {
          "id": "msg_master_trainer_max",
          "hash": "321bc2fb4a86bf1a"
        }
      ]
    }
  }
}
```

At the initial sample stage, five synthetic corruption/bounds/personal byte-reassembly cases passed. Malformed headers, invalid line offsets, incomplete personal records, missing required FlatBuffer vectors, oversized vectors, and invalid roots are rejected. The full expanded regression suite and final receipt checks are recorded below.

## Full item and trainer batch — 2026-10-29

The pinned pkNX source provides the format boundary and named properties. `EditorGG.EditItems` passes only exact 0x24-byte files to `Item.FromBytes`; `GameFileMapping.cs` maps trainer data, party slots, and trainer classes to the local `bin/trainer/{trainer_data,trainer_poke,trainer_type}/` paths; `EditorGG` selects `TrainerData7b`, `TrainerPoke7b`, and `TrainerClass7b`. The local Python decoder mirrors those fixed structures, preserves `raw_hex`, and is cross-checked against the pinned C# objects. Trainer `Mode` remains numeric because the upstream source marks its meaning unsure; unnamed trainer-class bytes stay opaque.

The item/trainer batch and later targeted additions used:

```powershell
uv run lgpe decode-gamedata --limit 2 --execute
uv run lgpe decode-gamedata --limit 20 --execute
uv run lgpe decode-gamedata --limit 0 --execute --sources-file docs/research/source_lists/t07-new-gamedata.txt
uv run lgpe coverage
uv run lgpe register-gamedata --sources-file docs/research/source_lists/t07-new-gamedata.txt
```

The first complete batch decoded all 5,380 paired messages and compatible fixed-size item/trainer records; its 8,029 decoded results were retained. The newer selected-source batch added all 1,964 files not covered by that batch: 980 evolution sets, 980 mega-evolution sets, three event encounter tables, and one move table. The final manifest contains **9,993 DECODED, 13 UNKNOWN, 0 FAILED, and 0 PENDING** rows (10,006 total). Decoded sources are 5,380 messages, three personal/wild encounter tables, one move table, 1,058 item records, 1,588 trainer records, 980 evolution sets, 980 mega-evolution sets, and three event encounter tables. The three item-folder files with other sizes remain UNKNOWN: `battle_pocket.dat`, `field_pocket.dat`, and `item_hash_to_index.dat`. The other ten UNKNOWN rows are nine grammar DAT files and `bin/message/asset.tbl` without a paired message DAT. Actual group counts:

| Source group | Catalogued | Decoded | UNKNOWN |
|---|---:|---:|---:|
| `bin/pokelib/item/*.dat` | 1,061 | 1,058 | 3 non-record data/index files |
| `bin/trainer/trainer_data/*.bin` | 602 | 602 | 0 |
| `bin/trainer/trainer_poke/*.bin` | 602 | 602 | 0 |
| `bin/trainer/trainer_type/*.bin` | 384 | 384 | 0 |
| `bin/pokelib/evolution/evo_*.bin` | 980 | 980 | 0 |
| `bin/pokelib/mega_evolution/mega_*.bin` | 980 | 980 | 0 |
| `bin/script_event_data/{event_encount,add_poke,field_trade_data}.bin` | 3 | 3 | 0 |
| `bin/pokelib/waza/waza_data.bin` | 1 | 1 | 0 |

All outputs are one-to-one `.json` path mirrors. Item records are exactly 36 bytes; trainer headers 23 bytes; trainer party data is a multiple of 40 bytes and every slot is retained; trainer class files are 36 bytes with only four named bytes and the remaining tail preserved opaque. Every item/trainer export checks `raw_hex` reassembly against the complete input and rehashes the source after conversion. The three item-folder files with other sizes remain UNKNOWN rather than being reinterpreted: `battle_pocket.dat`, `field_pocket.dat`, and `item_hash_to_index.dat`. The other ten UNKNOWN rows are nine grammar DAT files without label tables and `bin/message/asset.tbl` without a paired message DAT.

Independent C# parity used the pinned `pkNX.Structures` classes on actual item/trainer files `{001,002}`. The comparer reported **CROSS_VALIDATED, 0 mismatches** across 50 properties per item, 13 trainer-header fields, 36 trainer-party fields per slot, and four named trainer-class fields. Additional actual output comparisons reported **CROSS_VALIDATED, 0 mismatches** for `EvolutionSet7` and `MegaEvolutionSet` (`evo_001/002`, `mega_001/002`); the 10 static rows (39 mapped properties), 16 gift rows (22 properties) and 10 trade rows (42 properties); and all 743 `Move7` records (35 properties each). Reproduce with `dotnet run --project scripts/gamedata-crosscheck/crosscheck.csproj -c Release -- <project>` followed by `python scripts/gamedata-crosscheck/verify_pknx_trainer_item.py`, `verify_pknx_evolution.py`, `verify_pknx_encounters.py`, and `verify_pknx_moves.py`.

Representative receipt hashes from the actual batch:

| Source | Source SHA-256 | JSON SHA-256 |
|---|---|---|
| `bin/pokelib/item/item001.dat` | `183b1f9aff6512ac2fd9cc6e4cea9f72b7c7bb84caba082319a824326e6362aa` | `4eeba3a1bfebee7cd0029488e15cb56b86cdbf395a4a96eac255206bcc18f005` |
| `bin/trainer/trainer_data/trainer_data_001.bin` | `8fab8d07e7d90f1450b1b45e1552f70a34e671ee18f1e33e77e5106d567c9688` | `114eb6bc49a976d0807e7e07ec035ef269acd92e4be8e00f14c73ed8bdb488ea` |
| `bin/trainer/trainer_poke/trainer_poke_001.bin` | `242cd0575860b0506931d22ebeb706db5cce70166a395aa89a43967a035292dd` | `6dfb1292509eabcf7958a2cf0113e4a75098c079de6c96262055d723d4cd3ab6` |
| `bin/trainer/trainer_type/trainer_type_001.bin` | `53653412046aa16ed8073689f47396b90a3d1834d6402bda29c71ee7c131858f` | `8e89a73d3d2b79474c5f9b0fa17aacd2e824ce8f11d2150aec5d2cfe0b88bba3` |

All 51 unit tests passed after these decoder and source-list CLI changes. At this checkpoint, before the later T08 R16 retry and following additions, the source-wide coverage report read **SCANNED 27,824; DECODED 20,991; FAILED 1; UNKNOWN 6,755; PENDING 0; UNSUPPORTED 77; 73,715 output receipts**. The global receipt audit checked 71,751/71,751 outputs with `bad=0`; the additional 1,964 game-data outputs were independently rehashed with no failures. Together these checks covered all 73,715 then-registered outputs.

At that earlier batch checkpoint, `waza_oboe.gfpak` learnset members had not yet been decoded. The following section records the later completed batch. `TrainerData7b.Mode` semantics and trainer-class tail bytes remain unassigned; message end-label semantics and unusual text controls need further study. These outputs do not establish encounter RNG, PID/EC, shiny rolls, capture behavior, or trainer runtime behavior.

At that checkpoint, the pinned-tool harness used .NET 10; the WSL session did not yet expose `X:` as `/mnt/x`. The current WSL session exposes the source through `/mnt/x` over 9P; the GameManagerGG CLI detects Windows `dotnet.exe` and uses native Windows paths for the full source hash audit.

## Evolution, move, and event encounter batch — 2026-10-29

The pinned `GameManagerGG`/`EditorGG` mappings and corresponding pkNX classes identify the consumed records. The `evo_*.bin` files are exactly 0x40 bytes (eight `EvolutionSet7` entries); the `mega_*.bin` files are 16 bytes (two 8-byte `MegaEvolutionSet` entries). The WD BinLinker at `bin/pokelib/waza/waza_data.bin` contains 743 entries of 0x28 bytes, parsed through pkNX `Move7`. `EditorGG.EditStatic`, `EditGift`, and `EditTrade` select the three event files. These class/property names come from the pinned source, not the resource-tree labels.

| Source | Bytes / records | Source SHA-256 | One-to-one JSON output | Output SHA-256 |
|---|---:|---|---|---|
| `bin/pokelib/evolution/evo_001.bin` | 64 / 8 | `1890836ad54a94b5426b0fbe51d25154b245a76b81c146570230f8d489db7887` | `bin/pokelib/evolution/evo_001.json` | `688e07635eb5ca8da8cda46fc4aae68a78d3821a9eb29a74d5f58b2f08144803` |
| `bin/pokelib/mega_evolution/mega_001.bin` | 16 / 2 | `374708fff7719dd5979ec875d56cd2286f6d3cf7ec317a3b25632aab28ec37bb` | `bin/pokelib/mega_evolution/mega_001.json` | `10041616c64d33c06c483eacf108d5a3514f6c120f1fd473c67a283c7ec27d77` |
| `bin/script_event_data/event_encount.bin` | 640 / 10 | `2bbe6321c8c25dd75ed5d11db81fa4077bd513081c0c77d72b6574874ff5e814` | `bin/script_event_data/event_encount.json` | `2f4c59c422f832cf74d3c13d1ee50c50dc3a07a5eec397209970d646e5e2d4eb` |
| `bin/script_event_data/add_poke.bin` | 512 / 16 | `465db539a6a218023e6557f86531f29a1676df00d0fdbbd8666927a547c05d18` | `bin/script_event_data/add_poke.json` | `bbb56cf008dca5f8fda11690bb80d551fcae90668bbdad05fc06a22d26ae18f1` |
| `bin/script_event_data/field_trade_data.bin` | 880 / 10 | `3dfd4721c9bf7f6be235a7726c7a2d8cd3bb327c5a76982268e5199af8b07830` | `bin/script_event_data/field_trade_data.json` | `13d501372e10f0701e05bdf4622bef6703a2fd4c2ec3069477d3375ed96d65d8` |
| `bin/pokelib/waza/waza_data.bin` | 32,700 / 743 | `a917be5dfc325171b759d449d6acac894950828e932f639a98b1190afe979bfd` | `bin/pokelib/waza/waza_data.json` | `199e276fd97893c7da33940c2c0ff44111da1091a8605eb9466731f2468d62bd` |

Raw bytes are retained in each JSON and every input was checked for exact byte reconstruction during conversion. The new one-to-one outputs replace only `.bin` with `.json`; stems and relative paths are unchanged. `EvolutionSet7` applies the pkNX negative-form clamp while retaining original raw bytes; the final two bytes of each mega-evolution entry remain opaque. Static encounter pointer fields retain the uncertain labels from pkNX comments. Gift AV and relearn-move getters overlap in the upstream class, so both views are exported. Trade UVs and move enum values remain numeric without invented semantics. No runtime behavior is inferred from these records.

The first unfiltered rerun was stopped before completion because it reprocessed the already verified 5,380 messages before reaching the newly added families. The CLI now accepts `--sources-file` for an explicit, newline-separated source list (UTF-8 or UTF-8-BOM, blank lines and `#` comments ignored). The tracked `docs/research/source_lists/t07-new-gamedata.txt` selects exactly 1,964 new sources: 980 evolution sets, 980 mega-evolution sets, three event encounter files, and the WD move table. The targeted CLI run completed with 1,964 DECODED and 0 FAILED. Targeted registration then independently rehashed all 1,964 source/output pairs with `verified=1964`, `failed=0`; the unique receipt count is 73,715. Four C# comparison scripts for the actual decoded outputs each reported `CROSS_VALIDATED` and zero mismatches.

## Battle AI `.amx` classification attempt

The scan found seven files under `bin/battle/ai_script/`. All seven begin with a
little-endian 32-bit value equal to the full file size, followed by the stable
bytes `e1f10a0a`; the remaining header bytes have not been mapped.
For example, `btl_ai_basic.amx` is 32,742 bytes and starts
`e67f0000e1f10a0a04000c0070000000`. SHA-256 values and exact headers for all
seven are in the source scan and can be regenerated with:

```powershell
uv run python -c "from pathlib import Path; from lgpe_research.core import PROJECT,source_dirs,sha256; root=source_dirs(PROJECT.parent)['romfs']; [print(p.relative_to(root).as_posix(),p.stat().st_size,p.read_bytes()[:16].hex(),sha256(p)) for p in sorted((root/'bin/battle/ai_script').glob('*.amx'))]"
```

The pinned local pkNX/Switch-Toolbox/read_swsh/pokedat source search found no
LGPE AMX bytecode parser; pkNX has only a SwSh `ScriptMeta` schema carrying a
`PathAMX` string. That is a path reference from another title, not evidence for
this VM or its instructions. Exact-build Ghidra work below later identified a
custom AMX-like parser in LGPE 1.0.2 `main`; this supersedes the earlier
conclusion that no local parser had been found. The public CompuPhase Pawn
source remains a comparison reference only, not the decoder used here.

### Read-only AMX header catalog — 2026-10-29

Added `uv run lgpe amx-catalog`, which uses the existing `manifests/files.csv`
as its source list (and a small observed-directory fallback when no scan
manifest exists). For the exact xref-confirmed `bin/archive/script_amx.gfpak`,
it also consumes `manifests/archives.jsonl` and reads only the extracted member
paths under `<archive>.contents/`; it rechecks the container and member hashes
before parsing. The ignored `manifests/amx_headers.jsonl` now contains **712
catalog entries: 7 loose RomFS files + 705 GFPAK members, 712 header
candidates, 712 static header-gate passes, 0 body DECODED, 0 FAILED, and 712
UNKNOWN bodies**. These are AMX catalog rows, not 712 new source-level UNKNOWN
files: the GFPAK itself remains one decoded archive source. Every row carries
the path, source size and SHA-256, raw 60-byte header, parsed fields, source
build identity and `body_status: UNKNOWN`. All 705 member outputs matched their
container manifest sizes and SHA-256 values; no source or decoded member was
modified. The source-wide coverage remains unchanged because no bytecode body
was decoded.

All 712 catalog entries have `magic=0xf1e1`, `file_version=10`,
`amx_version=10`, `defsize=12`, and a `size` field equal to their physical
length; every `hea` value exceeds the physical file size. Flags are `0x04` on
the seven loose files, `0x1c` on 703 GFPAK members, and `0x14` on two members.
In the official
CompuPhase Pawn source pinned at
`db97293fa949d7627272a1c8d7a9470818bdbe91` (Apache-2.0), `0xf1e1` is
`AMX_MAGIC_64`; `AMX_FUNCSTUB` is two `uint32_t` fields (8 bytes), and
`amx_Init` returns `AMX_ERR_FORMAT` if `defsize` differs from that structure.
It also asserts `hea == size` in that implementation, while the LGPE samples'
`hea` is greater than their physical `size`. Thus the standard pinned runtime
is not a verified decoder for these files. The official header source is
`tools/src/pawn/amx/amx.h`, and its check is in `tools/src/pawn/amx/amx.c`;
the manifest records the exact commit. This comparison does not override the
game's own parser evidence below.

### Exact-build Battle AI loader and AMX header gate — 2026-10-29

Read-only Ghidra 12.2 analysis used the local ExeFS `main` with SHA-256
`1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8` and image
base `0x7100000000`. The newly tracked scripts are
`scripts/ghidra/InspectAmxLoaderStrings.java`,
`scripts/ghidra/InspectAmxLoaderFunctions.java`,
`scripts/ghidra/InspectAmxResourceHelpers.java`, and
`scripts/ghidra/InspectBattleAiTable.java`. The successful local script/app
logs are ignored under `logs/ghidra-amx-*-v5-*.log`; rerunning the command
below recreates them from the saved Ghidra project.

The string `bin/archive/script_amx.gfpak` at `0x7100eff9c5` has a code
reference at `0x7100178ee4` in `FUN_71001783e0`; this establishes the exact
build's resource path and loader chain for the archive. The seven-file AI
table at `0x71015d2c00` contains `bin/battle/ai_script/*.amx` paths.
`FUN_7100a71bf0` (`0x7100a71bf0`) bounds the selected index to `< 7`,
selects the path, calls the resource path helpers at `0x710000b660` and
`0x7100135890`, and requests the resource object through `0x71000a63a0`.
`FUN_7100a71d70` (`0x7100a71d70`) takes the loaded buffer at object offset
`+0x170` and byte length at `+0x160`, then calls `FUN_7100a771d0`
(`0x7100a771d0`). That wrapper reaches `FUN_71006749b0` (`0x71006749b0`),
which copies the input and calls the header parser `FUN_710066fb20`
(`0x710066fb20`), followed by additional AMX validation and name resolution
helpers. `FUN_7100670450` resolves names from a supplied table; this static
trace does not establish which script commands execute at runtime.

The decompiled header gate at `FUN_710066fb20` checks magic `0xf1e1`,
`file_version <= 10`, `amx_version >= 6`, positive `stp`, and either
`defsize == 0x1c` or `defsize == 0x0c` with the 16-bit value at the
`nametable` offset `< 0x40`. It then takes a separate branch when flag bit
`0x04` is set. The catalog records that bit without labeling its transform as
a known compression scheme. These are conditions recovered from this exact
binary, not a claim that the game was executed.

All seven loose files have `magic=0xf1e1`, versions `10/10`, `defsize=12`,
`flags=4`, and name-table length 63. The 705 extracted GFPAK members also all
pass the same static gate; their individual flags and name-table lengths are
preserved in the manifest. Five actual members selected from the beginning of
the container demonstrate the retained index, internal path and hash:

| Index | Internal path | Bytes | Member SHA-256 |
|---:|---|---:|---|
| 0 | `A830472B45868B06/37A21F6E58876C11` | 5,008 | `87f593473ae99bd6d96a843452eca58f5f8d1a878a10d78a625fb24c5801f470` |
| 1 | `A830472B45868B06/12245350323FE3D3` | 268 | `4f1c8b50b954b66a16dde9c2d56a7cce8296d4e4177ac0bf29403357d6bc9e3f` |
| 2 | `A830472B45868B06/97A90E8E0F70BA93` | 6,298 | `d400e84f824b105e2bdf6756735478224c7214d00eb1ca8c6e290fa9f4abb820` |
| 3 | `A830472B45868B06/4EBC59F44BA52A29` | 1,838 | `6d9ad2105f03697f3f534ce32c8e0d1000b3f9e09facba0e3fe72f9f48d8b062` |
| 4 | `A830472B45868B06/6FE508C5CE01097E` | 6,376 | `fd8a90bcb0e0b40d791444dc11052881182882ca4dacf096b48ee54ca09d1a2b` |

The source GFPAK SHA-256 is
`99611f8c3bdd53ba7e6272cc5ed101157f4e16a30d556d16144a5d290273f77c`. The
Windows-native `uv run lgpe amx-catalog` completed with
`scanned=712`, `loose_scanned=7`, `archive_member_scanned=705`,
`header_candidates=712`, `static_header_pass=712`,
`static_header_reject=0`, `decoded=0`, `failed=0`, and `unknown=712`.
Manifest rows preserve each archive member as
`bin/archive/script_amx.gfpak.contents/<internal path>` plus its original
container index and source/container hashes.

Reproduction from the project root on the local Windows/Ghidra host:

```powershell
cmd.exe /c "D:\Tool\ghidra\ghidra_12.2_PUBLIC\support\analyzeHeadless.bat work\ghidra-main\project LGPE102-main -process main -noanalysis -scriptPath scripts\ghidra -postScript InspectBattleAiTable.java -scriptlog logs\ghidra-amx-battle-ai-table-script.log -log logs\ghidra-amx-battle-ai-table-app.log"
```

Then regenerate the local catalog and check the repository regression suite.
On Windows/PowerShell, run:

```bash
uv run lgpe amx-catalog
uv run lgpe plan
uv run python -m unittest tests.test_amx_catalog -v
```

For direct WSL commands on this mapped drive, keep Linux uv's environment
outside the Windows project `.venv`:

```bash
UV_PROJECT_ENVIRONMENT=/tmp/lgpe-research-wsl-venv UV_LINK_MODE=copy uv run lgpe amx-catalog
UV_PROJECT_ENVIRONMENT=/tmp/lgpe-research-wsl-venv UV_LINK_MODE=copy uv run python -m unittest tests.test_amx_catalog -v
```

The tracked `scripts/Start-Research.sh` sets this WSL environment by default.
Using the temporary environment prevents Linux uv from replacing the Windows
`.venv`; it does not touch the game dump.

`pawndisasm` was not built or run: this WSL image has no `cmake` or C compiler,
Docker's daemon is not running, and non-interactive `sudo apt-get` requires a
password. More importantly, the pinned standard Pawn header check already
rejects the observed record size, so running its disassembler would not
establish LGPE compatibility. This is a documented format boundary, not a
failed LGPE sample decode.

The source fetch helper now includes Pawn and has a WSL entry point. Running
`bash scripts/Fetch-Tool-Sources.sh` completed and refreshed
`tools/source-revisions.tsv` from local Git checkouts. The focused AMX suite
passed **9/9**, including the seven loose actual samples, archive-member
provenance and static-gate boundary cases. This host's Windows PATH
does not include Git, so the PowerShell source-fetch entry point exits with a
clear instruction to use the WSL script; no source revision list was truncated
by that preflight. Reproduce the catalog and plan refresh
from the repository root:

```bash
uv run lgpe amx-catalog
uv run lgpe plan
```

The Windows-native `uv run lgpe amx-catalog` reported `scanned=712`,
`header_candidates=712`, `static header PASS=712`, `decoded=0`, `unknown=712`,
`failed=0`; `uv run lgpe plan` refreshed all **27,824** plan rows.

## `waza_oboe.gfpak` learnset decoding — 2026-10-29

The pinned pkNX mapping identifies `bin/archive/waza_oboe.gfpak` as the
`Learnsets` archive consumed by `GameManagerGG`. `GameManagerGG` constructs
`Learnset6` objects for its members. In the pinned `Learnset6.cs`, complete
four-byte records are signed little-endian `Move` and `Level` Int16 values; the
final Int32 `-1` (`FFFFFFFF`) is written as the terminator. These are parser
fields from that source implementation; this batch does not assign additional
gameplay semantics to them.

The local archive SHA-256 is
`ed4c338d32f857016e8978fd888239c7505b9e8c6a8bdef754aed62c0b145647`. All 980
extracted members have lengths divisible by four and end in `FFFFFFFF`. The
batch decoded all 980 members to JSON next to each unchanged raw member under
`decoded/1.0.2/romfs/bin/archive/waza_oboe.gfpak.contents/`, preserving their
two-component hashed internal paths and container indexes. Each receipt binds
the source archive, internal path, index, extracted member SHA-256, and JSON
SHA-256. The source archive was rehashed after execution and remained unchanged.

| Container index | Internal path | Bytes / entries | Member SHA-256 | JSON SHA-256 |
|---:|---|---:|---|---|
| 1 | `094C9B49A1A93A8E/35DAE0B7C2C7428A` | 44 / 10 | `d823b9eff4b58b684527cec6e08ecac828d0d4b63c68e8ba2d44f92085ea847c` | `e5ae2bcbfce56c92c9afc0eaf0167628886241d8b2a3639d1010e3b3f4401e11` |

The complete output contains **15,380 Move/Level entries**. The pinned pkNX
C# harness exports every `Learnset6` object, including raw bytes and its
round-trip serialization. `verify_pknx_learnsets.py` compared all 980 Python
outputs against those records and reported `CROSS_VALIDATED`, with 0 mismatches
for Move values, Level values, entry counts, raw bytes, terminators, and
round-trips. The exact pkNX source commit is
`d191cd0e5c05f2af81d9a41c1f1d82e6621b351a`.

The real execution was advanced through `--limit 2`, `--limit 20`, and
`--limit 0`; final counts are 980 DECODED, 0 FAILED, 0 UNKNOWN, and 0 PENDING.
The targeted command
`uv run lgpe verify --sources-file docs/research/source_lists/t07-learnsets.txt`
checked 1,960 outputs (both the extracted members and their JSON counterparts)
with `bad=0` and an empty error list. It exits 5 because its summary also counts
the pre-existing global failure ledger (`failed_or_unsupported=79`), not due to
receipt mismatches. Reproduce the cross-check by running
`dotnet run --project scripts/gamedata-crosscheck/crosscheck.csproj -c Release`
then `python scripts/gamedata-crosscheck/verify_pknx_learnsets.py`.

The `uv run lgpe decode-learnsets --limit N --execute` command preserves all
previous per-member manifest results outside the selected range. The tracked
`docs/research/source_lists/t07-learnsets.txt` selects this exact archive for
targeted verification and retry. The expanded unit suite includes decoder,
container path/hash, source-selection, and coverage receipt-count checks.

## Headless GameManagerGG batch cross-check — 2026-10-29

The new .NET 10 worker in `scripts/gamemanagergg-worker/` uses the pinned
`GameManagerGG` mapping and record classes on the actual LGPE 1.0.2 `0/` and
`1/` paths. Its read-only subclass disables `FileMitm.SetRedirect`; no write
method is called. Output is isolated under ignored `work/gamemanagergg/` and is
used only as an independent reference for the production JSON mirrors.

Reproduce from the project root:

```powershell
.\scripts\Crosscheck-GameManagerGG.ps1
uv run python scripts/gamedata-crosscheck/verify_gamemanagergg_worker.py . `
  'work/gamemanagergg/run-20261028T220208Z'
```

In WSL, set the uv project environment outside the mapped drive when invoking
manually, then use the same command with `--root` set to the WSL-visible game
directory. The CLI converts arguments to Windows paths when it selects native
Windows .NET from PATH.

The completed run emitted 980 personal records, 743 move records, 980 learnset
members (15,380 Move/Level pairs), 980 evolution files, and 980 mega-evolution
files (1,960 entries). All **1,963** mapped source files have complete
before/after SHA-256 lists in the worker receipt and remained identical. The
independent verifier reported **4,663 raw-byte comparisons, zero mismatches**
against the path-mirrored production JSON. The learnset worker output keeps
`internalPath: null` / `UNKNOWN_HASH_ONLY`, and retains the pack member index,
absolute path hash, compression metadata and raw bytes; the production
container decoder continues to provide its verified hashed internal paths.
The PowerShell 7 wrapper also completed a native Windows run at
`work/gamemanagergg/run-20261028T220208Z/`; its independent verifier returned
the same 4,663/4,663 `CROSS_VALIDATED` result. The wrapper adds `.EXE` to
`PATHEXT` because this host's PowerShell environment exposes only `.CPL`, which
otherwise prevents the FlatSharp build target from locating `dotnet.exe` by
name.

Personal (980), moves (743), learnsets (980), and mega-evolution (980) all
round-tripped exactly through pkNX. Evolution `Write()` round-tripped 620/980
files. The other 360 are expected parser normalization: `EvolutionSet7`
clamps negative signed form bytes to zero. Their source bytes remain in
`rawHex`, and the production schema uses the same pinned-source rule. These
normalization differences are not counted as source or export mismatches.

This worker does not change the game-data manifest coverage: it adds a
repeatable reference parser and a full raw-byte parity audit, not another
production conversion.

## Actual AMX compact-cell decoding — 2026-10-29

The earlier header-catalog state above is historical: its `body_status:
UNKNOWN` values were superseded by the completed decoder batch below. Static
Ghidra analysis of the exact local Let's Go Pikachu 1.0.2 ExeFS `main` (SHA-256
`1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8`, image
base `0x7100000000`) identified the parser at `0x710066fb20` and code validator
at `0x710066ff20`. The implementation in
`src/lgpe_research/amx_decode.py` reads signed big-endian 7-bit continuation
groups into 64-bit cells, then mirrors the validator's opcode/operand
consumption, code/data/stack bounds, branch/switch target bounds, and
callback-null rejection. Its two-cell instruction table was recovered from
the validator's exact-build decompilation; adding the initially omitted
two-cell opcodes corrected false rejections from the first prototype. The
upstream Pawn revision is only a header/cell-format comparator and is not used
as LGPE execution evidence or as the decoder.

Before any `--execute` batch, the command hashes the actual local
`1.0.2/<NCA>/0/main` and refuses to decode if the file is missing or its SHA-256
differs from the exact-build value above. The current local file was rehashed
after the run and still matches.

The JSON export contains decoded code/data cell values and instruction
boundaries with cell/byte offsets and opcode numbers. It does not execute VM
instructions, resolve command names, or claim battle behavior, and source
bytes remain unchanged. The game validator's passing result supports this
bounded structural decode for the listed local inputs; it is not a general
AMX/Pawn compatibility claim.

The Windows-native batch command
`cmd.exe /c "D:\SDK\uv-x86_64-pc-windows-msvc\uv.exe run lgpe decode-amx --execute"`
reprocessed all **712/712** catalog rows: 7 loose scripts and 705 extracted
members of `bin/archive/script_amx.gfpak`, with **712 DECODED, 0 FAILED, 0
UNKNOWN**. It emitted 949,074 cells and 484,241 instruction-index rows. The
member decoder rechecks the archive/member hashes and preserves index and
internal path. For example, container index 0 at
`A830472B45868B06/37A21F6E58876C11` (5,008 bytes; member SHA-256
`87f593473ae99bd6d96a843452eca58f5f8d1a878a10d78a625fb24c5801f470`) maps to
`decoded/1.0.2/romfs/bin/archive/script_amx.gfpak.contents/A830472B45868B06/37A21F6E58876C11.json`;
the JSON is 165,662 bytes with SHA-256
`861013a0413bfc129801819bf387460cad35805012e8bc1855fccc97b7538e33`. Its
catalog row records index 0, original internal path, source hash, container
hash, output path and output hash.

The loose sample `bin/battle/ai_script/btl_ai_basic.amx` (32,742 bytes; SHA-256
`638cded5e75523c0c75a75fc55af07a6b0844e51e81fcf9093755112c6c2f31c`) maps to
`decoded/1.0.2/romfs/bin/battle/ai_script/btl_ai_basic.json` (2,531,690 bytes;
SHA-256 `1873d1c3d7aa4a54611846b2225ac9c7171486ff607d35f0b76c8e6d161ab3e7`).
That row records 24,474 decoded cells and 13,575 instruction boundaries.

Receipt verification rehashed **1,410/1,410** receipts associated with the
archive (705 extracted raw members plus 705 JSON outputs) and **7/7** loose
source/output receipts; both runs reported `bad=0`, `failed=0`, and
`errors=[]`. Reproduce with the tracked source lists:

```powershell
uv run lgpe decode-amx --limit 8 --execute --sources-file docs/research/source_lists/amx-smoke.txt
uv run lgpe decode-amx --execute
uv run lgpe verify --sources-file docs/research/source_lists/amx-archive.txt
uv run lgpe verify --sources-file docs/research/source_lists/amx-loose.txt
uv run lgpe coverage
uv run python -m unittest discover -s tests -q
```

The focused AMX/catalog/receipt tests pass **22/22** under Windows and WSL; the
complete suite passes **99/99** under both environments.

After this batch, source-wide coverage is **SCANNED 27,824; DECODED 21,075;
FAILED 1; UNKNOWN 6,748; PENDING 0; UNSUPPORTED 0; 77,696 registered output
receipts**. The one failure remains the independently recorded Blender model
crash. Only the seven loose `.amx` files are source-level rows; the 705 script
members are children of the already decoded GFPAK source. `tasks/INDEX.md` and
`docs/research/STATUS.md` contain the current task and coverage summaries.

## `field_pocket.dat` exact-build byte-map decode — 2026-10-29

The prior UNKNOWN classification for the non-`0x24` item-folder DAT files was
appropriate before a matching reader was established. A SHA-guarded Ghidra
12.2 pass against the local Let's Go Pikachu 1.0.2 ExeFS `main` (base
`0x7100000000`, SHA-256
`1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8`) now
provides a narrow decoder basis for `bin/pokelib/item/field_pocket.dat`:

- `FUN_710073b950` at `main+0x73b950` constructs a resource name ending in
  `field_pocket.dat` and passes it to `FUN_71001d88b0`.
- Its only direct caller is `FUN_710071cec0` at `main+0x71cec0`. That function
  requests the resource through `FUN_71000adc70`, reads a byte count from the
  returned object at `+0x160`, and copies from its data pointer at `+0x170` to
  the global slot at `0x710163ea48`.
- The slot is in the uninitialized `.bss` block in Ghidra, so the bytes are not
  recoverable from the static `main` image. The exact local RomFS source is
  1,058 (`0x422`) bytes with SHA-256
  `07a1d8da834d426c8de16f3c4bd7d28307bc86a9e217ebf5170b09316797402b`.
- `FUN_710071d1b0` bounds the item index below `0x422` and reads the
  corresponding byte masked with `0x07`; `FUN_710071d210` performs a signed
  byte check at the same index. The low-three-bit field is now independently
  cross-validated as pkNX GameManagerGG `Item.PocketField` for all 1,058
  records from this exact RomFS tree. Human-readable pocket labels are not
  asserted, and the meaning of bit 7 remains unassigned.

Added `field_pocket()` in `src/lgpe_research/gamedata_decode.py` and a dedicated
path group in `src/lgpe_research/batch.py`. It exports 1,058 indexed records,
each preserving the original byte, validated numeric `pocket_field`, and
observed high-bit view; concatenating the bytes or top-level `raw_hex`
reproduces the input exactly. The real `pocket_field` counts are
`[23, 60, 99, 8, 14, 24, 53, 777]` and 193 bytes have bit 7 set. No
human-readable pocket names or bit-7 meaning are assigned.

The real batch command, restricted by the tracked one-source list, was:

```sh
UV_PROJECT_ENVIRONMENT=/tmp/lgpe-research-env uv run lgpe decode-gamedata --root .. --sources-file docs/research/source_lists/field-pocket-1.txt --execute
UV_PROJECT_ENVIRONMENT=/tmp/lgpe-research-env uv run lgpe verify --root .. --sources-file docs/research/source_lists/field-pocket-1.txt
UV_PROJECT_ENVIRONMENT=/tmp/lgpe-research-env uv run lgpe coverage
"/mnt/c/Program Files/dotnet/dotnet.exe" run --project scripts/gamedata-crosscheck/crosscheck.csproj -c Release -- field-pocket-crosscheck .
```

The batch decoded **1/1 selected** source with zero failures. Receipt
verification reported `registered=1`, `verified=1`, `bad=0`, `failed=0`. The
one-to-one output is
`decoded/1.0.2/romfs/bin/pokelib/item/field_pocket.json`, SHA-256
`91afa237944aa961b959dc4f46c507ffda45f475d9fe161295661e8b1e91436a`; the
source and JSON hashes match `manifests/gamedata.jsonl` and
`manifests/outputs.jsonl`. The initial rerun safely rejected the prior export with its older
`selector_code` field as a conflict. After verifying its exact source round-trip
and both hashes, only that derived JSON was removed and regenerated; the
extracted source was not modified. Receipt verification then reported
`registered=1`, `verified=1`, `bad=0`, `failed=0`.

The pinned pkNX cross-check command above reads the exact-build `main`, the
`field_pocket.dat` table, and `item000.dat` through `item1057.dat`. It compares
the JSON indices, bytes, and `pocket_field` values against
`Item.FromBytes(...).PocketField` from pkNX commit
`d191cd0e5c05f2af81d9a41c1f1d82e6621b351a`; result: **1,058 compared, 0
mismatches**. It guards the `main` hash
`1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8` and
source hash `07a1d8da834d426c8de16f3c4bd7d28307bc86a9e217ebf5170b09316797402b`.
The ordered concatenation of `item000.dat`–`item1057.dat` is also guarded by
SHA-256 `c15d85a4aba08aeebdceace89ba5344cd9c5068bef78cc6f448115f462f64e0f`.
This validates the numeric field mapping; it does not name pocket categories
or bit 7.

At this point in the T07 sequence, the game-data manifest had 10,009 DECODED
and 11 UNKNOWN sources. The later `battle_pocket.dat` value-level check and
decode are recorded below.

## `item_hash_to_index.dat`: earlier SWSH parser probe — 2026-10-29

This section records the state before the exact-build Ghidra follow-up at the
end of this file. Its `UNKNOWN` status and negative raw-string scan are
superseded there.

The exact LGPE 1.0.2 source is 16,740 bytes, SHA-256
`a9050fef634aa1bc2dfe34cd48781bc6357498f05133e2ac63a463be2b5f9fc0`. The
pinned pkNX `ItemHash8.GetItemHashTable` source (`tools/src/pkNX/pkNX.Structures/Item/ItemHash8.cs`,
commit `d191cd0e5c05f2af81d9a41c1f1d82e6621b351a`, GPL-3.0) reads a 32-bit
little-endian count followed by 16-byte rows. The `item_hash_to_index.dat`
mapping belongs to `FilesSWSH`, and `EditorSWSH.cs` is its only source call;
this does not establish an LGPE consumer or semantics.

The new `scripts/gamedata-crosscheck/crosscheck.csproj` mode
`itemhash-probe <source>` invokes that actual C# parser on the extracted LGPE
sample. The command exited 0 and wrote `work/itemhash-crossversion-probe.json`.
Observed shape: count 1,046; file size `4 + 1,046 * 0x10`; 1,046 distinct
candidate 64-bit words; 1,045 distinct 32-bit words in range 0–1,057, with
zero once and 1,057 twice; all 1,046 four-byte trailing words are zero. The
SWSH implementation returns 1,044 dictionary entries after excluding zero
and the duplicated key. These are a cross-version candidate parse only.

The bounded raw-byte scan of the packed ExeFS files `main`, `rtld`, `sdk`, and
`subsdk*` found no `item_hash_to_index` literal. The single-source batch list
`docs/research/source_lists/item-hash-1.txt` returned `selected=0`,
`decoded_outputs=0`, `failed=0`; no canonical JSON or receipt was created.
At the time, the game-data manifest retained this source as `UNKNOWN`, and the regenerated
plan named the SWSH-only parser boundary. At the time, source-wide coverage was
21,092 DECODED / 6,732 UNKNOWN; the later `battle_pocket.dat` follow-up below
updates those totals. The original source bytes are untouched; no field
semantics were imported from Sword/Shield.
## `battle_pocket.dat`: exact-source pkNX value match and byte-map export — 2026-10-29

The local LGPE 1.0.2 source is 1,058 (`0x422`) bytes with SHA-256
`9e7f1132f2a67da6cd4dde7ac5bb9b96e094ca52b346d56c72544c2e885ac226`.
Pinned pkNX `Item.PocketBattle` is a projection of the packed item record.
The new `battle-pocket-probe` mode in
`scripts/gamedata-crosscheck/crosscheck.csproj` reads the exact-build source,
the `item000.dat`–`item1057.dat` set, and the generated JSON. It checks
`raw_hex`, each index and byte, and the numeric value against
`Item.FromBytes(itemNNN.dat).PocketBattle` from commit
`d191cd0e5c05f2af81d9a41c1f1d82e6621b351a`. The checked `main` SHA-256 is
`1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8`; the
ordered item-record concatenation hash is
`c15d85a4aba08aeebdceace89ba5344cd9c5068bef78cc6f448115f462f64e0f`.

The check reports `CANDIDATE_MATCH`, **1,058 records, 0 mismatches**. Values
are 0: 1,028, 1: 22, and 2: 8. This exact, complete data match supports a
numeric `pocket_battle` projection; it does not prove the table's runtime
loader or accessor in `main`. The JSON deliberately does not assign enum names
to those values.

The tracked single-source commands were:

```sh
UV_PROJECT_ENVIRONMENT=/tmp/lgpe-research-env uv run lgpe decode-gamedata --root .. --sources-file docs/research/source_lists/battle-pocket-1.txt --execute
UV_PROJECT_ENVIRONMENT=/tmp/lgpe-research-env uv run lgpe verify --root .. --sources-file docs/research/source_lists/battle-pocket-1.txt
"/mnt/c/Program Files/dotnet/dotnet.exe" run --project scripts/gamedata-crosscheck/crosscheck.csproj -c Release -- battle-pocket-probe .
UV_PROJECT_ENVIRONMENT=/tmp/lgpe-research-env uv run lgpe coverage
UV_PROJECT_ENVIRONMENT=/tmp/lgpe-research-env uv run lgpe plan
```

The batch decoded 1/1 with zero failures, and receipt verification returned
`registered=1`, `verified=1`, `bad=0`, `failed=0`. The one-to-one output is
`decoded/1.0.2/romfs/bin/pokelib/item/battle_pocket.json`, 91,416 bytes,
SHA-256 `635e644885b545a0ad883f9d7082e56985909bed8d5e15d78f44c8ec32506197`.
The new plan reports this source `DECODED` with the pkNX value check and
explicitly says the exact-main loader/accessor is unconfirmed. Game-data
coverage is now **10,010 DECODED / 10 UNKNOWN / 0 FAILED** of 10,020 sources;
source-wide coverage is **SCANNED 27,824; DECODED 21,093; FAILED 0; UNKNOWN
6,731; PENDING 0; UNSUPPORTED 0; 77,714 registered outputs**. The remaining
UNKNOWN game-data sources are nine grammar DAT files and
`item_hash_to_index.dat`.

## `item_hash_to_index.dat` candidate index cross-reference — 2026-10-29

This is the earlier candidate-only report. The exact 1.0.2 reader and final
decode evidence below supersede its `UNKNOWN` format status.

This pass adds an opaque-row inspector and an exact-source cross-reference;
it does **not** promote the file from `UNKNOWN`. The local source remains
16,740 bytes, SHA-256
`a9050fef634aa1bc2dfe34cd48781bc6357498f05133e2ac63a463be2b5f9fc0`. The
candidate layout is only the SWSH `ItemHash8` shape from pinned pkNX commit
`d191cd0e5c05f2af81d9a41c1f1d82e6621b351a` (GPL-3.0): a 4-byte count and
1,046 candidate 16-byte records. No LGPE reader or field meaning is claimed.

The candidate 32-bit value at record offset `+8` was compared only by numeric
equality with the `index` of actual decoded English `itemname` message lines.
The paired inputs are `bin/message/English/common/itemname.dat` (33,196 bytes,
SHA-256 `9df661cc9c203e42a24f03d61d34067278fa23f4c7f2a9a2435cb05d57326f01`)
and `itemname.tbl` (24,427 bytes, SHA-256
`a1d590c0b6a04d881d0265a229857b830e8531e3a6637460518da5e36cc79250`).
`gamedata_decode.message` re-decoded those exact bytes using pinned pokedat
commit `bd423b2cad9aa852fddb796bbba3c5e7b381289b`, and the returned document
exactly equaled the parsed existing `itemname.json` (file SHA-256
`c0491b5a9cfb2b0676bb2b697bfeb65e72f4891e07ad40fa9b00d6dc7ab04376`). The
checker itself now verifies the local pokedat commit, re-decodes these two
source files, and rejects a stale or altered JSON reference before joining.

The numeric join found **1,046/1,046 candidate records** with an English
message-line index and no ambiguous message rows. One candidate index (`1057`)
occurs twice, so the records reference 1,045 distinct `ITEMNAME_###` IDs;
13 of the 1,058 message-line indexes are unreferenced:
`114, 120, 129, 130, 131, 132, 133, 426, 427, 871, 897, 898, 899`. At that
stage, the report retained every raw 16-byte record, file offset, and opaque
little-endian values at `+0`, `+8`, and `+12`, while keeping
`analysis_status: UNKNOWN`. It is
written to ignored `work/item-hash-index-crossref.json` by
`uv run python scripts/research/check_item_hash_index_crossref.py`.

The prior WSL verification attempt exposed that historical Windows runs wrote
UNC absolute paths into output receipts. `verify_outputs` now resolves such a
receipt only when its path suffix matches the locally derived source/output
mirror; it then checks the local source and output hashes as usual. The new
regression tests reproduce Windows UNC source/output paths, including a container source path. The
targeted command
`uv run lgpe verify --root .. --sources-file docs/research/source_lists/itemname-crosscheck.txt`
now reports `registered=1`, `verified=1`, `bad=0`, `failed=0`. A real member
receipt from `bin/archive/script_amx.gfpak` was independently checked in an
isolated temporary project against its local container hash, extracted member,
and JSON output; it reports **1/1 verified**. The broader WSL command using
`docs/research/source_lists/container-receipt-wsl-smoke.txt` was stopped after
more than five minutes with no terminal result because per-member path
resolution is slow on the mapped 9P drive; no full 1,410-row pass is claimed.
The complete
WSL unit suite passes **121/121**. Source-wide coverage is unchanged at
**SCANNED 27,824; DECODED 21,093; FAILED 0; UNKNOWN 6,731; PENDING 0;
UNSUPPORTED 0; 77,714 registered outputs**. T07 remains `IN_PROGRESS`;
the exact format, hash algorithm, runtime consumer, and purpose had not yet
been established.

### WSL verification performance follow-up — 2026-10-29

The interrupted broad receipt check was rerun after replacing repeated
per-receipt `Path.resolve()` walks with a containment resolver that caches
validated shared directories and paths. It still rejects a symlink leaf and
any parent resolving outside the allowed root. The verifier now streams the
JSONL manifest rather than materializing the full 174 MB file in memory, and
maps foreign Windows UNC receipt paths directly against the already validated
local mirror path.

The real command
`UV_PROJECT_ENVIRONMENT=/tmp/lgpe-research-wsl-venv uv run lgpe verify --root .. --sources-file docs/research/source_lists/container-receipt-wsl-smoke.txt`
completed in about **4 min 28 sec** on the WSL 9P mount. The selected
`bin/archive/script_amx.gfpak` batch contained **1,410 registered receipts;
1,410 verified; 0 bad; 0 failed; 0 unsupported**. The earlier stopped run is
superseded by this full result. A microbenchmark on a real decoded member
measured 20 repeated `Path.resolve()` calls at 14.24 sec and 20 `is_file()`
calls at 1.86 sec on this mount, explaining why redundant path walks had
prevented timely completion. The full WSL regression suite now passes
**125/125**. Source-wide coverage remains **SCANNED 27,824; DECODED 21,093;
FAILED 0; UNKNOWN 6,731; PENDING 0; UNSUPPORTED 0; 77,714 registered
outputs**. The manifest scan itself remains slow on this mount; verification
success does not change T07's unresolved format/runtime questions.

### Grammar DAT parser probe — 2026-10-29

`uv run python scripts/research/probe_grammar_dat.py --root ..` records a
read-only probe against all nine files under `bin/message/grammar/` with the
pinned pokedat commit `bd423b2cad9aa852fddb796bbba3c5e7b381289b`. All nine
remain `UNKNOWN`; none has a same-name `.tbl` companion. The pinned `LGPE`
`TextFile` reader rejected English, French, German, Italian, and Spanish with
`Invalid initial key! Expected 0.`; the repository's `message` decoder
rejected those same five with `invalid LGPE text header`. JPN, Korean,
Simplified Chinese, and Traditional Chinese are exactly two bytes (`00 00`)
and both readers reject them as truncated inputs. The probe records each
source size and SHA-256, both reader errors, the raw prefix, and post-read
source-hash equality in ignored `work/grammar-probe.json`; it produced
**0 decoded, 9 UNKNOWN, 0 FAILED**. As a positive control, the same pinned
`TextFile` accepted actual `English/common/itemname.dat` and returned 1,058
lines. This does not show whether the two-byte language files are empty stubs
or incomplete source data, and it does not establish the grammar format. The
same script confirms that the UTF-16 source snapshot, `manifests/files.csv`,
and actual `grammar/*.dat` directory contain the same nine names, and that all
nine scan-catalog byte sizes match `stat()` on the source files. The snapshot
contains names but no file sizes or hashes, so it cannot resolve the two-byte
files' origin.

### Exact-build `item_hash_to_index.dat` reader and loss-preserving decode — 2026-10-29

The earlier raw `strings` scan was not a valid negative check for `main`: the
local `0/main` begins with NSO magic `NSO0`, and that command scanned the
packed NSO file bytes. Ghidra 12.2 loaded the same SHA-guarded NSO through its
Switch loader and exposed the mapped strings/code. On the exact Pikachu 1.0.2
`main` (base `0x7100000000`, SHA-256
`1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8`), the
defined string at `main+0xf02a31` is
`bin/pokelib/item/item_hash_to_index.dat`. Its data reference at
`main+0x1d4538` is inside `FUN_71001d4510` (`main+0x1d4510`).

The decompilation calls `FUN_71001d4ff0` with that literal, passes the
resulting path through `FUN_71000adc70`, then reads the returned data pointer
at request-object `+0x170`. It reads the 32-bit count at file offset 0 and
loops over 16-byte records. For each record it loads a qword at `+0` and a
qword at `+8`; the first is used for hash-map lookup/insertion, while the
second is cast to `short` and stored in the map entry. This establishes the
count/stride and loader projection for this exact build. It does not establish
the qword key's hash algorithm, the mapped short's user-facing meaning, or
runtime execution.

`FUN_71001d4510` has one direct call reference, from
`FUN_71001d35e0` at `main+0x1d364c`. That initializer also calls the
neighboring item-resource loaders. It in turn has direct calls from
`FUN_7100005bd0` at `main+0x5c88` and `FUN_71001d62b0` at `main+0x1d638c`.
Ghidra reports one data reference to `FUN_7100005bd0` at `main+0x1527458`;
that pointer reference alone does not establish that the initializer runs.
The path/read/parse evidence is static and build-specific.

The tracked inspector is `scripts/ghidra/InspectItemHashReferences.java`;
`scripts/ghidra/Run-InspectItemHashReferences.ps1` runs it against the local
read-only Ghidra project. The script checks the NCA identity, exact `main`
hash, source table size/hash, image base, and source path before emitting
strings, xrefs, decompilation, and initialized-memory matches. Reproduce with:

```powershell
pwsh.exe -NoProfile -File scripts/ghidra/Run-InspectItemHashReferences.ps1
```

The matching local RomFS source is 16,740 bytes with SHA-256
`a9050fef634aa1bc2dfe34cd48781bc6357498f05133e2ac63a463be2b5f9fc0`. The
new `gamedata_decode.item_hash_to_index` parser preserves the complete source
and every 16-byte record, recording file offsets, both complete qwords, and
the low-16-bit value stored by the loader. It writes the one-to-one mirror
`decoded/1.0.2/romfs/bin/pokelib/item/item_hash_to_index.json` (281,338 bytes,
SHA-256 `db0dbd0f9340a94456c3ec8a2fe7b817035f91decc399fef32ddf41d53e0f2ad`).
All 1,046 records decode and concatenated `raw_hex` equals the source bytes.
The targeted verification command:

```sh
uv run lgpe verify --root .. --sources-file docs/research/source_lists/item-hash-1.txt
```

returned **1 registered, 1 verified, 0 bad/failed/unsupported**.

The source value at record `+8`, truncated exactly as the loader does, still
matches 1,046/1,046 indexes in the source-verified English `itemname` message
document. There are 1,045 unique values; 1057 occurs twice, and 13 English
line indexes are not referenced. `work/item-hash-index-crossref.json` records
the rows and keeps `field_semantics_status: UNKNOWN`; this numeric join does
not name the map's consumer or prove that the values are item-name indexes.
The SWSH pkNX parser remains cross-version corroboration only, not the basis
for the LGPE format declaration.

After this sample batch, game-data coverage is **10,011 DECODED / 9 UNKNOWN / 0
FAILED/PENDING** of 10,020 sources. Source-wide coverage is **SCANNED 27,824;
DECODED 21,094; FAILED 0; UNKNOWN 6,730; PENDING 0; UNSUPPORTED 0; 77,715
registered outputs**. The nine grammar DAT files remain UNKNOWN.

### Grammar DAT structural decode and exact-build path trace — 2026-10-29

The earlier message-envelope probe is superseded at the structural layer. A
bounded grammar decoder now preserves the entire input as `raw_hex`, the raw
interstitial bytes, every UTF-16LE segment, its exact file offset, and its raw
bytes. It exports one JSON per source under the same relative path and stem
with only `.dat` changed to `.json`. It does not call these message DATs and
assigns no language/parser semantics. The second header byte and interstitial
region remain `UNKNOWN`.

Observed across the five nonempty files: byte 0 equals the number of u16
little-endian absolute offsets stored from file offset 2; the first payload
offset equals `2 + 2*offset_count + offset_count*header_byte_1`; offsets are
strictly increasing and aligned; each offset-bounded segment is valid
UTF-16LE ending in a NUL. The other four files are exactly `00 00` and decode
as zero-offset, zero-payload forms. The decoder validates these observed
bounds and encoding rules, retaining opaque bytes rather than naming them.
Across all nine files there are 3,372 source bytes, 52 text segments and 230
NUL-delimited string fragments. The 2-byte forms are valid structural empty
forms under this decoder; this does not establish why those locales are empty.

| Source | Bytes | SHA-256 | Offsets / segments | String fragments |
|---|---:|---|---:|---:|
| `bin/message/grammar/English.dat` | 86 | `76341d90414dcdb5a330fb205e66fb0eaff84c66bc4944f67f8d0f6f003f2061` | 4 | 8 |
| `bin/message/grammar/French.dat` | 538 | `fb83a92ef3ba82400c78f126ac6b1e614dcff8dc77a9948f33f27fe3e82bfdfe` | 12 | 42 |
| `bin/message/grammar/German.dat` | 334 | `9cb8aeccd90b41f7deb62a6c47510c3b7d36176f0392bb2ff93231d5ebde5ddd` | 8 | 26 |
| `bin/message/grammar/Italian.dat` | 1,602 | `ba0750015be1e667ee7f0948915e01fa87a2a8b36719ed4833de0909bc60a83a` | 16 | 100 |
| `bin/message/grammar/JPN.dat` | 2 | `96a296d224f285c67bee93c30f8a309157f0daa35dc5b87e410b78630a09cfc7` | 0 | 0 |
| `bin/message/grammar/Korean.dat` | 2 | `96a296d224f285c67bee93c30f8a309157f0daa35dc5b87e410b78630a09cfc7` | 0 | 0 |
| `bin/message/grammar/Simp_Chinese.dat` | 2 | `96a296d224f285c67bee93c30f8a309157f0daa35dc5b87e410b78630a09cfc7` | 0 | 0 |
| `bin/message/grammar/Spanish.dat` | 804 | `d27412d77e7526ca9841b1e9c042d68b0cb9b7b0a345a117c07cc531ca68f8b1` | 12 | 54 |
| `bin/message/grammar/Trad_Chinese.dat` | 2 | `96a296d224f285c67bee93c30f8a309157f0daa35dc5b87e410b78630a09cfc7` | 0 | 0 |

The previous read-only probe hashes match the source hashes above, and the
batch rechecked source hashes after conversion. Each JSON's `raw_hex` equals
its source bytes; output SHA-256 and source SHA-256 are recorded in
`manifests/gamedata.jsonl` and `manifests/outputs.jsonl`.

The exact-build Ghidra 12.2 script checks NCA ID
`2b7730a9e56498bbafac2002d4908c6b`, `main` SHA-256
`1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8`, and
image base `0x7100000000`. It found 9 defined grammar strings and 9 direct
string xrefs, all in `FUN_71001ae750` (`main+0x1ae750`). That function builds
all nine paths via `FUN_710004deb0` and submits the requests through
`FUN_71000adc70` (`main+0xadc70`). Its only direct incoming call reference
is from `FUN_7100005bd0` (`main+0x5bd0`, call at `main+0x61d0`). Ghidra shows
one data reference to that caller at `main+0x1527458`; this is a static
reference chain and does not prove the initializer or requests execute. The
request consumer/parser was not recovered. Reproduce the inspection with:

```powershell
pwsh.exe -NoProfile -File scripts/ghidra/Run-InspectGrammarDataReferences.ps1
```

The actual batch used the tracked selections
`docs/research/source_lists/t07-grammar-smoke3.txt` and
`docs/research/source_lists/t07-grammar-9.txt`:

```sh
UV_PROJECT_ENVIRONMENT=/tmp/lgpe-research-env uv run lgpe decode-gamedata --root .. --sources-file docs/research/source_lists/t07-grammar-smoke3.txt --execute
UV_PROJECT_ENVIRONMENT=/tmp/lgpe-research-env uv run lgpe verify --root .. --sources-file docs/research/source_lists/t07-grammar-smoke3.txt
UV_PROJECT_ENVIRONMENT=/tmp/lgpe-research-env uv run lgpe decode-gamedata --root .. --sources-file docs/research/source_lists/t07-grammar-9.txt --execute
UV_PROJECT_ENVIRONMENT=/tmp/lgpe-research-env uv run lgpe verify --root .. --sources-file docs/research/source_lists/t07-grammar-9.txt
```

The three-file smoke decoded 3/3 and verified 3/3. The full selection then
decoded 9/9 with 0 failed, and verified **9 registered / 9 verified / 0 bad /
0 failed / 0 unsupported**. No original files changed. Game-data coverage is
now **10,020 SCANNED; 10,020 DECODED; 0 FAILED; 0 UNKNOWN; 0 PENDING; 0
UNSUPPORTED**. Source-wide coverage is **SCANNED 27,824; DECODED 21,103;
FAILED 0; UNKNOWN 6,721; PENDING 0; UNSUPPORTED 0; 77,724 receipts**.
WSL CPython 3.12.3 passes **132/132** tests; native Windows CPython 3.12.13
ran 132 with 131 passed and one symlink-permission skip. T07 remains
`IN_PROGRESS`: the parse tree is structural, and runtime/parser semantics
remain unverified.

## Localized `sort_string` DAT candidate profile — 2026-10-30

Run the read-only profiler with:

```sh
UV_PROJECT_ENVIRONMENT=/tmp/lgpe-research-env uv run lgpe profile-sort-string --root ..
```

It writes `manifests/sort_string_candidates.jsonl` (one source/hash record per
file) and `manifests/sort_string_candidates.summary.json`. The actual RomFS
contains **81** matching files: nine locale folders, three filename families
(`item`, `monsname`, `waza`) and three suffixes per family (`initial_index`,
`initial_to_sort`, `sort_table`). The report path set matches `files.csv` 81/81,
and recomputed hashes match all 81 source files. Stage counts are **SCANNED 81;
DECODED 0; FAILED 0; UNKNOWN 81; PENDING 0; UNSUPPORTED 0**. These remain in
source-wide UNKNOWN; no decoded output was generated.

Every file has even length. The report records a little-endian u16
representation as a candidate hypothesis and records candidate counts, but
does not emit parsed contents or assign semantic fields. All 27
`*_sort_table.dat` candidates have nonempty distinct values equal to `1..N`
(N=1,057 item; 809 monsname; 742 waza; nine files per family). Each matching
`*_initial_index.dat` has N+1 candidate values and begins with `0xffff`.
`initial_to_sort` candidate counts are 54 for English/French/German/Italian/
Spanish, 92 JPN, 30 Korean, 50 Simp_Chinese and 72 Trad_Chinese, repeated in
each family. These checks establish byte-level patterns only; they do not
decode the tables. An empty sort table does not pass the permutation check.

| Source | Bytes | SHA-256 |
|---|---:|---|
| `bin/app/sort_string/English/item_initial_index.dat` | 2,116 | `a62b7f1c731270c5e0245c6c509119836002211eeaff2ee85ce39f8a6a57d4e6` |
| `bin/app/sort_string/English/item_initial_to_sort.dat` | 108 | `3c9e480ff4f63f2c60d677764dab457554c1d656be895146aa3c63341d3bc76b` |
| `bin/app/sort_string/English/item_sort_table.dat` | 2,114 | `ff12ac2acbd8d340414409f260b87f695e231f6aa30380d88299bbf8321b81e4` |

Reproduce exact-build static inspection with
`pwsh.exe -NoProfile -File scripts/ghidra/Run-InspectSortStringReferences.ps1`.
The wrapper guards NCA folder `2b7730a9e56498bbafac2002d4908c6b_NCA`, `main`
SHA-256 `1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8`,
and image base `0x7100000000`; the Ghidra 12.2 project is opened read-only.
Locale selection xrefs lead to `FUN_71003740d0` (`main+0x3740d0`). The item,
monsname, and waza filename trios occur in `FUN_7100b31400`,
`FUN_7100b315e0`, and `FUN_7100b318c0`, respectively, each requesting the
three files in that order. Generic resource helper `FUN_7100374530` stores
raw buffer pointers and byte sizes on the observed path; this is not proof of
16-bit table access. `FUN_7100377800` is a `ushort` accessor for a separate
`zukan_data` group and is not evidence for these files. No direct parser
access to these sort-string buffers was established, and static requests do
not prove runtime execution.

The separate `bin/pokelib/personal/monsname.dat` is not in this profile; the
following follow-up section documents its later decode. Focused profiler tests: **5/5**. Full WSL2 regression suite, with
`PYTHONPATH=.`, pytest cache disabled for the mapped drive, and process-scoped
Git `safe.directory` for the pinned pkNX checkout: **168 passed, 70 subtests
passed**. Source-wide coverage remains **SCANNED 27,824; DECODED 21,456;
FAILED 0; UNKNOWN 6,340; PENDING 0; UNSUPPORTED 28; 78,104 outputs**.

## Personal `monsname.dat` unlabeled text decode — 2026-10-30

The separate `bin/pokelib/personal/monsname.dat` was tried with pinned
pokedat commit `bd423b2cad9aa852fddb796bbba3c5e7b381289b` (GPL-3.0). The
standalone pokedat CLI warned that no same-stem `.tbl` exists, but decoded 803
nonempty text lines; labels and hashes were therefore unavailable. The
project batch now runs the same upstream `TextFile` parser for this exact
source, retaining only parser-generated indexes and strings plus the complete
raw source bytes in JSON. It does not invent IDs or hashes.

Execute and verify the single-source batch with:

```sh
UV_PROJECT_ENVIRONMENT=/tmp/lgpe-research-env uv run lgpe decode-gamedata --root .. --sources-file docs/research/source_lists/t07-personal-monsname.txt --execute
UV_PROJECT_ENVIRONMENT=/tmp/lgpe-research-env uv run lgpe verify --root .. --sources-file docs/research/source_lists/t07-personal-monsname.txt
UV_PROJECT_ENVIRONMENT=/tmp/lgpe-research-env uv run lgpe check-personal-monsname --root ..
```

The mirrored JSON is
`decoded/1.0.2/romfs/bin/pokelib/personal/monsname.json`; its source path
differs only by extension. Source SHA-256 is
`69ad057bd964a21629646e4e694a705ee69d0c919ba1cf2b13ec0e58f7c6a2a8`
(24,384 bytes); output SHA-256 is
`270d56ccbcb21bd231b6cbaea76e86e733f816c6ef75be86d99b4acac7166e5a`.
Receipt verification passed **1/1**, with zero bad, failed, or unsupported
outputs.

The separate, already decoded reference
`bin/message/JPN/common/monsname.dat` has 810 entries; all 803 personal-file
strings equal its same-index prefix. The seven trailing reference lines are
not present in the personal file. The generated audit report
`manifests/personal_monsname_crossref.json` records both source/output hashes,
tool commits, and comparison counts. This establishes decoded text and a
content cross-reference; labels, source identity beyond the path, and any
relationship to localized `sort_string` indexes remain unassigned.

Subset T07 counts now include this source: **SCANNED 1; DECODED 1; FAILED 0;
UNKNOWN 0; PENDING 0; UNSUPPORTED 0**. Source-wide coverage after `uv run
lgpe coverage`: **SCANNED 27,824; DECODED 21,457; FAILED 0; UNKNOWN 6,339;
PENDING 0; UNSUPPORTED 28; 78,105 outputs**. The 81 localized sort-string
sources remain UNKNOWN. The focused decoder, batch, and cross-reference tests
pass **6/6**; WSL2 full regression suite passes **174 tests and 70 subtests in
85.56 seconds**.

## Exact-main `zukan_sort` u16 arrays — 2026-10-30

This is a separate data family from the 81 localized
`bin/app/sort_string/*.dat` files. A new SHA-guarded Ghidra 12.2 trace against
the local Pikachu 1.0.2 `0/main` (`1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8`)
read the ten path pointers at `main+0x15520b8`. They resolve to
`bin/app/zukan_data/bin/zukan_sort_{zenkoku,chihoua,chihoub,chihouc,chihoud,chihoue,high,short,heavy,light}.bin`.
The owner initializer calls `main+0x3775e0` with indexes 0 through 9. That
loader copies the loaded data pointer and projects the byte length to a count
by shifting right one. `main+0x377800` directly reads a 16-bit element at
`buffer + index*2`; the query path at `main+0xb0acd0` calls that accessor.
This establishes a little-endian u16 array representation for this family.
It does not assign meaning to any element, or prove runtime execution.

The existing `FUN_7100377800` accessor is therefore tied to the distinct
`zukan_sort_*.bin` files; it is not evidence that the localized
`sort_string/*.dat` files are u16 arrays. Those 81 DAT files remain UNKNOWN.
No field names or index semantics are inferred from the similar sort naming.

`gamedata_decode.zukan_sort_data` exports each observed u16 as
`value_u16le`, file offset and raw two-byte hex, with the complete source
`raw_hex` preserved. `run_gamedata_batch` writes same-relative-path `.json`
outputs. The tracked `manifests/zukan_sort_results.jsonl` records all ten
source/output hashes, counts, and exact-main provenance; its SHA-256 is
`1a888080b288c862585c1de93b774db6bb785bed23aff25b11a6c19da5e813f2`.
All ten outputs were independently checked for source/output hash equality,
full-byte reassembly, per-entry reassembly, and matching entry counts.

Real-source smoke run: **SCANNED 3; DECODED 3; FAILED 0; UNKNOWN 0; PENDING 0;
UNSUPPORTED 0**; receipts verified **3/3**. Full family run: **SCANNED 10;
DECODED 10; FAILED 0; UNKNOWN 0; PENDING 0; UNSUPPORTED 0**; receipts
verified **10/10**. The ten files contain six 810-element arrays (1,620 bytes
each) and four 1,120-element arrays (2,240 bytes each). Reproduce with:

```sh
PYTHONPATH=. UV_PROJECT_ENVIRONMENT=/tmp/lgpe-research-env uv run lgpe decode-gamedata --root .. --sources-file docs/research/source_lists/t07-zukan-sort-smoke.txt --execute
PYTHONPATH=. UV_PROJECT_ENVIRONMENT=/tmp/lgpe-research-env uv run lgpe verify --root .. --sources-file docs/research/source_lists/t07-zukan-sort-smoke.txt
PYTHONPATH=. UV_PROJECT_ENVIRONMENT=/tmp/lgpe-research-env uv run lgpe decode-gamedata --root .. --sources-file docs/research/source_lists/t07-zukan-sort-all.txt --execute
PYTHONPATH=. UV_PROJECT_ENVIRONMENT=/tmp/lgpe-research-env uv run lgpe verify --root .. --sources-file docs/research/source_lists/t07-zukan-sort-all.txt
PYTHONPATH=. UV_PROJECT_ENVIRONMENT=/tmp/lgpe-research-env uv run lgpe coverage
pwsh.exe -NoProfile -ExecutionPolicy Bypass -File scripts/ghidra/Run-TraceSortStringOwnerAccess.ps1
```

The Ghidra runner enforces the exact main SHA and `-noanalysis -readOnly`; it
reproduced ten path strings and decompiled 15 functions, with three temporary
function boundaries discarded on close. No original game files were changed.
The full WSL2 regression suite passes **177 tests and 70 subtests in 85.46
seconds**. Updated source-wide totals are **SCANNED 27,824; DECODED 21,467;
FAILED 0; UNKNOWN 6,329; PENDING 0; UNSUPPORTED 28; 78,115 registered
outputs**. The game-data manifest now has **10,031 DECODED** rows.

## Localized sort-string consumer trace follow-up — 2026-10-30

The exact-main path/load trace for localized `item`, `monsname`, and `waza`
sort resources did not establish their binary element representation. To
follow the class side, `TraceLocalizedSortVtableAccess.java` checks the same
Pikachu 1.0.2 `main` hash and image base, then decompiles 12 item/waza vtable
targets recovered from the prior pointer-table cross-reference. It found 12
decompilable functions; 11 function boundaries were created only in the
read-only session. These targets are cleanup thunks and resource lifecycle
methods, with no reads from the loaded candidate arrays. The item vtable
targets are `main+0xb313c0`, `+0xb313f0`, `+0xb31860`, `+0xb31890`,
`+0xb31870`, and `+0xb318a0`; the waza targets are `main+0xb31880`,
`+0xb318b0`, `+0xb321e0`, `+0xb32310`, `+0xb32320`, and `+0xb32330`.

`TraceSortResourceFieldUses.java` then scanned 2,839,329 executable
instructions for six offsets used by the generic sort-resource helper. It
reported 3,515 instructions across the executable and 86 within
`main+0xb00000` to `main+0xb3ffff`. The constants are too common to associate
with the localized sort buffers without an object/dataflow link, so these
matches do not validate u16, endian, or any table semantics. Per-offset
candidate counts were `0x340`: 689, `0x348`: 420, `0x350`: 426, `0x358`: 376,
`0x360`: 951, and `0x368`: 653. No decoder was added and no decoded output
was emitted on this evidence.

The localized source subset remains **SCANNED 81; DECODED 0; FAILED 0;
UNKNOWN 81; PENDING 0; UNSUPPORTED 0**. Current source-wide totals remain
**SCANNED 27,824; DECODED 21,467; FAILED 0; UNKNOWN 6,329; PENDING 0;
UNSUPPORTED 28; 78,115 outputs**. The ten `zukan_sort_*.bin` arrays remain a
separate, already decoded family. Reproduce the follow-up with:

```powershell
pwsh.exe -NoProfile -ExecutionPolicy Bypass -File scripts/ghidra/Run-TraceLocalizedSortVtableAccess.ps1
pwsh.exe -NoProfile -ExecutionPolicy Bypass -File scripts/ghidra/Run-TraceSortResourceFieldUses.ps1
```

## Localized sort-table/message cross-reference — 2026-10-30

`uv run lgpe crossref-sort-string --root ..` re-read all 81 actual localized
`sort_string` DAT files, rehashed them against both `files.csv` and the earlier
byte-profile manifest, then checked every candidate sort table against its
same-locale decoded `common/{itemname,monsname,wazaname}.json`. The message
source and JSON hashes were rechecked against their DECODED game-data manifest
rows before comparison. The command generated
`manifests/sort_string_message_crossrefs.jsonl` (27 rows) and its summary.
The JSONL SHA-256 is
`08c73bdf77b1b6291cef8e407395b0637052ba60f30e2ab463587d0a9be2fb20`; the
summary SHA-256 is
`85ae395e997faa6d790fc156d0db023ae5c8148a416f399ef435e28d04490755`.

For all 27 `_sort_table.dat` files, little-endian 16-bit candidate values form
a complete permutation of `1..N`, big-endian candidates form no such
permutation, each candidate value resolves to exactly the same-numbered
decoded message `line.index`, and all 27 sets of message IDs have the expected
family prefix. The array lengths are 1,057 items, 809 Pokémon names, and 742
moves; each companion message has one additional line at index 0. As a
content-order check, English monsname is exactly nondecreasing under Unicode
NFKD + case-fold (808/808 adjacent pairs); English item names are 1,053/1,056.
That normalization score is diagnostic only and is not a locale collation
claim. Four of the 27 candidate tables are fully ordered under that generic
comparison; CJK ordering is expected to differ from Unicode code-point order.

This is byte-content and message cross-reference evidence, not a recovered
element-read instruction. Ghidra on the exact Pikachu 1.0.2 `main` confirms the
three resource request functions and filenames, but still does not identify
the consumer's element width or byte order. The report therefore keeps
**SCANNED 81; DECODED 0; FAILED 0; UNKNOWN 81; PENDING 0; UNSUPPORTED 0**;
no production output or receipt was created. Existing source-wide totals are
unchanged at **SCANNED 27,824; DECODED 21,467; FAILED 0; UNKNOWN 6,329;
PENDING 0; UNSUPPORTED 28; 78,126 registered outputs**. Focused cross-reference
tests pass **5/5**. The complete `main` hash remains
`1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8`.

### Exact-build helper/resource separation follow-up — 2026-10-30

`TraceSortStringAccessorLink.java` extends the same SHA-guarded, read-only
Ghidra trace. It decompiled 24 functions and created one temporary function
boundary; Ghidra discarded that boundary when closing `/main`. The target is
the Pikachu 1.0.2 `main` with SHA-256
`1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8`, base
`0x7100000000`.

This pass disambiguates the owner fields. `FUN_7100b094e0` stores its helper at
owner `+0x20` and the separately constructed three-file resource object at
`+0x28`. `FUN_7100b0a200` calls the u32-count/u16-search accessors on `+0x20`.
The helper initializer's fixed loaders include exact-build resource paths
`bin/app/zukan_data/bin/zukan_chi_data.bin`, `zukan_sty_data.bin`,
`zukan_nex_data.bin`, and `zukan_evo_data.bin`. They are a different resource
family from the three paths requested at `FUN_7100b315e0`:
`monsname_initial_index.dat`, `monsname_sort_table.dat`, and
`monsname_initial_to_sort.dat`. The owner query's accesses therefore do not
prove the element layout of those localized DATs. The trace confirms resource
requests and static field relationships only; it does not prove runtime
execution or direct reads from the three localized file buffers.

Reproduce with
`pwsh.exe -NoProfile -ExecutionPolicy Bypass -File scripts/ghidra/Run-TraceSortStringAccessorLink.ps1`.
The localized subset remains **SCANNED 81; DECODED 0; FAILED 0; UNKNOWN 81;
PENDING 0; UNSUPPORTED 0**. Source-wide totals remain **SCANNED 27,824;
DECODED 21,467; FAILED 0; UNKNOWN 6,329; PENDING 0; UNSUPPORTED 28; 78,126
registered outputs**. No decoder, output, or receipt was added.

### Localized sort owner and child vtable expansion — 2026-10-30

The follow-up runner now also reads the exact-build vtable tables for the
derived monsname-list owner and the `+0x28` resource child, then decompiles the
additional list/resource methods. The SHA-guarded read-only run completed with
**41 decompiled functions** and **16 temporary function boundaries**, which
were discarded when Ghidra closed `/main`. It records the resource-child
vtable global at `0x7101609450`; Ghidra's saved reference map reports one
direct data reference, from the constructor at `main+0xb0b560`. The inspected
child methods at `main+0xb0b6a0`, `+0xb0b6b0`, `+0xb0b6c0`, and `+0xb0b6d0`
forward to the generic resource-release helper `FUN_7100373e30`. The
additional derived-list entries at `main+0xb07d10`, `+0xb07d80`, `+0xb07e00`,
`+0xb07e80`, `+0xb07d60`,
`+0xb07dc0`, `+0xb07e40`, `+0xb07ee0`, `+0xb07f80`, and `+0xb07fc0` operate on
list bounds, callback state, or byte-valued list records. These methods do not
directly read the three localized resource buffers. This is a bounded static
trace, not proof that no indirect consumer exists elsewhere.

Reproduce with
`pwsh.exe -NoProfile -ExecutionPolicy Bypass -File scripts/ghidra/Run-TraceSortStringAccessorLink.ps1`.
The files remain **SCANNED 81; DECODED 0; FAILED 0; UNKNOWN 81; PENDING 0;
UNSUPPORTED 0**. Global coverage remains **SCANNED 27,824; DECODED 21,467;
FAILED 0; UNKNOWN 6,329; PENDING 0; UNSUPPORTED 28; 78,126 outputs**; no
conversion output or receipt was emitted.

### T07 exact-main localized sort readers and first batch decode — 2026-10-30

The follow-up is SHA-guarded to the actual Pikachu 1.0.2 `main` at base
`0x7100000000`, SHA-256
`1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8`.
Ghidra 12.2 read-only pass v12 reports language `AARCH64:LE:64:v8A` and
decompiled 53 functions. It discarded 16 temporary function boundaries on
close; the wrapper confirmed `-noanalysis -readOnly`, exact source hash, and `Discarding changes to ... /main`.

Three exact-build request functions load the matching filename triplets:

| family | request function | first / second / third file |
|---|---:|---|
| item | `main+0x31400` | `item_initial_index.dat` / `item_sort_table.dat` / `item_initial_to_sort.dat` |
| monsname | `main+0x315e0` | `monsname_initial_index.dat` / `monsname_sort_table.dat` / `monsname_initial_to_sort.dat` |
| waza | `main+0x318c0` | `waza_initial_index.dat` / `waza_sort_table.dat` / `waza_initial_to_sort.dat` |

Each function calls the shared loader at `main+0x374530`; direct callers of
the item and waza request functions are `main+0x7774a0` and `main+0x7775b0`.
In its localized-resource branch, the loader binds the second file's data
pointer and byte length at object `+0x340/+0x348`, and the third file's data
pointer at `+0x360`.

The element reads are now explicit in this exact `main`:

- `FUN_7100374a90` (`main+0x374a90`) checks `index < byte_length/2`, then
  returns the `u16` at `data + index*2`. Its callers include
  `main+0xb09cc0`, `main+0xb0a060`, `main+0x750320`, and `main+0x74eeb0`.
  The accessor's AArch64 `u16` load establishes little-endian element width.
- `FUN_7100374ad0` (`main+0x374ad0`) reads two `u16` values at
  `data + index*4` and `+2`; its call sites include the exact family handlers.
  `main+0xb0a000` passes the returned pair to `main+0xb09cc0`; that consumer
  loops from the first value while `first <= current <= second`, so the
  second value is an inclusive loop endpoint in this consumer. The JSON
  retains neutral `first_u16le` / `second_u16le` names.
- `FUN_7100374ac0` (`main+0x374ac0`) reports the second resource's byte length
  divided by two. This agrees with the `u16` element accessor.

The first `*_initial_index.dat` file is passed to the same loader and its
buffer pointer/size are cached, but this trace did not find a corresponding
element read. Those 27 files therefore remain UNKNOWN and have no JSON output.
No meaning is assigned to sort-table values beyond the observed `u16`
accessor and the already documented message cross-reference.

Implemented `src/lgpe_research/localized_sort_decode.py` with two lossless
representations: `u16le-index-table` for `*_sort_table.dat` and
`u16le-pair-table` for `*_initial_to_sort.dat`. Both include 0-based record
indexes, byte offsets, numeric values, and full `raw_hex`; malformed element
sizes and empty files fail explicitly. `decode-gamedata` emits mirrored JSON
paths with only `.dat` changed to `.json`, registers source/output hashes and
static evidence, and records the first family files as UNKNOWN. The fixed
source list `configs/sort_string_sources.txt` was generated from and matched
the actual RomFS inventory (81 paths; 9 locale directories × 3 families × 3
files).

Execution sequence:

1. Four real sample files across both decoders and all three families passed
   source/output SHA-256 checks and JSON `raw_hex` round trips.
2. A 20-file bounded batch decoded 10 sort tables and 10 range tables; all
   20/20 receipts and raw-byte round trips passed with 0 failures.
3. Full localized batch:
   `uv run lgpe decode-gamedata --root .. --limit 0 --execute --sources-file configs/sort_string_sources.txt`
4. Targeted verification rehashed every source/output pair, verified every
   receipt and raw-byte round trip: **54/54 DECODED; 0 FAILED**. The subset is
   now **SCANNED 81; DECODED 54; FAILED 0; UNKNOWN 27; PENDING 0;
   UNSUPPORTED 0**. `manifests/gamedata.jsonl` contains **10,112 rows**:
   **10,085 DECODED, 27 UNKNOWN**. Global coverage is **SCANNED 27,824;
   DECODED 21,521; FAILED 0; UNKNOWN 6,275; PENDING 0; UNSUPPORTED 28;
   78,180 registered outputs**.

Four representative source → JSON SHA-256 pairs:

| source | source SHA-256 | JSON SHA-256 |
|---|---|---|
| `English/monsname_sort_table.dat` | `eaf41c43fb88032ea6a6b0a18ba0a35783cde91bd2ea15be1840f5966fab72a2` | `1e44ec5b2169c849b23ea1d7417e6e937a0cb2ecb9d5f68799e765554f9df55a` |
| `French/item_sort_table.dat` | `770cf5485b3c48bf53d80e763810b1c6a10dc8bebed2215b8d1fa1e50fbf90c5` | `e67a823d5aa60ac80ce4ef1659372e4591044a00ec8692f8c8fe0d290e9decf6` |
| `JPN/waza_initial_to_sort.dat` | `2b7d6c1431a7e20f25faf9b1f5d6874fb649417c563e92a86505dd2e688a64d4` | `18ef1e2e247fd816ff53b2b483d236791c42bddb29481e21f244463ce5df20fe` |
| `English/monsname_initial_to_sort.dat` | `bf9ef01dda1117ffdbd4427f66388c64e7862dcae8cfad26f61e59a5dd8e96cc` | `d960aec0643c023fcf4d33ae18193db7130a5e30a3ac3a75869d78e7c47ed47b` |

Reproduce the localized pass from the repository root with the command above,
then run `uv run lgpe coverage`. On this WSL host the pre-existing project
`.venv` is Windows-only; the verified Linux run used
`UV_PROJECT_ENVIRONMENT=/tmp/lgpe-research-venv` without replacing `.venv`.
An unfiltered all-corpus `verify` attempt was interrupted after 5:30 because
mapped-drive output I/O remained blocked; it exited 130 and produced no failure
list. The supported targeted verifier completed with
`uv run lgpe verify --root .. --sources-file configs/sort_string_sources.txt`:
**registered 54 / verified 54 / bad 0 / errors [] / failed 0 / unsupported 0**.
The prior native-Windows full replay verified 78,126 outputs before this batch;
this pass independently verifies all 54 additions. Re-running
`uv run lgpe crossref-sort-string --root ..` reports 27/27 same-index message
joins and now reads canonical manifest status **54 DECODED / 27 UNKNOWN**; the
cross-reference command itself does not write decoder outputs.

### Exact first-resource accessor boundary follow-up — 2026-10-30

Ghidra 12.2 v13 reran against the exact Pikachu 1.0.2 `main` SHA-256
`1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8`, with
image base `0x7100000000`, language `AARCH64:LE:64:v8A`, `-noanalysis`, and
`-readOnly`. The script additionally decompiled the 12 functions in
`main+0x373e00..main+0x374b80`; all 12 completed, and five mentioned one or
more searched offsets `+0x340/+0x348`, `+0x350/+0x358`, or `+0x360`.
`docs/research/evidence/sortstring-resource-v13.txt` preserves the actual
decompiler excerpts and the script's bounded-scan summary.

The three exact-build request callers establish resource order:

| caller | first resource | second resource | third resource |
|---|---|---|---|
| `main+0x31400` | `item_initial_index.dat` | `item_sort_table.dat` | `item_initial_to_sort.dat` |
| `main+0x315e0` | `monsname_initial_index.dat` | `monsname_sort_table.dat` | `monsname_initial_to_sort.dat` |
| `main+0x318c0` | `waza_initial_index.dat` | `waza_sort_table.dat` | `waza_initial_to_sort.dat` |

`main+0x374530` copies the first resource's data pointer and byte length into
helper offsets `+0x350/+0x358`; it copies the second resource into
`+0x340/+0x348` and the third pointer into `+0x360`. The in-range readers
`main+0x374a90` and `main+0x374ac0` use only the second resource (one bounded
u16 read and its byte-length/2 count), while `main+0x374ad0` reads two u16s
from the third. The traced item/monsname/waza owner consumers call those
second/third-resource readers. No element load from the first resource was
found in the bounded helper range or those known consumers. The unrelated
`main+0x377a20` u16 reader belongs to a separate `zukan_*` helper chain and is
not evidence for the localized first resource.

The actual RomFS contains 27 `*_initial_index.dat` files. The English
item/monsname/waza samples are 2,116 / 1,620 / 1,486 bytes respectively (all
even lengths), but length alone does not establish an element width or byte
order. The batch manifest therefore remains **SCANNED 81; DECODED 54; FAILED
0; UNKNOWN 27; PENDING 0; UNSUPPORTED 0**. All 27 index files have manifest
status `UNKNOWN` and no JSON output; no output or receipt was created. Global
coverage remains **SCANNED 27,824; DECODED 21,521; FAILED 0; UNKNOWN 6,275;
PENDING 0; UNSUPPORTED 28; 78,180 outputs**.

Reproduce with `pwsh.exe -NoProfile -ExecutionPolicy Bypass -File
scripts/ghidra/Run-TraceSortStringAccessorLink.ps1`. The script verifies the
main SHA before and after analysis and reports that Ghidra discarded all
temporary function boundaries on close; the source main was opened
read-only. The bounded negative result does not rule out a reader elsewhere
in the binary, so `initial_index` stays `UNKNOWN` pending a direct cross-reference.


### Exact-main first-resource pointer-field search — 2026-10-30

Ghidra 12.2 v17 repeated the inspection read-only against the exact Pikachu
1.0.2 `main` (SHA-256
`1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8`, base
`0x7100000000`, `AARCH64:LE:64:v8A`). Across all functions currently defined
in the Ghidra FunctionManager, the script found **88** instruction bodies
with literal AArch64 load operands `#0x350`; this does not establish that
those operands share a structure base. All **88/88** functions decompiled;
**44** had decompiler C lines containing `0x350`. It then
filtered incoming references to those functions against the traced localized
owner/request address ranges and found **4** references: all three item,
monsname, and waza request functions call `main+0x374530`, and monsname owner
initialization at `main+0xb06d60` calls `main+0xb06f10`. The shared loader's
C excerpt checks/caches the first-resource pointer. The owner-side edge to
`main+0xb06f10` was only grouped by its literal immediate in v17; the v19
instruction context below shows that this is a page-relative static address,
not a resource-object field. The filtered v17 output is
`docs/research/evidence/sortstring-pointer-field-v17.txt`.

This is a static search of currently defined function bodies and literal
`[base,#0x350]` load operands. It does not rule out an unowned instruction,
an indirect pointer calculation, or another access pattern elsewhere in the
binary. It does not establish a schema for `initial_index`. Therefore the
localized subset remains **SCANNED 81; DECODED 54; FAILED 0; UNKNOWN 27;
PENDING 0; UNSUPPORTED 0**; the 27 `*_initial_index.dat` sources still have
no JSON output. Global coverage remains **SCANNED 27,824; DECODED 21,521;
FAILED 0; UNKNOWN 6,275; PENDING 0; UNSUPPORTED 28; 78,180 outputs**.


### Corrected owner-side offset interpretation — 2026-10-30

The v17 broad search matched literal load operands, not proven instances of
one shared structure field. The v19 exact-main rerun renamed the output as an
offset-operand scan and emitted the owner function's instruction context.
At `main+0xb06f98`, `ADRP x11, 0x7101609000` precedes `LDR x11, [x11,
#0x350]`; the accessed address is `0x7101609350`. Likewise the `#0x358`
load after `ADRP x12, 0x7101609000` reads from `0x7101609358`. Ghidra's
function decompilation names these as `PTR_LAB_7101609350` and
`PTR_LAB_7101609358`, then stores them in owner members `+0x18e0` and
`+0x18e8`. The same pattern repeats in a second branch. This is not evidence
of a first-resource buffer read, and the prior “pointer/length comparison”
label is withdrawn.

The raw immediate scan still finds **88** defined functions with one or more
load instructions containing `#0x350`; all **88/88** decompile and **44**
have a C line containing the literal `0x350`. Among four incoming references
from the localized owner/request ranges, three are the family requests to
the confirmed shared loader `main+0x374530`, and the fourth is the owner
initialization edge to `main+0xb06f10`; the latter is the static-page false
positive described above. These raw counts are search candidates, not 88
confirmed accesses to the localized resource object.

The only confirmed first-resource use remains the loader's pointer-cache
check/store at `+0x350`; no element reader was identified. This scan does not
exclude unowned instructions or indirect accesses. The 27
`*_initial_index.dat` files remain UNKNOWN with no output. Localized subset:
**SCANNED 81; DECODED 54; FAILED 0; UNKNOWN 27; PENDING 0; UNSUPPORTED 0**.
Global: **SCANNED 27,824; DECODED 21,521; FAILED 0; UNKNOWN 6,275;
PENDING 0; UNSUPPORTED 28; 78,180 outputs**. The read-only v19 context and
scan excerpts are retained at
`docs/research/evidence/sortstring-offset-context-v19.txt`.

### 2026-10-31 exact-resource boundary and receipt recheck

Review of the saved v19 exact-main Ghidra output and trace script confirms that
`main+0x377a20` is a direct u16 load from a different helper object. Its
observed caller chain (`main+0x176940` through the `main+0x377820` resource
helpers) is the separate `zukan_*` data path; it does not establish a read from
the first resource passed to the localized sort loader at `main+0x374530`.
The localized request functions still order their resources as
`initial_index`, `sort_table`, `initial_to_sort`; the first resource has only
the recorded pointer-cache use, while the second and third have the traced
element readers documented above. No new element schema is assigned to
`initial_index`.

Native Windows targeted verification was rerun with
`uv run --offline --python 3.12 lgpe verify --root .. --sources-file
configs/sort_string_sources.txt`, using a temporary `UV_PROJECT_ENVIRONMENT`
because the checked-out `.venv` contains Linux executables. The source list
selected 81 paths; the receipt manifest contains 54 decoded outputs and
verification returned **registered 54 / verified 54 / bad 0 / errors [] /
failed 0 / unsupported 0**. This verifies the 54 source/output hash pairs;
the 27 UNKNOWN inputs have no outputs or receipts to verify. Localized totals
remain **SCANNED 81; DECODED 54; FAILED 0; UNKNOWN 27; PENDING 0;
UNSUPPORTED 0**. Global totals remain **SCANNED 27,824; DECODED 21,839;
FAILED 0; UNKNOWN 5,957; PENDING 0; UNSUPPORTED 28; 78,498 outputs**. No
source game files or decoded outputs were changed by this recheck.

The exact-main NSO relocation module passed **4/4** after making Windows
`git.exe` discoverable to the Python child process. The full native Windows
suite then passed **269 tests with 1 expected symlink-permission skip** in
19.477 seconds. The temporary Python 3.12 environment was selected with
`UV_PROJECT_ENVIRONMENT`; `PATH` and `PATHEXT` included the installed Git
directory and `.EXE` suffix so `shutil.which("git")` resolves the pinned
PokeLDN checkout. The first harness attempt omitted `PATHEXT`, which caused
the NSO integration test to lack its required Git executable; that environment
issue was corrected before the passing rerun.
