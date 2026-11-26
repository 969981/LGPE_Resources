# T09: raw demo BSEQ literals and Wwise event candidates

This pass reads the exact local Pikachu 1.0.2 sources without using the battle
BSEQ command dictionary for demo records. It adds `lgpe map-demo-audio`, with
`--dry-run`, and the Windows-native `scripts/Map-Demo-Audio.ps1` wrapper. It
writes only the ignored research sidecar
`manifests/bseq_demo_audio_candidates.json`; the existing BSEQ decoder receipts,
unsupported classifications, coverage and generated decoder outputs are not
updated. The standard CLI run journal still records CLI invocations.

The result is **static raw-byte / FNV-1 / HIRC-ID correspondence**. Demo command
boundaries, command meanings, adjacent numeric fields, bank loading, event
invocation, timing, runtime selection and audible playback remain **UNKNOWN**.
No command name is inferred from the battle parser. Event display names from
the absent `wwnames.db3` database remain unknown; source strings are retained
as candidate literals, rather than assigned as authoritative Wwise names.

## Actual run and reproducible commands

From the project root, run with a usable uv environment:

```powershell
uv run lgpe map-demo-audio --root ..
uv run lgpe map-demo-audio --root .. --dry-run
uv run python -m unittest discover -s tests -p 'test_bseq_demo_audio.py' -v
uv run python -m unittest discover -s tests -p 'test_bseq*.py' -v
```

The actual report and focused tests were run through native Windows uv, using
`UV_PROJECT_ENVIRONMENT=$env:TEMP/lgpe-research-win-venv`. From WSL, this wrapper
captures native subprocess stdout/stderr correctly:

```sh
pwsh.exe -NoProfile -File scripts/Map-Demo-Audio.ps1
pwsh.exe -NoProfile -File scripts/Map-Demo-Audio.ps1 -DryRun
```

The exhaustive `uv run lgpe run --limit 0 --execute` workflow now runs this
stage after the BNK-media, Wwise event-media, and supported-sequence map stages,
and records a `demo_audio_map` run-journal checkpoint. Bounded runs skip the
cross-corpus T09 maps because their inputs may be incomplete.

The WSL uv attempts entered `p9_client_rpc` I/O wait before useful output and
were terminated; the successful native run and tests are the evidence here.
No Ghidra analysis or executable changes were involved.

Successful report summary:

| Check | Actual result |
|---|---:|
| UNSUPPORTED demo source files rehashed | 28 |
| Source bytes | 264,964 |
| Sources with no bounded prefix candidate | 1 |
| Literal occurrences / distinct strings | 206 / 161 |
| Raw local BNKs rehashed and HIRC parsed | 265 |
| Linked BNK XML outputs independently rehashed | 22 |
| Distinct linked internal or loose media receipts reverified | 248 |
| Literal occurrences with raw type-4 HIRC ID candidates | 206 |
| Literal occurrences without a local type-4 ID candidate | 0 |
| Raw preceding `2700` / `2a00` occurrences | 184 / 22 |

Of the 206 occurrences, 201 have one candidate bank, one has two, and four have
four. Matching bank cardinality is not a loading/ownership assertion.

The report is **1,970,898 bytes**, SHA-256
`737e041908a7535830e75a482e1a7770f5019615fc2dc20f367e7a75844a8529`.
It includes all 28 source hashes, the source-manifest hashes, literal offsets
and raw windows, exact matching bank hashes, raw HIRC record/index/action-ID
offsets, and existing static Wwise graph/media provenance. All report paths are
source-relative or mirrored decoded paths. The report contains local research
data and is not committed.

The new focused suite passed **9/9 tests**, including three real sample links
and the actual empty-match file, plus malformed/truncated HIRC and bounded
literal rejection cases. The private-corpus tests skip when the user's dump
and receipts are unavailable. They do not ship game assets. The tests also
check that analysis leaves `manifests/bseq.jsonl` byte-identical.
The combined `test_bseq*.py` suite passed **15/15 tests** in 12.925 seconds.
The native dry-run revalidated the same inputs and returned the identical
1,970,898-byte payload SHA-256 above without writing the report again.

## Bounds and verification method

Only manifest rows with `status=UNSUPPORTED` under `bin/demo/sequence/` are
selected. Each selected source SHA-256 must match its receipt and its bytes
must carry SESD version 3 and the final `FFFFFFFF` marker. The existing corpus
has 28 such sources; all 28 keep `sourceDecoderStatus=UNSUPPORTED` in the report.
The production decoder manifest still has 353 `DECODED_EXISTING_VERIFIED` and
28 `UNSUPPORTED` rows after this run.

Candidates must start at a standalone ASCII `Play_` or `Stop_` identifier,
contain only ASCII letters/digits/underscore, terminate with NUL before byte
32, and have zero bytes through the rest of that 32-byte window. The report
retains the preceding 16 raw bytes but does not interpret them as a verified
command header. Embedded prefixes, overlong strings, absent terminators,
truncated windows and nonzero padding are rejected. This bounded rule does not
claim to find every audio-related value in the files.

Every successful local BNK source receipt is independently SHA-checked. The
new reader checks Wwise v128, all chunk bounds, HIRC count/object bounds,
duplicate object IDs and type-4 event action-array sizes. Event IDs and action
IDs are read directly from those original bytes. The hash candidate uses
lowercase ASCII/UTF-8 and FNV-1 32-bit, matching the existing pinned wwiser
method at commit `08e937b649bc7007c234bbd59e34a41d5eef3b38`.

The sidecar attaches existing Wwise graph rows only after their source/XML
hashes match, their event action IDs/offsets agree with the raw type-4 object,
and the linked XML is rehashed. Same-bank action-target and media sourceID
fields are checked directly at the recorded raw offsets. Cross-bank graph
edges remain attributed to the existing Wwise map rather than reinterpreted
as demo command semantics. For internal media, the original DIDX tuple and
DATA slice are checked against the media ID, offset, length and WEM hash;
current extracted WEM and any linked WAV hashes must match. Loose WEM and WAV
links are independently rehashed as well. The new report is not registered as
a decoded BSEQ or playable asset.

## Three exact sample links

All BSEQ paths below are under `bin/demo/sequence/`; bank paths are under
`bin/sound/NX64/wwise/bank/`. All offsets are absolute offsets in the named
source file.

| BSEQ | Source SHA-256 |
|---|---|
| `ev0050_get.bseq` | `5cee23f728c980c1830faefa688132f20e96e0e66ff253da5f733d18f96be2df` |
| `sd9060_fly.bseq` | `c5a392549c5bb5776f19591badb05a9346d553e052cf336d4b318d953e360353` |
| `sd9130_trade.bseq` | `86cad0876f07db9cbebd43c1cf3b9d3e609cc1dc39de124410e5161ba4284fdb` |

| BSEQ literal location | Literal | FNV-1 candidate ID | BNK / raw HIRC type-4 object offset |
|---|---|---:|---|
| ev0050_get `0x18c0` | `Play_ev0050_get_01` | 3182649025 (`0xbdb35ec1`) | ev0050_get_pk.bnk / 499300 |
| sd9060_fly `0x7b8` | `Play_SE_field_hiden_008_cut_in` | 4184399362 (`0xf968de02`) | System_Common.bnk / 14764292 |
| sd9130_trade `0x183c` | `Play_sd9130_trade_01` | 689516791 (`0x291930f7`) | sd9130_trade.bnk / 925790 |

The event ID field is at object offset +5; the retained report also gives each
action-ID field offset and full static graph row. Raw 16-byte contexts directly
before these literal windows are, respectively:

```text
96000000960000006400000000002700
00000000000000006400000000002700
82000000820000006400000000002700
```

| BNK | Source SHA-256 | XML SHA-256 |
|---|---|---|
| ev0050_get_pk.bnk | `2e8fa0798a427dea2a376e98df6d3b541f712aaef250e4db13a02b73ff7a8cab` | `1a3b1d282e0b05ea809b477ec89d3f5e71ccbb5eb78120d7b503c93895e349f5` |
| System_Common.bnk | `9d2ea89622c8bf9da0782ead2c675a0ddc301702995cc5cba2a71e8aff25f890` | `44cf37426b3c75c4a89b2d60a3c0336afbb81558297ecd0d3fa2b7cff215aee5` |
| sd9130_trade.bnk | `02a10a24a130ec273bb35daaa601570baa255fc84a30822a59fa7d527a04db50` | `499c570eccb3252924cc7b8d00b924aa6ad11147e2e5462341846286847944d3` |

The exact internal WEM/WAV paths are
`decoded/1.0.2/romfs/bin/sound/NX64/wwise/bank/<bank>.bnk.contents/<ID>.{wem,wav}`.

| Bank / media ID | DIDX index / DATA-relative offset / bytes | WEM SHA-256 | WAV SHA-256 |
|---|---|---|---|
| ev0050_get_pk / 26569135 | 0 / 0 / 167378 | `2d6785af0f3e6e00dc39e3203a56c51e2eb2556e8a72bf336f1737b562272ea4` | `b5b56fa8d362e80635a5cd4dd498c12d09ee5270a79bd002b0f0d19ccc1bf4b9` |
| System_Common / 453451329 | 112 / 6600352 / 89222 | `ae02f44491121565331c35434d013245f27efb6a8c6fe8580b84086c973d6cf8` | `fba61107dd6bcc27f0b1ca03cec4b3c09907335a75a21e4734d9c46b0d84950e` |
| sd9130_trade / 784726135 | 2 / 530400 / 67886 | `8914c1792c5561cab4e8c78c92681139519cbc5733db63ab286041dbbe12f503` | `80a50e2b587c4a80323e982dffaf67468720457fde31e4c92aaf77c9ccbd1829` |

The zero-prefix regression input is
`bin/demo/sequence/sd9111_evolution_after.bseq`, 3,300 bytes, source SHA-256
`3e2a832902caf2093be30735aba5aab536068ef7ca0c31a5cc69ddf2ef3640aa`.
Its source entry is retained with `NO_PREFIX_LITERAL_CANDIDATE`, zero candidates
and the original unsupported parser error. This does not establish absence of
all possible audio behavior.

## Remaining unknowns

All 28 files have the same observed SESD v3 envelope; the battle dictionary is
not a demo decoder. Direct inspection found that 14 stored `NameError` failures
mask `UnicodeDecodeError` at the initial record: the pinned parser's exception
wrapper refers to undefined `i`/`grp_num`. Other failures often read bytes of
`data:/bin/demo/res/...` strings as battle command IDs after stepping with an
inapplicable parameter size. These failures do not demonstrate malformed game
files and were not changed by this report.

Both `2700` and `2a00` precede some `Play_` and some `Stop_` candidates, so
neither is named simply as a play/stop instruction. A complete demo record
schema and an exact-build game-code consumer remain unverified. The sidecar
preserves these unknowns instead of upgrading extraction or playback claims.
