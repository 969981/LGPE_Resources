# LGPE-Research: Let's Go Pikachu 1.0.2

Windows-first, reproducible analysis of the user's already extracted ExeFS and RomFS. The source dump is read-only. Generated outputs, caches, local tool checkouts, and Ghidra projects stay under the research workspace and are excluded from Git.

## Local source and baseline

The current checkout was run against 1.0.2 NCA folder 2b7730a9e56498bbafac2002d4908c6b_NCA. The actual scan contains 27,824 files. The uploaded UTF-16 tree has 27,819 paths: all match the dump, and the five additional extensionless ExeFS files are main, rtld, sdk, subsdk0, and subsdk1. There are no zero-byte files or scan access anomalies. See docs/research/STATUS.md and docs/research/T00-notes.md.

## Repeatable workflow

From PowerShell 7:

    cd 'X:\ROMS\Nintendo Switch\Pokemon\Pokemon Lets Go Pikachu\LGPE-Research'
    uv sync
    uv run lgpe run --limit 20
    uv run python -m unittest discover -s tests -v

If `uv` is not on PowerShell's PATH, run the suite through the configured Windows SDK fallback and captured process output:

    .\scripts\Test-Project.ps1

The default run scans the actual source, catalogs the uploaded tree, compares names, writes the processing plan, and dry-runs up to 20 candidates per supported domain. It does not convert game files. Execute that bounded batch with:

    uv run lgpe run --limit 20 --execute

Run every currently compatible archive, paired message, external WEM, BNK XML, SESD BSEQ, BNTX, model, animation, particle, BFOTF OpenType and supported NX BFFNT font sheet, bounded GFBCol root-structure, and exact-build AMX compact-cell candidate with:

    uv run lgpe run --limit 0 --execute --timeout 600

The one-click scripts are scripts/Start-Research.ps1 and scripts/Start-Research.sh. In PowerShell, pass `-Limit 20` and add `-Execute` to perform conversions; `-FullSha256` opts into hashing every source file. The PowerShell script also accepts `-Timeout`, `-Blender`, `-Ffmpeg`, and `-Vgmstream`. On Windows it defaults uv to `%TEMP%\lgpe-research-win-venv`, makes the local Git executable discoverable to Python, and adds the standard executable extensions to `PATHEXT` for child processes. On WSL, make sure both project and source paths are visible; set `LGPE_GAME_ROOT` when the game's parent is not the project parent. The shell script keeps its Linux environment at `/tmp/lgpe-research-wsl-venv` by default because the mapped project drive may not support virtual-environment symlinks. Override that with `LGPE_UV_ENVIRONMENT` to use another Linux filesystem location. For real conversions, provide native tool paths with `--blender`, `--ffmpeg`, and `--vgmstream`, for example:

An exhaustive `run --limit 0 --execute` also indexes and extracts internal BNK WEM members, rebuilds the static Wwise event/media map, writes the supported-BSEQ-to-Wwise event-ID cross-reference, and analyzes raw demo-BSEQ audio candidates after conversion. Those full cross-reference stages are skipped on bounded runs.

    .\scripts\Start-Research.ps1 -Limit 20 -Execute -Timeout 600

    LGPE_GAME_ROOT=/mnt/x/ROMS/Nintendo\ Switch/Pokemon/Pokemon\ Lets\ Go\ Pikachu scripts/Start-Research.sh --limit 20

    LGPE_GAME_ROOT=/mnt/x/ROMS/Nintendo\ Switch/Pokemon/Pokemon\ Lets\ Go\ Pikachu scripts/Start-Research.sh --limit 0 --execute --timeout 600 --blender /usr/bin/blender --ffmpeg /usr/bin/ffmpeg --vgmstream /usr/local/bin/vgmstream-cli

You can also run individual domains:

    uv run lgpe decode-archives --limit 20 --execute
    uv run lgpe decode-gamedata --limit 20 --execute
    uv run lgpe decode-gamedata --limit 0 --execute --sources-file docs/research/source_lists/t07-new-gamedata.txt
    uv run lgpe decode-gamedata --limit 0 --execute --sources-file docs/research/source_lists/ahtb-unpaired-15.txt
    uv run lgpe profile-sort-string --root ..
    uv run lgpe crossref-sort-string --root ..
    uv run lgpe decode-gamedata --root .. --limit 0 --execute --sources-file configs/sort_string_sources.txt
    uv run lgpe verify --root .. --sources-file configs/sort_string_sources.txt
    uv run python scripts/research/check_item_hash_index_crossref.py
    python3 scripts/research/check_ahtb_zone_crossrefs.py
    uv run lgpe register-gamedata --sources-file docs/research/source_lists/t07-new-gamedata.txt
    .\scripts\Crosscheck-GameManagerGG.ps1
    uv run lgpe map-audio-events
    .\scripts\Map-Audio-Events.ps1
    uv run lgpe map-sequence-audio
    uv run lgpe map-demo-audio
    uv run lgpe decode-audio --limit 20 --execute
    uv run lgpe decode-wave --limit 20 --execute
    uv run lgpe decode-banks --limit 20 --execute
    uv run lgpe decode-sequences --limit 5 --execute --sources-file docs/research/source_lists/t09-bseq-smoke5.txt
    uv run lgpe decode-sequences --limit 0 --execute --sources-file docs/research/source_lists/t09-bseq-381.txt
    uv run python scripts/research/refresh_bseq_scan_signatures.py
    uv run lgpe verify --sources-file docs/research/source_lists/t09-bseq-381.txt
    uv run python scripts/research/check_bseq_outputs.py
    .\scripts\Map-Sequence-Audio.ps1
    .\scripts\Decode-BnkMedia.ps1 -SourcesFile docs/research/source_lists/t09-bnk-media-smoke5.txt -Limit 5 -Execute
    .\scripts\Decode-BnkMedia.ps1 -SourcesFile '' -Limit 0 -Execute
    .\scripts\Verify-Outputs.ps1 -SourcesFile docs/research/source_lists/t09-bnk-media-all265.txt
    .\scripts\Refresh-Coverage.ps1
    uv run lgpe decode-textures --limit 20 --execute
    uv run lgpe decode-models --limit 20 --execute
    uv run lgpe decode-fonts --limit 1 --execute
    uv run lgpe decode-fonts --limit 0 --execute
    uv run lgpe decode-bffnt --limit 0 --execute
    uv run lgpe decode-animations --limit 20 --execute
    uv run lgpe decode-particles --limit 20 --execute
    uv run lgpe decode-collisions --limit 20 --execute
    uv run lgpe verify-collisions
    uv run lgpe amx-catalog
    uv run lgpe decode-amx --limit 8 --execute --sources-file docs/research/source_lists/amx-smoke.txt
    uv run lgpe decode-amx --execute
    uv run lgpe encounter-weights
    uv run lgpe spawn-rng-crossref
    uv run lgpe save-api-crossref
    uv run lgpe save-worker-pointer-scan
    uv run lgpe retry-failed --execute
    uv run lgpe retry-failed --domain model --timeout 600 --execute
    uv run python scripts/smoke_bntx.py
    uv run python scripts/verify_asset_outputs.py

`profile-sort-string` records byte-level candidates for all 81 localized
`sort_string` DATs. `crossref-sort-string` rehashes those sources and checks
the 27 candidate sort tables against decoded same-locale message lines; it
writes an evidence manifest and does not decode them. The exact Pikachu 1.0.2
`main` trace identifies `main+0x374a90` as a bounded u16le reader for the
second resource (`*_sort_table.dat`) and `main+0x374ad0` as a pair of u16le
reads for the third (`*_initial_to_sort.dat`). Batch conversion emits 54
path-mirrored JSON files; `verify` rechecks all 54 source/output receipts and
their hashes. The 27 first resources (`*_initial_index.dat`) remain UNKNOWN:
the loader caches their buffers, but no element reader has been tied to those
buffers. The separate `zukan_sort` u16 reader is a different resource chain
and is not evidence for these files.

Use --limit 0 for all candidates in the selected domain. `--sources-file` accepts one ROMFS-relative path per line, with optional `#` comments, and lets you process or rehash an exact source set while preserving other manifest rows. `retry-failed` selects only recorded FAILED sources; add `--include-unsupported` to retry previously unsupported sources after changing an adapter. Successful retries clear matching failures while preserving other domain manifest rows.

`spawn-rng-crossref` verifies the exact Let's Go Pikachu 1.0.2 `main`, source/output hashes for personal, ordinary encounter, and event-static encounter data, pinned pkNX enum/path-mapping sources, and the SHA-guarded Ghidra trace inputs before writing `manifests/spawn_rng-value-crossref.json` (schema v10). Values `0x90..0x92` match personal-table indexes/`GoSpecies` values and `Species` values in three `EncounterStatic7b` rows. Ghidra traces the event file through its own resource loader, 64-byte record-table builder, and lookup/consumer path. The consumer's normalized `Species`/`Form` checks match two source rows (Eevee/Form 1 and Pikachu/Form 8). It writes pkNX Gender value 1 (Male) if the first read of an opaque byte returns zero; if that read is nonzero and the second read returns one, it writes 2 (Female). A follow-up traces the opaque byte getter and setter at `main+0x1ca030`/`main+0x1ca020`. At setter call `main+0xf058`, verified instructions pass constant 1, while a decompiled switch case in the same caller shows an RNG-derived boolean expression; that discrepancy and runtime object identity are unresolved. The setter caller has one data reference from writable `.data` at `main+0x15278b8`, holding its entry address, but no direct references to that data cell were found in the saved Ghidra database. A wider query finds 375 references to the containing page base (`main+0x1527000`); those do not establish access to this specific cell, so setter-cell dispatch remains unverified. The event-state owner `FUN_710028f300` is also stored at writable `.data` cell `main+0x1547368` and directly calls the event loader and consumer, but that cell has no direct incoming references. Its page has five broad references, whose inspected contexts address other offsets (`+0x1c8`, `+0x820`, and `+0x838`); event-state runtime dispatch remains unverified. A v17 exact-main Ghidra pass inspected six code-address qwords in the 64-byte window beginning at `main+0x1547348`, including incoming-reference counts (1,175 DATA references to `main+0x2a90`, 65 to `main+0x11160`, and one matching data-cell reference for each of four other targets). Function boundaries are present at `main+0x11160` and `main+0x28f300`; Ghidra has no defined function at `main+0x2a90`, `main+0x28f2e0`, `main+0x28f2f0`, or `main+0x28f6c0`. These raw pointer and instruction observations do not identify the window as a vtable or establish runtime dispatch. Runtime execution, the opaque field's meaning, and gameplay outcome remain unverified. The static-event path has no direct call to the RNG candidate; the report remains `CORRELATED_UNASSIGNED` because the candidate's data semantics and runtime reachability are not established.

The GameManagerGG worker decodes actual personal, moves, learnset, evolution, and mega-evolution inputs with pinned pkNX. It writes reference JSONL and before/after source SHA-256 receipts under `work/gamemanagergg/`; it never writes to the dump or adds production `DECODED` manifest rows. On Windows, run `scripts/Crosscheck-GameManagerGG.ps1`; it ensures a Windows uv environment exists, builds with the detected .NET SDK, then runs the CLI. On WSL, set `UV_PROJECT_ENVIRONMENT=/tmp/lgpe-research-wsl-venv` for direct `uv run` because the mapped project drive does not support `.venv` symlinks; the CLI finds Windows `dotnet.exe` and converts source/output paths when available. Run `uv run python scripts/gamedata-crosscheck/verify_gamemanagergg_worker.py . <worker-run-directory>` to compare every raw record with the existing mirrored JSON exports.

`uv run lgpe map-audio-events` validates BNK source and wwiser XML hashes against their manifests, then writes a static event/action/HIRC reachability map to ignored `manifests/wwise_event_media.jsonl`. It matches Wwise `sourceID` values to decimal `.wem` names and WAV receipts, and joins same-bank `sourceID`/DIDX media IDs only when the BNK hash matches the verified source receipt. A companion `manifests/wwise_unreferenced_wem.jsonl` checks every loose WEM absent from event-reachable media against all parsed HIRC `sourceID` values and rehashes the matching WEM/WAV receipts. Current result: seven loose WEMs lack event-graph and HIRC sourceID matches across 265 parsed banks; all seven have verified WAV outputs. This does not prove they are unused by the game. Event names remain unknown without `wwnames.db3`; static links do not establish runtime playback, sequence choice, or probability. The event map links 1,190 reachable media references to 1,109 unique internal DIDX members; 1,170 references have verified internal WAV receipts and 20 point to exact prefetch fragments that cannot be decoded standalone.

`uv run lgpe map-sequence-audio` rehashes all 265 BNK/XML pairs and all 381 BSEQ manifest sources, then validates every supported BSEQ JSON and its embedded original bytes before writing the static name/ID join to ignored `manifests/bseq_wwise_events.jsonl`. It records exact `BelugaSoundLoadBank` parser literals, FNV-1 32-bit candidates for `BelugaSoundPlaySe` parser fields, Wwise event indexes, event-to-media receipt links, and candidate-bank/source hashes. Current results: 268/268 bank-name literals match a local BNK stem; 768/949 play-event fields match an event ID in a sequence-referenced bank, and 181 are found only outside those referenced banks. Command meanings, runtime bank loading, event invocation, and playback remain unverified. On this mapped X: drive, use `scripts/Map-Sequence-Audio.ps1` from native PowerShell 7 to avoid slow WSL 9P hashing.

`uv run lgpe map-demo-audio` examines only the 28 UNSUPPORTED demo/cutscene BSEQ sources as bounded raw bytes; it does not change their decoder status. The ignored `manifests/bseq_demo_audio_candidates.json` cross-checks NUL-padded `Play_`/`Stop_` literal FNV-1 IDs against raw Wwise v128 HIRC type-4 events, verifies the linked source/XML/action/media hashes, and preserves offsets and raw windows. Current exact-source census: 206/206 candidates match local HIRC IDs across 265 banks, 22 linked XML files and 248 media receipts. Command boundaries, meanings, bank loading, invocation, timing, and playback remain UNKNOWN. On the mapped drive, use `scripts/Map-Demo-Audio.ps1` from native PowerShell 7.

`decode-bnk-media` reads Wwise v128 `DIDX`/`DATA` entries from the original BNKs, extracts exact internal media under `<bank-name>.bnk.contents/<mediaID>.wem`, and decodes complete WEMs to sibling WAV files with vgmstream. Use `--sources-file` for a bounded bank set; `--limit` round-robins over selected banks, and `0` means every member. The PowerShell wrapper uses native Windows paths for this machine's mapped X: source. The verified full batch indexed 1,109 members across 265 banks: 1,103 internal WEMs decoded, and six `PrefetchStreaming` fragments were retained as `.prefetch.bin` with source/index/prefix hashes and marked `UNSUPPORTED` for standalone WEM decoding. See `docs/research/T09-notes.md` for sample IDs, hashes, and validation. `manifests/bnk_media.jsonl` tracks each member; `manifests/bnk_media_banks.jsonl` tracks each bank. The 2,477 BNK-associated outputs passed verification. `Verify-Outputs.ps1` accepts a source list, and `Refresh-Coverage.ps1` updates the global source/output summary.

The model retry command raises the per-file Blender timeout to 600 seconds for recorded model failures. `smoke_bntx.py` converts four real local formats into temporary PNGs, checks their hashes and writes `logs/bntx-smoke.json`. `verify_asset_outputs.py` rechecks mirrored PNG/GLB paths, source/output hashes, PNG chunks/rows and GLB geometry, registers receipts for verified decoded outputs, and writes `logs/asset-output-validation.json`.

## Exact-build save API references

Run `pwsh.exe -NoProfile -ExecutionPolicy Bypass -File scripts/ghidra/Run-InspectSaveApiReferences.ps1` against the saved Ghidra project, then `uv run lgpe save-api-crossref` to write `manifests/save-api-crossref.json`. The trace is read-only and pinned to the local Let's Go Pikachu 1.0.2 `0/main` hash. It records direct API references from Ghidra's saved analysis database only: save-data ownership and runtime execution remain `UNKNOWN`/`UNVERIFIED`, and zero direct write/commit references do not rule out indirect calls.

Run `pwsh.exe -NoProfile -ExecutionPolicy Bypass -File scripts/ghidra/Run-ScanSaveWorkerPointers.ps1`, then `uv run lgpe save-worker-pointer-scan` to write `manifests/save-worker-pointer-scan.json` from the second read-only trace. Its raw scan covers the initialized Ghidra memory blocks for absolute qword and image-offset dword matches to the save worker/helpers. It also scans every executable instruction for ADR/ADRP materialization of the worker page and a nearby matching offset add. The current exact-build run found no such candidates; registration and ownership remain unresolved, and other indirect forms remain possible.

## Output and evidence layout

- manifests/files.csv: actual scan with extension, size, signature, header bytes, and optional full hash.
- manifests/plan.csv: per-source triage plan.
- manifests/outputs.jsonl and outputs.csv: one receipt per output, with exact source/output hashes, method/tool versions, source-relative path, and archive index/internal path when applicable.
- manifests/archives.jsonl, gamedata.jsonl, learnsets.jsonl, audio.jsonl, bnk.jsonl, bseq.jsonl, bnk_media_banks.jsonl, bnk_media.jsonl, wwise_event_media.jsonl, wwise_unreferenced_wem.jsonl, bseq_wwise_events.jsonl, textures.jsonl, models.jsonl, animations.jsonl, particles.jsonl, collisions.jsonl: per-domain DECODED/FAILED/UNKNOWN/UNSUPPORTED/PENDING results or static cross-reference rows. BSEQ JSON retains the complete source bytes and distinguishes byte-exact from normalized round trips; command meanings remain unverified. Collision rows may include a validated generic root-table view while retaining semantic status `UNKNOWN`; BNK media rows preserve DIDX indexes, offsets, hashes, and exact internal output paths.
- manifests/coverage.csv and coverage.summary.json: source-wide SCANNED plus current analysis status, output counts and extension coverage.
- manifests/waves.jsonl: RIFF/WAVE format inspection, MS ADPCM→PCM16 conversions, validation fields, exact source/output hashes and mirrored paths. Native PCM sources remain UNKNOWN unless converted.
- manifests/amx_headers.jsonl: AMX header observations, compact-cell decode and exact-build opcode-stream validation, source/container hashes, original member indexes, and mirrored JSON paths. VM command semantics remain unverified.
- manifests/failures.jsonl: retryable FAILED or UNSUPPORTED records.
- manifests/runs.jsonl: append-only RUNNING, per-domain CHECKPOINT, and terminal events for CLI invocations; an unfinished run remains visible after interruption.
- logs/bntx-smoke.json and logs/asset-output-validation.json: real texture conversion and typed-output verification evidence.
- decoded/1.0.2/romfs/... and decoded/1.0.2/exefs/...: generated structured outputs preserving source-relative directories and stems; one-to-many archives use original-name.contents/internal-path.
- docs/research/: sample evidence, exact tool revisions, decoder limits, and version-specific static analysis.

The archive CLI validated all 1,017 GFPAK/SARC containers and extracted 59,121 internal files. The game-data manifest currently contains 10,085 DECODED, 27 UNKNOWN, and 0 FAILED/PENDING sources. It includes 5,380 paired message files, personal/wild encounter, item, trainer, evolution, event, and move records, 15 unpaired AHTB tables, nine structural grammar DAT views, exact-main `item_hash_to_index.dat` reader evidence, and all 980 `waza_oboe.gfpak` Learnset6 records cross-validated against pinned pkNX. Opaque table fields and grammar semantics remain UNKNOWN. All 1,134 external WEM inputs and 1,103 complete internal BNK WEMs have validated WAV outputs. The separate 318-file RomFS WAVE batch verified Microsoft ADPCM and produced PCM16 WAVs; 298 were newly decoded and 20 preexisting outputs were adopted after byte-identical re-decoding. Particle and animation structure batches cover their full candidate sets. All three actual BFOTF fonts were decrypted to path-mirrored OTF files. The actual `num_00.bffnt` also decoded to a structure-preserving JSON index, its exact embedded BNTX, and a validated 512×512 PNG sheet. Other FFNT revisions and additional section variants remain UNKNOWN/UNSUPPORTED until separately verified. Latest source-wide coverage is **27,824 SCANNED; 21,843 DECODED; 0 FAILED; 5,953 UNKNOWN; 28 UNSUPPORTED; 78,504 outputs**. See `docs/research/STATUS.md` and `docs/research/T09-notes.md` for evidence and remaining limits.

## Conversion policy

- A one-to-one conversion changes only the extension and preserves the source-relative path and stem.
- GFPAK and SARC members preserve container indexes, internal paths, hashes, and source attribution under <container-name>.contents/.
- Message DAT files without a verified label pairing/envelope remain UNKNOWN. Grammar DATs have a separate, path-specific structural decoder; its second header byte, interstitial semantics, and consumer remain UNKNOWN. Unpaired AHTB TBLs can be decoded as index/hash/byte-label records while their table semantics remain unidentified; other binary formats without a validated parser remain UNKNOWN or UNSUPPORTED with original index/path evidence.
- GFBCol structural JSON records only root/vtable bounds and untyped slot-byte prefixes; it is not a collision-mesh decode and remains `UNKNOWN` until a version-matched schema is verified.
- AMX JSON expands compact 64-bit cells and indexes instruction boundaries only when checks recovered from the exact LGPE 1.0.2 `main` accept the stream; script execution and command meanings remain unverified.
- LGPE battle `.bseq` inputs with the observed `SESD` version 3 envelope are decoded to path-mirrored JSON through the pinned pbseqtool parser. Every output embeds the complete source as `raw_hex`; semantic serialize/reparse equality is checked. If pbseqtool normalizes binary representation, `byte_roundtrip_exact` is false and the original bytes remain preserved. The `bin/demo/sequence` parser failures are marked `UNSUPPORTED` under the upstream README's demo/cutscene limitation, with exact exception text retained; no game-command semantics are assigned.
- No file is treated as decoded because its suffix changed. Conversion commands validate file signatures, sizes, structures, or media samples before registering outputs.
- Every batch reads source paths under 1.0.2/NCA/0 or 1.0.2/NCA/1 and writes only beneath this project's decoded/, manifests/, logs/, or work/.
- Full SHA-256 scanning is opt-in because it reads every original file. Output receipts always hash their source and derived output.

## Tool sources and licenses

Exact source commits are listed in tools/source-revisions.tsv. Fetch public source with `scripts/Fetch-Tool-Sources.ps1` on Windows when Git is on PATH, or `bash scripts/Fetch-Tool-Sources.sh` from WSL. License observations, executable versions, sample commands, and cross-check status are in docs/research/TOOL_REVISIONS.md. The uv lock pins the pure-Python `flatbuffers` runtime required by the animation add-on and `texture2ddecoder` used for BC7. Local checkouts under tools/src/ are ignored by Git. The Blender importer and animation add-on checkouts have no root license file; they are used only from the local research setup and are not redistributed.

## Environment and limits

- Windows: PowerShell 7, Python 3.12, uv, .NET 10, Blender 5.1, FFmpeg 8, Ghidra 12.2, and a pinned vgmstream r2168 CLI were verified locally. This host's Windows PATH lacks Git, so public source revisions were fetched and recorded through the WSL helper.
- WSL: `scripts/Start-Research.sh` expects Linux uv and a source path visible inside WSL. This machine exposes the mapped source through 9P at `/mnt/x`, but a full scan waited in `p9_client_rpc` for more than eight minutes without a checkpoint. Use a performant WSL-visible mount and set `LGPE_GAME_ROOT`, or run `scripts/Start-Research.ps1` on Windows for this mapped drive.
- Ghidra addresses in T10-notes.md are exclusively for this Let's Go Pikachu 1.0.2 main, hash 1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8. String references do not yet prove runtime call behavior or table field semantics.
- Collision schema fields remain UNKNOWN. Exact-build Ghidra analysis of the LGPE 1.0.2 Battle AI loader and AMX parser supports a local compact-cell decoder and opcode-boundary validator. This exports cell values and an instruction index without executing scripts or assigning game-command semantics. BNK metadata is decoded to XML with wwiser; absent name databases are recorded as a limitation rather than replaced by guessed event names. See per-domain manifests and task status for current counts.
