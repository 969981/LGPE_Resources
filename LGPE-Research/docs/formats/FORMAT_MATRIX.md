# LGPE 1.0.2 tentative format matrix

Evidence at initial packaging = `OBSERVED_TREE` only. Column “tool” is a proposed decoder path, **not a verified successful local conversion**.

| source | purpose inferred from location | tool / approach | output | risk / check |
|---|---|---|---|---|
| `.gfpak` | Game Freak archive (`bin/archive/pokemon`, `field`) | pkNX / Switch-Toolbox (both state support) | `.gfpak.contents/...` | validate offsets, sizes, internal names and compression; don't assume all internal names visible |
| `.arc` | UI/localized resources | inspect magic first, Switch-Toolbox if format confirmed | `.arc.contents/...` | ARC is ambiguous; not automatically Nintendo SARC |
| `.bntx` | Switch texture | Switch-Toolbox | PNG / metadata JSON | texture may have multiple surfaces/mips, then container-style output |
| `.gfbmdl` | Game Freak 3D model | Switch-Toolbox / Blender addon | glTF/DAE/FBX, material JSON | model/skeleton/textures validation; may depend on GFPAK extractions |
| `.gfbanm` | animation | io_scene_gfbanm Blender addon | FBX/GLTF channels / JSON | bone matching and animation export support vary |
| `.gfbcol` | collision | reverse engineer GF collision binary | JSON/mesh if proven | not a standard model extension |
| `.gfbmad` | material | source-based investigation | JSON if schema known | do not rename random binary |
| `.ptcl` | particles | Switch-Toolbox claimed PTCL support | JSON/texture list if verified | variant-specific format |
| `.wem` | Wwise audio | vgmstream-cli | WAV | verify playable RIFF and non-empty samples |
| `.bnk` | Wwise bank | wwiser, vgmstream | embedded WAV or bank report | bank may contain only event/metadata |
| `.dat + .tbl` under `bin/message` | localized text+index | pokedat (LGPE)/pkNX TextFile | JSON/TXT and index | labels, controls, encoding, newline handling |
| `.dat` elsewhere | arbitrary binary/table | signature and consumer code | case by case | never assume same encoding as message |
| `.tbl` elsewhere | assorted tables | signature and consumer code | case by case | may not use message-index layout |
| `personal_total.bin` | personal stat/form table | pkNX GameManagerGG or data structures | JSON/CSV | prove entry sizes, version alignment |
| `encount_data_p.bin` | wild encounters (Pikachu candidate) | pkNX EditorGG (FlatBuffer EncounterArchive) | JSON/CSV | archive boundaries / offsets; check game-specific fields |
| `encount_data_e.bin` | wild encounters (Eevee candidate) | pkNX EditorGG | JSON/CSV | contains Eevee variant data in game dump; no claim both currently active |
| `.amx` | Battle AI script | LGPE 1.0.2 Ghidra loader/parser xrefs + bounded header catalog | header metadata/static gate only; body listing remains UNKNOWN | custom in-game AMX-like parser identified; do not substitute standard Pawn decoder |
| `.bnsh_vsh/.bnsh_fsh` | shaders | Switch shader research | metadata/bytecode report | proprietary shader variants |
| `.bseq` | sequence | identify magic and consumer | metadata if possible | do not treat as Standard MIDI |
| ExeFS `main` | Switch executable | Ghidra Switch Loader + PyGhidra | symbols/calls/RTTI JSON | address basis must be versioned and proven |

## Format investigation workflow

1. Note exact original path, file size, first 64 bytes, SHA256 sample and source version.
2. Search real parser/source for matching signature/extension; link function/file and commit.
3. Build small `samples/` in gitignored `work/`; run **real** decoding on representative test files.
4. Verify count, names and length boundaries; compare against an independent tool if possible.
5. Add tests/fixtures that don't redistribute game bytes; log hashes/properties rather than binary originals.
6. Only after confirmed success mark `DECODED` and expand batches with resource limits.
