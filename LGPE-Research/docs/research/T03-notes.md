# T03: Source inventory and local toolchain

Exact source commits, license evidence, source paths, and local commands are indexed in tools/source-revisions.tsv and docs/research/TOOL_REVISIONS.md. No ROM, keys, proprietary SDK, or commercial DLL was downloaded.

## Locally verified

- pkNX commit d191cd0e5c05f2af81d9a41c1f1d82e6621b351a (GPL-3.0): source cross-reference for GFPAK/SARC and LGPE data. The .NET 10 `scripts/gamedata-crosscheck` harness compiles the pinned `pkNX.Structures` assemblies and compares actual personal, wild/event encounter, item, trainer, evolution, mega-evolution, and move samples against the Python batch schemas. All four independent verifier scripts report 0 mismatches. Full game-data coverage includes 1,058 item records, 1,588 trainer records, 980 evolution sets, 980 mega-evolution sets, three event encounter tables, and 743 `Move7` records across one WD BinLinker.
- Switch-Toolbox commit 3fcb87f1fea25ad56db139b0d9577db591f54118 (GPL-3.0): GFPAK/SARC source and hash corpus reviewed; BNTX parser source referenced. The Windows .NET 10 build was attempted and failed in upstream Windows-only WinForms/WPF build targets (MSB4803/MSB3822/MSB3823).
- pokedat commit bd423b2cad9aa852fddb796bbba3c5e7b381289a (GPL-3.0-only): locally pinned reference source.
- vgmstream r2168, source commit d9875b1fff307e4759dfb85e49e3d5e6fb196f7c: actual WEM-to-WAV batch. The installed executable and official archive hashes are recorded in TOOL_REVISIONS.md.
- wwiser commit 08e937b649bc7007c234bbd59e34a41d5eef3b38: actual BNK-to-XML adapter. Upstream checkout contains no root license file; no redistribution claim is made.
- Blender 5.1.2 and FFmpeg 8.0.1: actual bounded model/texture conversions. Ghidra 12.2 with Switch Loader commit 5d80d195bf284f8ad5f2f9b66c3bdd5c67dd66a6: actual exact-build NSO analysis.

## Read-only GameManagerGG worker — 2026-10-29

The pinned pkNX source is exactly `d191cd0e5c05f2af81d9a41c1f1d82e6621b351a` (GPL-3.0; clean tracked source). Added `scripts/gamemanagergg-worker`, a headless .NET 10 console project referencing `pkNX.Game`. It constructs `GameLocation` with the explicit LGPE Pikachu enum (`GP`) and the actual extracted `1/` RomFS and `0/` ExeFS paths. A small subclass suppresses `GameManagerGG.SetMitm`; the worker never enables file redirection and never calls `SaveAll`, so it has no write path into the source dump.

Actual command from the WSL project checkout (the WSL project environment is placed on `/tmp`; dotnet is located through Windows PATH and invoked natively):

```sh
UV_PROJECT_ENVIRONMENT=/tmp/lgpe-research-venv uv run lgpe crosscheck-gamemanagergg \
  --root "/mnt/x/ROMS/Nintendo Switch/Pokemon/Pokemon Lets Go Pikachu"
uv run python scripts/gamedata-crosscheck/verify_gamemanagergg_worker.py . \
  work/gamemanagergg/run-20261028T214446Z
```

Equivalent PowerShell command from the project directory:

```powershell
.\scripts\Crosscheck-GameManagerGG.ps1
uv run python scripts/gamedata-crosscheck/verify_gamemanagergg_worker.py . `
  'work/gamemanagergg/run-20261028T220208Z'
```

The PS7 wrapper was executed on this host. It checks/creates the Windows uv
environment, finds the installed .NET 10 SDK, builds the worker, then invokes
the built DLL through the same `lgpe` CLI. This host's `PATHEXT` listed only
`.CPL`, which prevented the pinned FlatSharp target's `dotnet --list-runtimes`
command from resolving `.exe`; the wrapper adds `.EXE` for its child processes.
The native build completed with 9 upstream warnings and 0 errors. The actual
Windows run wrote `work/gamemanagergg/run-20261028T220208Z/` and passed the
same verifier: 4,663 raw comparisons, 1,963 unchanged source files, 0
mismatches.

The CLI invokes .NET 10.0.403 and builds the worker in Release mode. It emitted mirrored-in-meaning reference JSONL under `work/gamemanagergg/run-20261028T214446Z/` for 980 personal records, 743 moves, 980 learnset archive members (15,380 Move/Level pairs), 980 evolution files, and 980 mega-evolution files (1,960 entries). This is an independent pkNX check, not a replacement for the production mirrored decoder or an extra manifest `DECODED` claim.

The worker recorded SHA-256 for all **1,963 mapped input files** before parsing and after export; both maps were identical (`sourceUnchanged=true`). Representative source hashes:

| Input | SHA-256 |
|---|---|
| `bin/pokelib/personal/personal_total.bin` | `0bd93e9122b1148f5ea844a5fe35334d17680430d9164bce799dd08f6cf3cddf` |
| `bin/pokelib/waza/waza_data.bin` | `a917be5dfc325171b759d449d6acac894950828e932f639a98b1190afe979bfd` |
| `bin/archive/waza_oboe.gfpak` | `ed4c338d32f857016e8978fd888239c7505b9e8c6a8bdef754aed62c0b145647` |
| `bin/pokelib/evolution/evo_001.bin` | `1890836ad54a94b5426b0fbe51d25154b245a76b81c146570230f8d489db7887` |
| `bin/pokelib/mega_evolution/mega_001.bin` | `374708fff7719dd5979ec875d56cd2286f6d3cf7ec317a3b25632aab28ec37bb` |

The worker reassembled all 980 personal records, 743 `Move7` records, 980 `Learnset6` members, and 980 mega-evolution files byte-for-byte. `EvolutionSet7.Write()` reassembled 620/980 files exactly; the other 360 differ because the pinned parser clamps negative signed form bytes to zero. Every evolution row retains original `rawHex`, path, and hash, and the production JSON comparison confirms the same clamp rule; these are reported as normalization differences, not source corruption. GFPack entry paths remain explicitly `UNKNOWN_HASH_ONLY`; the worker retains container index, absolute path hash, compression metadata, and raw member bytes instead of assigning unhashed names.

`verify_gamemanagergg_worker.py` compared every worker raw record/file with the existing mirrored production JSON and reported **CROSS_VALIDATED, 4,663 raw comparisons, 1,963 unchanged sources, zero mismatches** on both the WSL-launched and Windows-native runs. The receipts are `work/gamemanagergg/run-20261028T214446Z/receipt.json` and `work/gamemanagergg/run-20261028T220208Z/receipt.json`; each stores both complete path/hash maps.

## Remaining limitations

Switch-Toolbox GUI batch execution is not available in the local .NET 10 environment: its attempted upstream build failed in Windows-only WinForms/WPF targets (MSB4803/MSB3822/MSB3823). Supported batches use the implemented headless readers and format-specific adapters. Some upstream Blender tools have incomplete or absent license files; the checkout remains local and source attribution is retained. The GameManagerGG worker validates structures and bytes; it does not prove additional runtime semantics or replace the production decoder. T03 is `VALIDATED` for local source provenance, reproducible builds, and adapters; the Switch-Toolbox limitation is retained above.
