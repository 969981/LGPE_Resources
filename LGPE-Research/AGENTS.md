# AGENTS.md — Codex / subagents contract

## Mission

Research **Pokémon Let's Go, Pikachu! 1.0.2**, extracted on the user's own X: drive. Deliver a reproducible, versioned, batch-capable, auditable resource extraction + decoding pipeline that retains the source directory tree (except for export format extensions). Extend it later toward static & dynamic reverse engineering of personal, encounters, scripts, spawn, RNG and save-related functions. Do actual work, not just write plans.

## Location and immutable inputs

- Project root: `X:\ROMS\Nintendo Switch\Pokemon\Pokemon Lets Go Pikachu\LGPE-Research`.
- Source game root = project parent.
- Source: `../1.0.2/2b7730a9e56498bbafac2002d4908c6b_NCA/`.
- `0/` holds `main, main.npdm, rtld, sdk, subsdk0, subsdk1` (likely ExeFS; confirm).
- `1/bin/` holds RomFS game resources (likely RomFS; confirm).
- Preserve original relative path under `decoded/1.0.2/{romfs,exefs}/`; never write into `../1.0.2/`.
- This repo deliberately excludes any ROM binaries, keys, copyrighted assets, save files, proprietary DLLs, and generated extraction outputs.

## Execution: follow this order

1. Read `README.md`, `configs/project.toml`, and `docs/source_snapshot/...`; inspect `tasks/INDEX.md`.
2. `uv sync`, run tests; `uv run lgpe doctor`, `tree-catalog`, `scan`, `plan` on **real user files**. If no filesystem access, produce an exact blocker record; do not invent extracted results.
3. Start `tasks/T00...T03`, then split parallel research by independent families: GFPAK; game-data/FlatBuffers; text; model/texture/animation; audio; binary runtime. Each subtask owns its own code/docs/tests and output subset.
4. Find and verify public references and tool source code; pin revisions, licenses, build steps and CLI flags. Prefer pkNX's `GameManagerGG` and `EditorGG` paths; do not blindly reuse SV-specific parsers.
5. Implement **real** headless decoders where feasible, or stable adapters wrapping validated external tools, then actually run a small representative sample and widen in safe batches. `--dry-run` cannot count as successful extraction.
6. After every format batch run tests and `uv run lgpe verify`; report sampled good/failed/unknown counts in `docs/research/STATUS.md`.
7. Commit small changes with format/provenance evidence; mark uncertainty precisely. Never say 'all done' merely after scaffolding or scanning file names.

## Mandatory engineering requirements

- Python 3.12+, `uv`; Windows PS7 first, WSL Ubuntu 24.04 / Docker optional; .NET 10 available; Ghidra / PyGhidra only for ExeFS.
- Design non-destructive, idempotent, resumable, failure-isolated commands with exit codes and dry-run mode for converters. Use stdout for summaries; structured JSONL for results/errors.
- Source bytes must never be silently changed. For proven extraction, verify output exists, size nonzero, type/magic matches expectation, checksum recorded, test on multiple samples. Don't claim that a renamed original is 'decoded'.
- Original and decoded paths correlate unambiguously. For one-to-one: `foo.wem -> foo.wav` while maintaining parent hierarchy. For container: `foo.gfpak -> foo.gfpak.contents/<original internal name>`; normalize safe paths; record container names/hashes and each child hash.
- `bin/message/*.dat` may be linked to `.tbl`; **not all** `.dat` are message files. `.arc` != confirmed `SARC`, `.amx` != confirmed Pawn AMX, `.bin` != necessarily FlatBuffers. Determine per-sample magic+code references.
- Any attempt to decode unknown data must result in an explicit `UNSUPPORTED` or `UNKNOWN`, not empty 'success' files.
- Tool download only from trusted source upstream, never redistribute Nintendo keys/game assets/proprietary SDKs. Keep tool sources at `tools/src/`, executables at `tools/bin/`, evidence at `docs/research/` and machine-produced outputs in gitignored directories.
- Do not commit prod.keys/title.keys, NSP/XCI/NCA, decoded models/audio/text or large generated dumps. Check Git staging before every commit.
- Do not execute untrusted binaries blindly, apply scripts from arbitrary websites without inspection, install packages into the global system, or use `--force` overwrites by default.
- Keep paths with spaces quoted. For WSL use `wslpath`, don't assume X: is available as /mnt/x if it isn't mounted.
- Respect upstream licensing/attribution. Use local source and docs for research without copying proprietary game content into GitHub.

## Definition of done (overall, incremental)

- [ ] Folder discovery validated against actual v1.0.2 extraction; source manifest with exact path, sizes, types, hashes-on-demand.
- [ ] Batch scheduler with source→format→decoder→outputs provenance and retry-able errors.
- [ ] GFPAK extraction implementation tested against pkNX/Toolbox including nested names, compression and validation (if verified possible).
- [ ] Game data and text conversion in representative categories with actual structured exports, compared to pkNX outputs.
- [ ] BNTX/model/animation/audio representative exports verified as playable/viewable (do not mistake support claims for a successful run).
- [ ] Full batch run of all *supported* formats; unsupported formats remain enumerated, not silently skipped.
- [ ] Unit/regression tests and at least one round-trip/semantic check per major class where technically possible.
- [ ] ExeFS `main` imported with version-correct offsets and source references; RNG/trade/encounter analysis marked evidence levels.
- [ ] README usage, tools matrix, fail/success summary, repro commands and Git commit history.

## Evidence levels

`OBSERVED_TREE`: filename in uploaded tree only; `OBSERVED_BYTES`: inspected actual file and signature; `SOURCE_CODE`: validated upstream parser; `DECODED`: real local output; `CROSS_VALIDATED`: compared across tools or against runtime. Attach date, exact version, source path, tool commit, and sample hash to every claimed milestone.

## Subagent handoffs

For each task create `docs/research/Txx-notes.md` with: goal, examined inputs, methods, commands, commits, sample hex, outputs and hashes, tested cases, failures/unknowns, next steps. Update `tasks/INDEX.md` statuses and `docs/research/STATUS.md` after actual progress. Avoid overlapping writers in `src/lgpe_research/cli.py`; use modular files + small PR-sized changes.
