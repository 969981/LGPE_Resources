# T12 — Documentation, repository history, and handoff checklist

Evidence updated 2026-10-29 (Asia/Shanghai). This task records the sustainable
project handoff state; it does not claim that all reverse-engineering topics are
finished.

## Repository and repeatability

- `README.md` documents the local 1.0.2 source boundary, read-only behavior,
  command-line workflow, generated evidence, and Windows/WSL usage.
- `tasks/INDEX.md` links T00–T12 to the measured work and outstanding research.
- `docs/research/STATUS.md` is the current source-wide status; each domain has a
  focused Txx research note.
- The Python package exposes `uv run lgpe ...`; `uv.lock` pins runtime
  dependencies. PowerShell 7 and WSL entry points are in
  `scripts/Start-Research.ps1` and `scripts/Start-Research.sh`.
- Tool source URLs, exact commits/releases, and license evidence are tracked in
  `tools/source-revisions.tsv` and `docs/research/TOOL_REVISIONS.md`.
- `.gitignore` excludes the extracted game data, decoded outputs, local tool
  checkouts/binaries, logs, work products, and generated manifests. No game
  binaries, keys, or proprietary SDK files are committed.
- Git history has separate checkpoints for baseline validation, archive
  extraction, message/game-data decoding, asset/audio samples, and decoder fixes.

## Release-readiness checklist

The current work is a research pipeline handoff, not a completed game-format
catalog. Before describing the broader research objective as complete:

- [ ] Finish a standalone pkNX/GameManagerGG headless worker; decode the learnset
  archive members and resolve currently opaque fields only with source or
  runtime evidence.
- [ ] Resolve or clearly preserve the current one-model Blender crash; obtain a
  standalone GFBCol schema/loading chain and improve particle/animation rendering.
  The 698 GFBCol roots now have schema-free JSON views but remain UNKNOWN. All 1,344 local BNTX files now decode
  to verified PNGs; the 77 former `UNSUPPORTED` rows were single-texture R16.
- [ ] Analyze Wwise HIRC/event/sequence and external media naming without guessed
  labels.
- [ ] Continue main-image xrefs to data loaders, encounter weights, catch/RNG/PID/
  EC/shiny logic, trade/GO Park, and save interfaces.
- [ ] Preserve exact per-build evidence, source/output hashes, decoder/tool
  versions, and regression coverage for any new parser.
- [ ] Re-run global receipt and typed-output checks after any manifest or output
  change; keep the source tree read-only.

## Current completion boundary

T00/T01, T02, T04–T06, and T11 have measured validation. The bounded Windows
PowerShell orchestrator run completed, and the current regression suite passes
62 tests; the WSL mapped-drive attempt waited in 9P I/O and is documented in T11.
T03, T07–T10 remain active as
indicated in `tasks/INDEX.md`. The repository is useful for repeatable incremental
research, but those open items must not be reported as completed merely because
the current pipeline is committed.
