# T00 — Windows 环境及已解包资源确认

Date: 2026-10-28 (Asia/Shanghai)  
Game: Pokémon Let's Go Pikachu 1.0.2  
Project: `X:\ROMS\Nintendo Switch\Pokemon\Pokemon Lets Go Pikachu\LGPE-Research`  
Input root: `X:\ROMS\Nintendo Switch\Pokemon\Pokemon Lets Go Pikachu\1.0.2\2b7730a9e56498bbafac2002d4908c6b_NCA`

## Verified input and environment

- Windows resolves the project/input drive `X:` to `\\192.168.1.5\j\ROMS\...`; the Windows Python/uv processes can read it.
- `0/` exists and contains `main` (13,018,038 bytes), `main.npdm` (1,540), `rtld` (7,353), `sdk` (5,151,629), `subsdk0` (6,602,247), and `subsdk1` (3,344,897). `main` begins `NSO0`.
- `1/` exists and contains `bin/` and `system_resource/`.
- Drive space at inspection: 353.38 GiB free, 578.12 GiB used. Project outputs were written under the project only; no command wrote under `1.0.2/`.
- Runtime versions/paths: CPython 3.12.14 (Codex workspace runtime), uv 0.11.25 (`D:\SDK\uv-x86_64-pc-windows-msvc\uv.exe`), Git 2.45.2 (`D:\Tool\Git\cmd\git.exe`), .NET 10.0.403, PowerShell 7.6.9 (`D:\Tool\PowerShell\7\pwsh.exe`), Ghidra install folder `D:\Tool\ghidra\ghidra_12.2_PUBLIC`, Blender 5.1.2, FFmpeg 8.0.1.
- `lgpe doctor` reports `vgmstream-cli` not found on PATH. This is not a decoder test; T09 must locate or install a pinned open-source build and exercise it.
- WSL2 does not have `/mnt/x`; `wslpath -u X:\...` leaves the Windows path unchanged. A DrvFS mount attempt failed because this WSL user has no passwordless sudo. Windows executables were called directly from WSL for this run; PowerShell 7 is installed and its project script parses successfully.

## Phase 0 commands and results

| Command/work | Result |
|---|---|
| `uv sync` | PASS; created `.venv` with CPython 3.12.14 and installed the local project. uv emitted a non-fatal warning that `SSL_CERT_DIR=D:\SDK\anaconda3\Library\ssl\certs` is invalid and ignored. |
| `uv run lgpe tree-catalog` | PASS; 27,819 snapshot entries. |
| `uv run lgpe doctor --root <game-root>` | PASS; ExeFS and RomFS directories found; uv/Git/.NET found by the CLI. |
| `uv run lgpe scan --root <game-root>` | PASS; 27,824 files, 0 access anomalies, 0 zero-byte files. Probe is 64-byte header only; full hashes are blank except separately recorded samples. |
| `uv run lgpe plan` | PASS; 27,824 plan rows. |
| `uv run lgpe compare-tree` | PASS; 27,819 matched, 0 snapshot-only, 5 scan-only. |
| `uv run python -m unittest discover -s tests -v` | PASS; 7 tests. |
| PowerShell 7 parser on `scripts/Start-Research.ps1` | PASS; no parse errors. |

Snapshot reconciliation is exact: all 27,819 inventory paths match the real scan. The five scan-only records are the extensionless ExeFS files `main`, `rtld`, `sdk`, `subsdk0`, and `subsdk1`; the snapshot inventory intentionally filters entries without a suffix. Machine report: `docs/catalog/scan_snapshot_diff.json`.

## Actual signature counts and work state

- `SCANNED`: 27,824.
- `DECODED`: 0. No format decoder had yet been run during T00/T01.
- `FAILED`: 0 scan access anomalies. Decoder failures are not applicable because no decode was attempted.
- `UNKNOWN`: 15,849 header probes returned `unidentified` or `short/unknown`. This is conservative signature coverage, not a claim that those files are unsupported.
- Additional scan facts: 125 extensions map to `kind=unknown`; 0 empty files. Actual signature counts include AHTB 5,395; RIFF 1,452; BNTX 1,344; BNSH 1,335; VFXB 1,160; GFLXPACK 643; SARC 374; Wwise BKHD 265; Nintendo NSO 5; EBML/WebM 2.
- The scanner initially missed three signatures found in real bytes (`GFLXPACK`, `SARC`, `VFXB`). A regression test failed for all three before the signature table was corrected, then passed. The corrected full scan and report above were generated after the fix.

## Sample byte evidence

These hashes identify local source samples; no payload bytes are included in Git.

| NCA-relative path | bytes | observed header | SHA-256 |
|---|---:|---|---|
| `0/main` | 13,018,038 | `NSO0` | `1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8` |
| `1/bin/archive/pokemon/pm0001_00.gfpak` | 2,322,672 | `GFLXPACK` | `6310620e6eb13f3e03f4106f8d72e5fb73bf2656a4b6d16dc15a0e6897c901d4` |
| `1/bin/app/battle/bin/battle_command_00.arc` | 1,480,436 | `SARC` | `7fdd7cf1378565f8b157f07250c5592fbc391063fe6f18ac495222943159534d` |
| `1/bin/message/English/common/bag.dat` | 9,324 | `0100cf00...` | `f33db12932cb3c748dcce7f0cd7a05c71fff5f1e1ba5e4741db17c710ceeabf9` |
| `1/bin/message/English/common/bag.tbl` | 5,000 | `AHTB` | `361c1300de617190c96f330b8aae0156d9d78a5da4a6eebe786ebec544cbeb70` |
| `1/bin/app/report/bin/fxmt_3_white202_a.bntx` | 8,304 | `BNTX` | `cddc198a3878a0425b717ec83febd46645ed1b3f92d1da498758bdfbcfa26d1a` |
| `1/bin/sound/NX64/wwise/bank/1001133599.wem` | 368,150 | `RIFF/WAVE` | `a73d56ecf5db7dd8d9a6ab93080ddd1a5746fac4d37e4b65f853d856fc552022` |

Other byte-only observations: `personal_total.bin` is 82,320 bytes; each `encount_data_{p,e}.bin` is 27,848 bytes; `btl_ai_basic.amx` is 32,742 bytes; sample PTCL begins `VFXB`; sample model/animation files have no recognized magic in the current table. These are observations only, not decoded schemas.

## T00 result

Validated local source discovery, environment, baseline scan, plan, manifest comparison, and regression suite. T00 does not claim any game-format decode. T01 is validated for the current catalog/signature baseline; format decoders remain queued under T04–T10.

## T00/T01 refresh — 2026-11-01

Re-ran `uv run lgpe doctor`, `uv run lgpe tree-catalog`, a full `uv run lgpe scan --root ..`, `uv run lgpe compare-tree`, and `uv run lgpe coverage` from native PowerShell 7. The doctor found both actual partition directories. The current scan contains **27,824** files (**6 ExeFS, 27,818 RomFS**), with **0 access anomalies** and **0 zero-byte files**; `full_sha256=false`, so this is the existing 64-byte header/signature inventory rather than an all-payload hash pass. The independent tree catalog has **27,819** suffix-bearing paths: all match, with **0 snapshot-only** and the expected five scan-only extensionless ExeFS names (`main`, `rtld`, `sdk`, `subsdk0`, `subsdk1`). `main` was separately rehashed after scanning and remains `1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8`.

The global decoder coverage refresh is unchanged: **27,824 SCANNED; 21,839 DECODED; 0 FAILED; 5,957 UNKNOWN; 0 PENDING; 28 UNSUPPORTED; 78,498 registered outputs**. The scanner now uses a no-symlink `os.scandir` walk and performs full scans in bounded, ordered batches of eight concurrent probes. A real `bin/message` traversal of **10,771** files produced identical path sets in **10.583s** with the old walk and **0.054s** with `os.scandir`. On a separate **1,000-file** source sample, sequential probes took **7.524s** and eight workers took **0.448s**, with identical size/header/signature results. The full native scan fell from **10m42.9s** on the sequential probe path to **1m51.2s** with bounded concurrency; both runs reported 27,824 files and zero anomalies. Limited scans stay sequential and a regression test confirms `--limit 1` probes exactly one file.

CSV tree export now fixes LF line endings. Regenerating `snapshot_file_inventory.csv` under Windows produced bytes identical to the committed inventory. WSL focused tests passed **8/8** for the pipeline; the native Windows full suite passed **273 tests (272 passed, one expected symlink-permission skip)**. The exact reconciliation report is `docs/catalog/scan_snapshot_diff.json`; the scan journal records sequential run `3bf0ba5089bb42e8b7cc8820c19d54ed` and concurrent run `3c6f4aa9ccf2428ab0c6a74e5f492de7`.
