# T11 — Full batches, verification, and regression

Evidence updated 2026-10-29 (Asia/Shanghai). All source paths are under the local
LGPE Pikachu 1.0.2 NCA extraction; no source files were modified. Generated
outputs and receipts are ignored by Git.

## Full source coverage

`uv run lgpe coverage` reads the current scan and domain manifests. The verified
summary is:

| Status/metric | Count |
|---|---:|
| SCANNED source files | 27,824 |
| DECODED sources | 21,068 |
| FAILED sources | 1 |
| UNKNOWN sources | 6,755 |
| UNSUPPORTED sources | 0 |
| PENDING sources | 0 |
| Registered output files | 76,984 |

Per-domain rows are in `manifests/archives.jsonl`, `gamedata.jsonl`, `learnsets.jsonl`, `audio.jsonl`,
`bnk.jsonl`, `textures.jsonl`, `models.jsonl`, `animations.jsonl`, and
`particles.jsonl`. The measured counts and limits are summarized in
`docs/research/STATUS.md`. Animation and particle sources count as structurally
decoded; playback and rendering are still unsupported.

The archive batch decoded 1,017 containers into 59,121 internal outputs. The
game-data manifest has 9,993 DECODED sources and 13 UNKNOWN rows: 5,380 paired
messages; personal/wild encounters; 1,058 items; 1,588 trainer files; 980
evolution sets; 980 mega-evolution sets; three event encounter tables; and one
WD move table with 743 records. The 1,134 WEM sources and 265 BNK sources have
validated WAV/XML outputs. Texture coverage is 1,344 decoded PNG outputs. The
77 formerly unsupported rows were single-texture R16_UNORM, not multi-texture
containers; see T08. Model coverage is 320 decoded GLB plus one
source that reproducibly crashes Blender. Full batch status is not inferred
from a dry-run.

## Output verification

The independent `scripts/verify_asset_outputs.py` audit checked all 1,344 PNG and
320 GLB outputs (1,664 total): source/output SHA256, exact mirrored paths, PNG
chunk CRCs and decompressed rows, and GLB mesh geometry. It reported zero bad
outputs. `logs/asset-output-validation.json` stores the detailed local result.

The completed `uv run lgpe verify` receipt snapshot reported **71,751 registered
and 71,751 verified outputs; `bad=0`, `errors=[]`**. Its JSON also reports
`failed_or_unsupported=79` at that earlier snapshot. The R16 retry cleared the
77 unsupported texture records; two Blender crash attempts remain for one unique
model source, so a selected `lgpe verify --sources-file docs/research/source_lists/t08-r16-all77.txt`
run reports 77/77 verified and `bad=0` but still exits 5 for that global ledger.
After the original receipt snapshot, the targeted
`register-gamedata --sources-file docs/research/source_lists/t07-new-gamedata.txt` pass
independently rehashed **1,964 new source/output pairs** (`verified=1964`,
`failed=0`), bringing the unique receipt count to 73,715. The prior 8,029
game-data outputs had separately passed the same registration check. Thus all
73,715 outputs were covered by either the global receipt snapshot or the later
targeted rehash. The learnset batch added 980 JSON outputs; `uv run lgpe verify
--sources-file docs/research/source_lists/t07-learnsets.txt` checked all 1,960
raw-member and parsed-JSON receipts for `waza_oboe.gfpak`, with `verified=1960`,
`bad=0`, and `errors=[]`. The 980 raw-member receipts overlap the earlier global
snapshot, so those runs cover the then-current 74,695 outputs. The 77 R16 PNGs
were later individually rehashed; the typed-asset audit then verified all 1,664
PNG/GLB outputs and restored 1,547 eligible asset receipts. At this T08
checkpoint output coverage was 74,772 unique files. The later full BNK-media
batch added 2,212 internal WEM/WAV/prefetch outputs; its all-265-bank
verification checked 2,477 bank-associated outputs with `bad=0`. Current output
coverage is 76,984 unique files. The only current `verify` ledger entries are
the two logged crash attempts for one model; source coverage has 1 FAILED and 0
UNSUPPORTED sources. A nonzero `verify` exit here signals that known unresolved
model outcome, not an output receipt mismatch. After changing decoders or outputs,
rerun `uv run lgpe verify` and inspect both `bad` and `failed_or_unsupported`.

## Regression and repeatable entry points

- `uv run python -m unittest discover -s tests -v`: 58 tests passed after the
  R16 decoder and provenance-preservation changes. The suite covers explicit-source list normalization,
  manifest-preserving targeted updates, learnset record parsing, container path
  and hash validation, coverage output counts, and the `lgpe run` learnset phase.
- `uv lock --check`, `python3 -m compileall -q src tests scripts/gamedata-crosscheck`,
  and `git diff --check` passed after the learnset changes.

After the T08 GFBCol root-structure addition, the `cmd_run` integration mock was
extended for the new collision phase. The full suite then passed **62 tests**
under WSL CPython 3.12.3 with uv 0.12.13 and `UV_LINK_MODE=copy`; the earlier
58-test count above is the prior checkpoint, not the current suite size.
- `uv lock --check`: dependency lock matches `pyproject.toml`.
- `bash -n scripts/Start-Research.sh scripts/*.sh`: shell syntax passed.
- PowerShell parser checks passed for the repository `.ps1` scripts.
- Linux uv 0.12.13 synchronized an isolated environment at
  `/tmp/lgpe-research-wsl-venv`; `uv run lgpe run --help` exposed the run options.
- The WSL wrapper passed shell syntax and uv sync, but a full source scan waited
  in `p9_client_rpc` on the mapped drive for 8 minutes 29 seconds without a
  checkpoint; that redundant run was terminated before decode or manifest
  writes. Use a performant WSL-visible mount or run the Windows wrapper for this
  source location.
- `scripts/Start-Research.ps1 -Limit 2` completed with exit 0 under Windows
  PowerShell 7. It rescanned 27,824 files, found 27,819/27,819 tree paths matched
  plus the five expected extensionless ExeFS paths, then exercised each domain
  adapter in bounded dry-run mode with zero failures and ran all then-current 40 tests.
- Both wrappers call the single `lgpe run` orchestrator and run the test suite
  even when orchestration returns nonzero. Use `--limit 0 --execute` for the
  full execution and `--limit 20` for a bounded dry-run.
- For incremental game-data work, `uv run lgpe decode-gamedata --limit 0
  --execute --sources-file <paths.txt>` converts only the listed ROMFS paths;
  `uv run lgpe register-gamedata --sources-file <paths.txt>` independently
  rehashes that same source set. The 1,964-file addition used this flow because
  an unfiltered repeat would re-decode the already completed 5,380 message pairs.
- For learnsets, `uv run lgpe decode-learnsets --limit 2 --execute`, then
  `--limit 20 --execute`, then `--limit 0 --execute` completed at 2, 20, and
  980 members respectively. The final manifest has 980 DECODED and 0 FAILED,
  UNKNOWN, or PENDING. `python scripts/gamedata-crosscheck/verify_pknx_learnsets.py`
  reported 15,380 entries and `CROSS_VALIDATED` with zero mismatches against
  pkNX commit `d191cd0e5c05f2af81d9a41c1f1d82e6621b351a`. The conversion uses
  the mapped `Learnset6` Move/Level pairs and terminal `FFFFFFFF`; raw bytes are
  retained, and output JSON is written beside each extracted member as
  `<member-name>.json` without changing its internal directory or index.

## Limits and re-run

`UNKNOWN` is a source-level format/decoder coverage result, not a failed decode.
`UNSUPPORTED` and `FAILED` remain explicit, with original source paths and
evidence in manifests. A future retry can be bounded to failed sources with
`uv run lgpe retry-failed --domain model --timeout 600 --execute`; unsupported
files can be included only after an adapter change using
`--include-unsupported`. Full current outputs are reproducible using
`uv run lgpe run --limit 0 --execute --timeout 600`; do not run concurrently with
other manifest writers.

## Current refresh — 2026-10-29

After the complete 265-bank internal-media pass, a fresh
`UV_PROJECT_ENVIRONMENT=/tmp/lgpe-research-wsl-venv UV_LINK_MODE=copy uv run lgpe coverage`
reported **SCANNED 27,824; DECODED 21,068; FAILED 1; UNKNOWN 6,755; PENDING 0;
UNSUPPORTED 0; 76,984 registered outputs**. The one source-level FAILED row is
the reproducible Blender crash for a single model. The subsequent AMX catalog
run scanned **712 entries**: seven loose actual AI scripts and 705 extracted
members of the xref-confirmed `script_amx.gfpak`. All 712 passed the exact-build
static header gate (0 rejects); body DECODED 0, FAILED 0, UNKNOWN 712.
Container indexes, internal paths and receipt-backed member hashes are
retained; all 705 observed member hashes match their archive receipts. These
catalog rows do not add to source-wide coverage because the archive is already
counted as one decoded source. Every AMX body remains UNKNOWN.

The current full unit suite passed **91/91** under WSL CPython 3.12.3 with uv
0.12.13. This includes actual local AMX samples, the recovered `defsize` and
name-table gate boundaries, duplicate member-path index preservation, invalid
container-receipt hash handling, source-hash preservation, and bounded
manifest updates. The gate evidence is from read-only Ghidra 12.2 analysis of the exact
`main` SHA-256 `1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8`;
the decompiled in-game parser path is documented in `docs/research/T07-notes.md`.

Reproduce the current reports without creating a `.venv` on the mapped drive:

```bash
UV_PROJECT_ENVIRONMENT=/tmp/lgpe-research-wsl-venv UV_LINK_MODE=copy uv run lgpe amx-catalog
UV_PROJECT_ENVIRONMENT=/tmp/lgpe-research-wsl-venv UV_LINK_MODE=copy uv run lgpe coverage
UV_PROJECT_ENVIRONMENT=/tmp/lgpe-research-wsl-venv UV_LINK_MODE=copy uv run python -m unittest discover -s tests -v
```

## Font batch and refreshed source inventory (2026-11-01)

The full native Windows scan after adding BFOTF/BFFNT signature identification
read **27,824 files** and exited 0. `uv run lgpe plan` catalogued 27,824
entries. `uv run lgpe compare-tree` reported **27,819 matched, 0
snapshot-only, 5 scan-only**; the five are the known extensionless ExeFS
files. `uv run lgpe coverage` now reports **27,824 SCANNED; 21,842 DECODED;
0 FAILED; 5,954 UNKNOWN; 0 PENDING; 28 UNSUPPORTED; 78,501 registered
outputs**. The three `.bfotf` files are decoded; the lone `.bffnt` remains
UNKNOWN.

The new `uv run lgpe decode-fonts --limit 0 --execute` batch wrote three
path-mirrored OTF outputs using the pinned Switch-Toolbox BFTTF transform.
`uv run lgpe verify --sources-file work/font-verify-sources.txt` checked all
three font receipts with `verified=3`, `bad=0`, and no failures. The original
font hashes are unchanged. See `docs/research/T08-notes.md` for exact paths,
hashes, and the OpenType table-directory validation.

The native Windows full suite now runs **283 tests: 282 passed, one expected
symlink-permission skip**, exit 0. This includes the `decode-fonts` CLI,
retry routing, coverage mapping, Windows-stable relative output paths, and
`lgpe run` stage integration.


## BFFNT support update — 2026-11-01

The added `decode-bffnt` command processed the actual LGPE 1.0.2
`bin/font/num_00.bffnt` sample. Its six-section NX FFNT structure, 218 CWDH
entries, three CMAPs, embedded BNTX, and 512×512 BC4 PNG were exported and
verified through three output receipts. Coverage is now **27,824 SCANNED;
21,843 DECODED; 0 FAILED; 5,953 UNKNOWN; 0 PENDING; 28 UNSUPPORTED; 78,504
outputs**. Exact hashes and commands are in
`docs/research/T08-BFFNT-notes.md`. The latest Windows suite passed **302
tests (301 passed, one expected symlink-permission skip)** at that checkpoint.
The latest full WSL rerun passed **302/302** with process-local
`safe.directory=*`. A subsequent native Windows rerun had one environment
error because the capture cross-reference CLI test could not write its
manifest through the mapped UNC share; one symlink-permission test was skipped.


## Cross-platform test isolation follow-up — 2026-11-01

The capture cross-reference CLI test now writes into a temporary project and
copies the two hash-attributed Ghidra provenance files there. Focused WSL test:
5/5 passed. The subsequent native Windows full suite passed **302 tests (301
passed, one expected symlink-permission skip)** with exit 0; the output no
longer targets the mapped repository share. The WSL full suite passed 302/302
with a process-local Git safe-directory setting.
