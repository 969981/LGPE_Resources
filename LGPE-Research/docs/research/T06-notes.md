# T06: actual LGPE sample decoding and cross-validation

Date: 2026-10-28. Real source root: `../1.0.2/2b7730a9e56498bbafac2002d4908c6b_NCA/1/`.

References pinned locally:
- [pkNX](https://github.com/kwsch/pkNX/tree/d191cd0e5c05f2af81d9a41c1f1d82e6621b351a), commit `d191cd0e5c05f2af81d9a41c1f1d82e6621b351a`, GPLv3 LICENSE. No proprietary SDK needed. Source was read before build.
- `tools/src/pokedat`, commit `bd423b2cad9aa852fddb796bbba3c5e7b381289b`, GPL-3.0-only per upstream README/LICENSE. Imported as an external dependency, not vendored. Exact remote is recorded below.

Implementation: `src/lgpe_research/gamedata_decode.py`, schema `lgpe-gamedata-v1`. Read-only sample runner, explicit execute flag, bounds validation, existing conflicting output refusal, per-input failure isolation, output/source hashes, repeat-run identical output acceptance. Each original input was rehashed after conversion and remained unchanged. Outputs are ignored, retain source-relative hierarchy and stem, and replace only extension with `.json`. Evidence log: `decoded/gamedata-sample-evidence.json`; independent output/checks: `work/gamedata-crosscheck/`. This fixed sample runner is not a full-language batch scheduler.

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

Result: **CROSS_VALIDATED for four selected pairs**: English and Simp_Chinese `common/bag` (207 lines each) and `script/master_trainer` (88 each), total 590 lines; 4/4 pairs decoded, 0 errors. This exceeds the requested 2–5 representative sample groups because T06 explicitly requires two files in each of two languages, in addition to three T07 files.

`TextFile.cs` proves the 16-byte header, one section, `(offset,u16 length,u16 flags)` entries, line key `0x7C89 + index*0x2983 mod 65536`, rotating key left 3 after each UTF-16 unit, zero terminator, `0x10` variables, ruby and escaped newline semantics. `EditorGG.EditCommon/EditScript` links this decoder to LGPE. Pokedat `text_file.py`, `text_config.py`, `tbl_handler.py` were inspected before importing with `TextConfig("LGPE")`. TBL bytes start `41 48 54 42` (`AHTB`); count followed by uint64 hash, uint16 label byte count, CP1252 label; this is distinct from unrelated DAT files.

Important observed mismatch: each TBL contains **one more label** than the DAT line count (208 vs 207; 89 vs 88). The final labels are `msg_bag_max` and the master-trainer max label. Their exact semantics are not proven; retained under `unpaired_labels`, never assigned a fabricated text. DAT and TBL are positional according to pokedat; label/hash sequences match between the two sampled languages.

Independent C# harness invokes upstream `TextFile` and `TextConfig(GameVersion.GP)`. All 590 decrypted line payloads and all flags agree exactly. Text display comparison required documented normalizations: variable symbolic names differ between pokedat and pkNX, so compare by numeric opcode; pokedat maps U+E300 to U+20BD (currency glyph), while pkNX retains the private-use code point. Before this normalization, five bag lines in each language differed; after it there are zero text mismatches. These display names remain upstream conventions, not independently proven runtime semantics. Examples of checked controls are `\n`, `[VAR ...]`, arguments and zero line terminators. Do not infer correctness of untested ruby/control codes or every language from this sample.

English bag/master-trainer contain 26/72 escaped-newline lines and 70/72 variable lines; Chinese 25/77 and 70/72. There are zero U+FFFD replacement-character lines; this is a useful quality check, not proof that every glyph has a font mapping. No translated dialogue is committed.

## Exact sample evidence

```json
[
  {
    "source": "bin/message/English/common/bag.dat",
    "tool_commits": {
      "pkNX": "d191cd0e5c05f2af81d9a41c1f1d82e6621b351a",
      "pokedat": "bd423b2cad9aa852fddb796bbba3c5e7b381289b"
    },
    "input_sha256": "f33db12932cb3c748dcce7f0cd7a05c71fff5f1e1ba5e4741db17c710ceeabf9",
    "input_bytes": 9324,
    "header_hex": "0100cf005c24000000000000100000005c2400007c0600000500000088060000",
    "tbl_sha256": "361c1300de617190c96f330b8aae0156d9d78a5da4a6eebe786ebec544cbeb70",
    "tbl_bytes": 5000,
    "count": 207,
    "unpaired_labels": 1,
    "escaped_newline_lines": 26,
    "variable_lines": 70,
    "status": "DECODED",
    "output": "decoded\\1.0.2\\romfs\\bin\\message\\English\\common\\bag.json",
    "output_sha256": "b240c34d2e95ea95bb649afd00c247f485a07e6a5945f02cd5729ee6c32f3b48",
    "output_bytes": 32521
  },
  {
    "source": "bin/message/English/script/master_trainer.dat",
    "tool_commits": {
      "pkNX": "d191cd0e5c05f2af81d9a41c1f1d82e6621b351a",
      "pokedat": "bd423b2cad9aa852fddb796bbba3c5e7b381289b"
    },
    "input_sha256": "d425f8138f90bdc98e944dd43659f0aa8d1e9793794744a73def95e353a1ad17",
    "input_bytes": 11908,
    "header_hex": "01005800742e00000000000010000000742e0000c40200002f00040024030000",
    "tbl_sha256": "7e075815c7ab03fb839ad767420bc5f06588111332897cd28c4a6fec84dc6454",
    "tbl_bytes": 2208,
    "count": 88,
    "unpaired_labels": 1,
    "escaped_newline_lines": 72,
    "variable_lines": 72,
    "status": "DECODED",
    "output": "decoded\\1.0.2\\romfs\\bin\\message\\English\\script\\master_trainer.json",
    "output_sha256": "5685d5618dd1c6f120743aa194fe457722f557714a86b40ef538649387187510",
    "output_bytes": 18910
  },
  {
    "source": "bin/message/Simp_Chinese/common/bag.dat",
    "tool_commits": {
      "pkNX": "d191cd0e5c05f2af81d9a41c1f1d82e6621b351a",
      "pokedat": "bd423b2cad9aa852fddb796bbba3c5e7b381289b"
    },
    "input_sha256": "00e28cad0874c3b0b5800016f668b3fdacd87ea8e9fd035f39339bae028370e9",
    "input_bytes": 5572,
    "header_hex": "0100cf00b41500000000000010000000b41500007c0600000500000088060000",
    "tbl_sha256": "361c1300de617190c96f330b8aae0156d9d78a5da4a6eebe786ebec544cbeb70",
    "tbl_bytes": 5000,
    "count": 207,
    "unpaired_labels": 1,
    "escaped_newline_lines": 25,
    "variable_lines": 70,
    "status": "DECODED",
    "output": "decoded\\1.0.2\\romfs\\bin\\message\\Simp_Chinese\\common\\bag.json",
    "output_sha256": "8d79215bdf6a2dbba4d05a5b73e886b9925798e5ce967c402d3e0fe876e42b27",
    "output_bytes": 32073
  },
  {
    "source": "bin/message/Simp_Chinese/script/master_trainer.dat",
    "tool_commits": {
      "pkNX": "d191cd0e5c05f2af81d9a41c1f1d82e6621b351a",
      "pokedat": "bd423b2cad9aa852fddb796bbba3c5e7b381289b"
    },
    "input_sha256": "34de376a5875a7349c11b2572e226e0242e45abd272c231a1e1c997096cce97d",
    "input_bytes": 5260,
    "header_hex": "010058007c14000000000000100000007c140000c402000016000000f0020000",
    "tbl_sha256": "7e075815c7ab03fb839ad767420bc5f06588111332897cd28c4a6fec84dc6454",
    "tbl_bytes": 2208,
    "count": 88,
    "unpaired_labels": 1,
    "escaped_newline_lines": 77,
    "variable_lines": 72,
    "status": "DECODED",
    "output": "decoded\\1.0.2\\romfs\\bin\\message\\Simp_Chinese\\script\\master_trainer.json",
    "output_sha256": "4d0c68d54f7caec2208d3ac3029362ac8f52bb8887c61e3f42b073a556c1b700",
    "output_bytes": 18557
  }
]
```

## Quality and cross-check evidence

```json
{
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
```

Tests: five synthetic corruption/bounds/personal byte-reassembly cases passed. Malformed header, invalid line offset, incomplete personal record, missing required FlatBuffer vector, oversized vector and invalid root are rejected. Source and decoded assets remain ignored; no commit created by this worker. Parent worker owns shared status/index/manifests and final `lgpe verify` integration.

Remaining limitations: fixed representative samples only; no complete multilingual file inventory or bulk run; exact end-label semantics unknown; test coverage does not establish all exotic text controls. T07 move/trainer/item data still pending. The independent harness needs the pinned tool sources and a successful .NET restore. X: is accessible to Windows Python, not mounted as /mnt/x in this WSL session.


## AHTB-only label table batch — 2026-10-29

The actual 1.0.2 scan catalog contains 15 RomFS `.tbl` files with the validated `AHTB` signature and no same-relative `.dat` source. The decoder `gamedata_decode.tbl_labels` now emits one JSON entry per record with its zero-based index, stored 64-bit hash, byte length, original label bytes as hex, and a CP1252 display label. It does not assign table-specific field semantics or interpret these files as message text.

Three real samples decoded before expansion: `bin/field/param/placement/table/AreaNameHashTable.tbl`, `bin/field/param/placement/table/ZoneNameHashTable.tbl`, and `bin/message/asset.tbl`. The complete bounded run used:

```sh
UV_PROJECT_ENVIRONMENT=/tmp/lgpe-research-ahtb-venv uv run lgpe decode-gamedata \
  --execute --limit 0 --sources-file docs/research/source_lists/ahtb-unpaired-15.txt
UV_PROJECT_ENVIRONMENT=/tmp/lgpe-research-ahtb-venv uv run lgpe register-gamedata \
  --sources-file docs/research/source_lists/ahtb-unpaired-15.txt
UV_PROJECT_ENVIRONMENT=/tmp/lgpe-research-ahtb-venv uv run lgpe coverage
python3 scripts/research/check_ahtb_zone_crossrefs.py
```

The decoder processed **15 sources, 15 DECODED, 0 FAILED**. A separate receipt-registration pass verified 15/15 outputs. Each `.tbl` became a same-directory, same-stem `.json`; fresh parse bytes matched the output, and source/output SHA-256 values are in the game-data and output manifests. The `asset.tbl` table has 8,290 entries; its labels contain no verified grammar paths, so it remains an AHTB label index rather than a decoded message corpus. The nine grammar DAT files and three non-record item DAT files remain UNKNOWN.

The independent check re-parses all 15, validates output path mapping and both manifests, and verifies `ZoneNameHashTable.tbl` source SHA-256 `2c314dec7348010523a6f695319d83a136b4f4b7c058666bf3f09c91a82912fe` (5,131 bytes, 257 rows). Using offset basis `0xcbf29ce484222645`, prime `0x100000001b3`, and each label's original bytes after stripping only trailing NUL padding, all **257/257** stored qword hashes match 64-bit FNV-1a. Source/result index links include `0x97deb1f2d0a83282` → row 134 `t005r0305`, `0x194d955fbf0a7685` → row 255 `gogo_park01`, and `0xd8652ab502b422c7` → row 256 `gogo_play01`.

Coverage after this increment: **SCANNED 27,824; DECODED 21,091; FAILED 0; UNKNOWN 6,733; PENDING 0; UNSUPPORTED 0; 77,712 registered outputs**. This improved structural coverage only; AHTB hash labels do not prove game-level meanings. The full WSL suite passes **107/107**.


### AHTB stored-hash method survey — 2026-10-29

After decoding, I tested 64-bit FNV-1a over each original label byte string with trailing NUL padding removed, using offset basis `0xcbf29ce484222645` and prime `0x100000001b3`. The calculation matches **3,105/3,105 rows across 14 of the 15 unpaired AHTB tables**. In `bin/message/asset.tbl`, it matches **0/8,290** stored qwords. The asset table's hash method remains unassigned; the decoder retains the stored qword and raw label bytes without enforcing a hash algorithm. `scripts/research/check_ahtb_zone_crossrefs.py` now prints per-table counts and guards these exact local observations.

### `asset.tbl` literal path cross-reference — 2026-10-29

`UV_PROJECT_ENVIRONMENT=/tmp/lgpe-research-wsl-venv uv run python scripts/research/check_asset_tbl_path_xrefs.py --root ..`
re-decodes the actual AHTB bytes, confirms the existing `asset.json` exactly
reproduces from them, verifies source/output hashes against `gamedata.jsonl`,
and cross-references each literal `bin/message/<label>` candidate against the
RomFS paths in `manifests/files.csv`. The inventory contains 27,818 RomFS
paths and is SHA-256
`134a9c78371fb16f5429022791cfa25dc13ee2771b901a1147dacfbd1ebebefe`.

The table has **8,290 unique labels** across ten language folders, 829 per
language. **5,380** candidates exactly match a local `.dat` path, with all
5,380 same-stem `.tbl` paths also present; there are zero case-only matches,
case-fold ambiguities, or invalid label paths. The remaining **2,910** labels
all have the literal `debug` path component and no match in this RomFS scan
(291 per language). This is an indexed path cross-reference, not proof of
loader use or message grammar, and it does not resolve the asset table's
stored-hash algorithm. The full per-entry report is written to ignored
`work/asset-tbl-path-xref.json`.
