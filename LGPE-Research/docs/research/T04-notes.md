# T04 — actual GFPAK extraction (2026-10-28)

Evidence: `SOURCE_CODE`, `DECODED`. All 249 GFPAK member decompressions were independently cross-validated byte-for-byte by SHA256 with Ubuntu system `liblz4.so.1` version 1.9.4. This validates compression output; full pkNX/Toolbox archive execution comparison remains outstanding.

## Sources and implementation

Pinned local source references:

- pkNX `d191cd0e5c05f2af81d9a41c1f1d82e6621b351a`, GPL-3.0 (`tools/src/pkNX/LICENSE`), `pkNX.Containers/Misc/GFPack.cs`, `FnvHash.cs`, and `pkNX.Containers/SARC/{SARCHeader,SFAT,SFATEntry,SFNT}.cs`.
- Switch-Toolbox `3fcb87f1fea25ad56db139b0d9577db591f54118`, GPL-3.0 (`tools/src/Switch-Toolbox/LICENSE`), `File_Format_Library/FileFormats/Archives/GFPAK.cs`, `FileFormats/Hashes/GFPAKHashCache.cs`, `Switch_Toolbox_Library/HashCalculate/FNV64A1.cs`, `Resources/Hashes/Pkmn.txt`.
- Hash corpus SHA256: `cf723be86f905c9cb1cc5a3317528ada3d87b252fc9202a8eb4bd9519cc92df0`.

Implemented bounded headless Python reader in `src/lgpe_research/archive_reader.py` because the reference implementations couple their archive classes to broad desktop/container dependencies. It follows the observed v0x1000 GFPAK layout and compression tags; no proprietary Oodle DLL is used. NONE, zlib, raw LZ4 are supported; Oodle and other versions/relocation explicitly return UNSUPPORTED. Sample compression tags are all 2 (raw LZ4).

GFPAK stores folder/filename/full-path hashes, **not plaintext internal names**. Game Freak's FNV-1a variant starts at `0xCBF29CE484222645`, unlike the standard offset basis. Names are resolved only when hash-verified against the pinned corpus or BNTX/BNSH embedded names. Fully recovered paths also match the stored full-path hash. Unknown names remain uppercase 16-digit hash identifiers, keeping original folder/member identities without fabricated extensions or flattened names. This is a naming limitation, not failed payload decompression.

The first exploratory name-resolution run used the standard FNV basis and resolved no paths. Comparing the actual pinned source exposed the different basis; it was corrected, the exact previously generated GFPAK products were removed only after their output hashes matched the exploratory log, and the extraction reran. Current output/results use the corrected basis.

## Reproduce

Run from the project directory in PowerShell. Source files remain immutable. This module has a dry-run default; only `--execute` writes members. Existing identical members resume; conflicting outputs are rejected. Each sample is isolated in the JSONL result stream.

```powershell
$romfs = Join-Path (Get-Location).Path '../1.0.2/2b7730a9e56498bbafac2002d4908c6b_NCA/1'
uv run python -m lgpe_research.archive_reader --source-root $romfs --output-root decoded/1.0.2/romfs --hash-corpus tools/src/Switch-Toolbox/File_Format_Library/Resources/Hashes/Pkmn.txt --results work/archive-results.jsonl --execute "$romfs/bin/archive/pokemon/pm0001_00.gfpak" "$romfs/bin/archive/field/area01.gfpak" "$romfs/bin/app/battle/bin/battle_command_00.arc"
uv run python -m unittest discover -s tests -p test_archive_reader.py -v
```

Actually executed using `D:/SDK/uv-x86_64-pc-windows-msvc/uv.exe run python -m lgpe_research.archive_reader` with the arguments above. WSL `/mnt/x` is unavailable, so Windows Python/uv access X: directly. No upstream executable was downloaded or blindly run. Source checkout commits were read from `.git/refs/heads/master`.

## Actual outputs

`work/archive-results.jsonl` contains source SHA256, header, method, pinned reference revisions, hash corpus SHA256, every original index, full/folder/file hash where available, packed offset/size/hash, decoded size/hash and mapped output path. `work/archive-verification.json` records an independent disk recheck of all 290 outputs and the unchanged source SHA256s. These machine outputs and extracted assets stay ignored.

| Source under RomFS | Source SHA256 | Files | Output bytes | Full names resolved |
|---|---|---:|---:|---:|
| `bin/archive/pokemon/pm0001_00.gfpak` | `6310620e6eb13f3e03f4106f8d72e5fb73bf2656a4b6d16dc15a0e6897c901d4` | 70 | 5504068 | 68 |
| `bin/archive/field/area01.gfpak` | `0a8d9fcd498fb7441077fd19d19263a910fd07abecc52a7ef3eec503a0416a36` | 179 | 10892904 | 0 |
| `bin/app/battle/bin/battle_command_00.arc` | `7fdd7cf1378565f8b157f07250c5592fbc391063fe6f18ac495222943159534d` | 41 | 1472090 | 41 |

Every output mirrors `decoded/1.0.2/romfs/<source-relative-path>.contents/<internal-path-or-hash-identity>`. pm0001 resolves 68/70 complete paths; the other two keep known folder names and hash-only filenames. area01's folder hash `D759403943DAF95F` is not resolved, so all its paths retain that folder identity; embedded texture names recover many filenames. All stored SARC paths are preserved.

Per-archive aggregate SHA256 below hashes the UTF-8 concatenation of `index + TAB + internal_path + TAB + output_sha256 + LF` in index order. This is an auditable metadata digest, not a hash of concatenated payloads:

- `bin/archive/pokemon/pm0001_00.gfpak`: `3ec2a25f50a92a0513b839e88f592e62a45bd421e0cff7de38e827db88a83f7d`.
- `bin/archive/field/area01.gfpak`: `03e4b32e700a0c474036188c72462e3478aa0ed0b277ccb80f4555eb8062722a`.
- `bin/app/battle/bin/battle_command_00.arc`: `4db3176bdfddff0b9090e34d57cbbff9e3ca31fbfc57b7f735c118b6db4f3cb7`.

Example decoded members:

- `bin/archive/pokemon/pm0001_00.gfpak.contents/bin/pokemon/pm0001_00/anm/718E2B0D8B147F19`: 26024 bytes, SHA256 `04fbcc996afb4a5158060878b086287daecae68f79286ceafd89d736bb7cdcf3`.
- `bin/archive/field/area01.gfpak.contents/D759403943DAF95F/area02_tree2_pasted__shadow.bnsh_fsh`: 8544 bytes, SHA256 `1a9420e62d22cb6b55c6cb28e57d3779ea646936cf332270dd4d036932956c7e`.
- `bin/app/battle/bin/battle_command_00.arc.contents/anim/battle_button_grptxt_00_keep.bflan`: 192 bytes, SHA256 `430fbfcdf594f5e6168d2fdf7164bdf92e40055f3ab7602e7e7e94a91bf25fd8`.

## Validation and limits

Nine archive tests pass, including three actual local fixtures, LZ4 literals/extended lengths/overlapping matches and malformed offsets, traversal and Windows special paths, malformed headers, size limits, compression tags, source immutability, dry-run, repeated extraction and output-conflict rejection. Inputs without the private dump skip only local fixture tests. All 249 real raw LZ4 payloads matched independent `LZ4_decompress_safe` output sizes/hashes from liblz4 1.9.4. The temporary transfer used to invoke the Linux library was deleted after validation.

No sample failed extraction (3/3 containers, 290/290 nonzero members); unknown names are explicitly identified above. Actual format counts and every output hash are in the verification/result artifacts. Archive member bytes are decoded container contents, not finished OBJ/glTF/PNG conversions. Embedded BNTX, BNSH, GFBMDL and animation data still need dedicated decoders. No claim that all GFPAK or all ARC variants are supported. Full independent archive-parser comparison and area01 hash dictionary expansion remain next steps. Root task owner handles shared status/manifest integration and `lgpe verify`.
