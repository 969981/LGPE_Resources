# T02: Safe paths, receipts, and resumable work

Local inputs: the extracted 1.0.2 RomFS and ExeFS under the parent NCA folder. The source remains read-only.

## Implemented and exercised

- One-to-one exports mirror the relative source path and replace only the extension under decoded/1.0.2/{romfs,exefs}.
- GFPAK extraction uses <filename>.gfpak.contents/<stored internal path>; SARC preserves the stored path. The completed archive manifest records source hash, container entry index/path, member hash, byte range/compression evidence, and output location.
- Archive member paths reject absolute paths, traversal, Windows device names, duplicate/colliding targets, and out-of-bounds ranges. Extraction stages files before atomic publication and refuses conflicting existing outputs.
- Per-domain JSONL manifests retain source status and hashes. failures.jsonl records retryable errors; retry-failed selects only recorded sources and preserves unrelated successful rows.
- Receipts include source/output SHA256, exact tool or method, source version, and output mirror path. The verifier checks hashes and source-to-output mapping.
- Real run: 1,017 archive containers decoded into 59,121 members with 0 failures; outputs remain in the decoded mirror. Full independent liblz4 cross-check evidence is in T04-notes.md.
- Regression evidence: archive traversal/bounds/conflict tests, retry registry tests, and path-mirror tests passed.

## Durable run journal

`manifests/runs.jsonl` is an append-only, fsynced event journal. Each CLI invocation records `RUNNING` and a terminal `COMPLETED` or `FAILED` event. The orchestrated `run` command records a checkpoint after scan/plan and after each domain, registration, verification, and coverage step. An interruption leaves its last checkpoint and RUNNING state visible; completed per-domain output manifests remain the resumable source of truth. The `doctor` command was executed through the actual CLI and produced matching RUNNING/COMPLETED events. Two unit tests cover event ordering, IDs, path serialization, and failure events.

This journal is observational rather than a database lease: it does not prevent duplicate concurrent invocations. Outputs are atomically published and verified on resume.

Commands used: uv run lgpe plan; uv run lgpe decode-archives --limit 0 --execute; uv run lgpe retry-failed --execute; uv run lgpe verify.

## Native Windows receipt verification and test runner — 2026-10-29

Windows PowerShell 7 could access the same X: source tree and the configured
`D:\SDK\uv-x86_64-pc-windows-msvc\uv.exe`, although `uv` was not on PATH. With
the project environment placed in the Windows temporary directory, the
existing `scripts/Verify-Outputs.ps1` wrapper verified the historical UNC
receipts for `bin/archive/script_amx.gfpak`: **1,410 registered, 1,410
verified, 0 bad, 0 failed, 0 unsupported**. The exact invocation is:

```powershell
.\scripts\Verify-Outputs.ps1 `
  -ProjectRoot 'X:\ROMS\Nintendo Switch\Pokemon\Pokemon Lets Go Pikachu\LGPE-Research' `
  -GameRoot 'X:\ROMS\Nintendo Switch\Pokemon\Pokemon Lets Go Pikachu' `
  -SourcesFile 'docs\research\source_lists\container-receipt-wsl-smoke.txt'
```

The new `scripts/Test-Project.ps1` uses the same `ProcessStartInfo.ArgumentList`
and redirected-output pattern. The actual Windows run completed **125 tests;
124 passed, 1 skipped** because this host did not permit symlink creation. The
same suite passes **125/125** under WSL.

## Full receipt verification and WSL path normalization — 2026-10-29

The native Windows full-manifest run examined **77,714 receipts** in 27m17s.
It verified **77,697** and reported 17 path-resolution errors at JSONL lines
77,698–77,714. Those rows were registered by WSL with absolute
`/mnt/x/roms/...` source and output paths. Windows resolved them as
`X:\mnt\x\roms\...`, outside the expected roots; WSL also rejected the
lowercase `roms/...` spelling because the mounted 9P tree exposes the
canonical `ROMS/Nintendo Switch/...` case. The first run found no SHA-256
mismatches among rows it could resolve.

The verifier now recognizes POSIX WSL mount paths only when their path below
`/mnt/<drive>/` exactly matches the locally derived expected source/output
path, which must also remain inside the configured root. It maps receipts to
that local expected path and hashes the local file; it never opens the foreign
path. The regression tests reject a non-drive mount and a mismatched leaf.
The exact 17 affected ROMFS sources are recorded in
`docs/research/source_lists/posix-receipt-smoke.txt`; rerunning the verifier
on that list returned **17 registered, 17 verified, 0 bad, 0 failed, 0
unsupported** under both native PowerShell and WSL. Together with the first
run, all **77,714** registered output receipts have now had their source/output
hashes checked, with **0 hash mismatches**. No game source or decoded output
bytes changed.

Reproduce the focused Windows check from the project root with:

```powershell
.\scripts\Verify-Outputs.ps1 `
  -ProjectRoot 'X:\ROMS\Nintendo Switch\Pokemon\Pokemon Lets Go Pikachu\LGPE-Research' `
  -GameRoot 'X:\ROMS\Nintendo Switch\Pokemon\Pokemon Lets Go Pikachu' `
  -SourcesFile 'docs\research\source_lists\posix-receipt-smoke.txt'
```

Source-wide coverage remains **SCANNED 27,824; DECODED 21,093; FAILED 0;
UNKNOWN 6,731; PENDING 0; UNSUPPORTED 0; 77,714 registered outputs**.
