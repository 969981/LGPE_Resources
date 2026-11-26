# Actual progress register

The template baseline below records the state at packaging time. The dated local runs supersede its `NOT_RUN_ON_LOCAL_DUMP` note for this checkout only.

## Template baseline (2026-10-28)

- `OBSERVED_TREE`: uploaded 1.0.2 `tree /f` inspected; UTF-16 snapshot included.
- `CODE_READY`: scan, plan, tree-catalog, output ingestion, WEM wrapper, SHA receipts, verification, and tests were present.
- At packaging time, no local proprietary game resource had been analyzed.

## Local verification — 2026-10-28

| Stage | Input | Tool | SCANNED | DECODED | FAILED | UNKNOWN | Evidence |
|---|---|---|---:|---:|---:|---:|---|
| Phase 0 / T00–T01 | LGPE 1.0.2 extracted `0/` and `1/` | uv 0.11.25, CPython 3.12.14 | 27,824 | 0 | 0 scan access errors | 15,849 unrecognized/short signatures | `docs/research/T00-notes.md`, `manifests/files.csv`, `manifests/files.summary.json`, `manifests/plan.csv` |

Snapshot comparison: 27,819/27,819 paths matched. Five additional actual paths are the extensionless ExeFS files `main`, `rtld`, `sdk`, `subsdk0`, and `subsdk1`. There are 0 snapshot-only paths, 0 zero-byte files, and 0 scan access anomalies. See `docs/catalog/scan_snapshot_diff.json`.

`UNKNOWN` is the scanner's conservative signature bucket (`unidentified` + `short/unknown`); it does not mean a decoder was tried and failed or that a format is unsupported. At initial scan, `DECODED=0` and decoder `FAILED=0`.

The initial signature probe missed the observed `GFLXPACK`, `SARC`, and `VFXB` magic. A regression test reproduced the misses, the signature table was corrected, and the full manifest was regenerated. Seven initial tests passed. The inherited invalid `SSL_CERT_DIR` warning is ignored by uv; synchronization and local commands succeeded.

## Final local batch state — 2026-10-29

The source dump remains read-only. Counts below are from the actual per-domain manifests and the regenerated source-wide coverage report. `DECODED` includes previously verified outputs only where the manifest explicitly labels them `DECODED_EXISTING_VERIFIED`.

| Domain | candidates | DECODED | FAILED | UNKNOWN | PENDING | UNSUPPORTED | Notes |
|---|---:|---:|---:|---:|---:|---:|---|
| Archives (.gfpak/.arc) | 1,017 | 1,017 | 0 | 0 | 0 | 0 | 643 GFPAK + 374 SARC; 59,121 internal outputs. Two GO Park UI SARC samples rechecked 46/46 output receipts with zero mismatches. |
| Game data (messages/personal/encounters/items/trainers/evolution/moves/AHTB/grammar) | 10,020 | 10,020 | 0 | 0 | 0 | 0 | 5,380 paired message sources + 15 unpaired AHTB label tables (including `asset.tbl`) + personal/wild encounter, item, trainer, evolution, event encounter, move records, and 9 structurally decoded grammar DATs. Grammar second-byte/interstitial semantics and parser/runtime use remain UNKNOWN. `item_hash_to_index.dat` uses an exact-build reader; `field_pocket.dat` uses exact-build access evidence; `battle_pocket.dat` is a numeric byte map cross-checked against pinned pkNX. |
| Learnsets (`waza_oboe.gfpak`) | 980 | 980 | 0 | 0 | 0 | 0 | 15,380 Move/Level entries; all members compared with pinned pkNX `Learnset6`, 0 mismatches. Original internal paths, indexes, member hashes, and container hash retained. |
| WEM audio | 1,134 | 1,134 | 0 | 0 | 0 | 0 | Validated WAV outputs; 1,114 newly decoded + 20 previously verified. |
| BNK metadata | 265 | 265 | 0 | 0 | 0 | 0 | XML hierarchy parsed for all banks; 245 newly decoded + 20 previously verified. Event names remain unresolved without `wwnames.db3`. |
| BNTX textures | 1,344 | 1,344 | 0 | 0 | 0 | 0 | All 1,344 source paths now have validated PNGs. The 77 previously unresolved files were single-texture `0x0A01` R16_UNORM, not multi-texture containers; see T08. |
| GFBMDL models | 321 | 321 | 0 | 0 | 0 | 0 | 321/321 sources now have verified GLB outputs after the recorded exact-source retry. |
| GFBANM animations | 455 | 455 | 0 | 0 | 0 | 0 | All sources decoded to structure JSON; animation playback/rendering remains unsupported. |
| VFXB/PTCL particles | 1,160 | 1,160 | 0 | 0 | 0 | 0 | All section trees decoded to JSON; particle simulation/rendering remains unsupported. |
| GFBCol root structures | 698 | 0 | 0 | 698 | 0 | 0 | Version 2 JSON indexes root vectors and validates 2,219 child table envelopes across all 698 sources; slot 3 remains 8 untyped four-byte entries per file. No field names/types assigned; all sources remain UNKNOWN. See the 2026-10-30 T08 follow-up. |
| Battle AI AMX catalog entries | 712 | 712 | 0 | 0 | 0 | 0 | 7 loose files + 705 members of decoded `script_amx.gfpak`; all 712 compact-cell streams decode and pass the exact 1.0.2 opcode/bounds validator. Cell and instruction-index JSON retain source/container hashes and member paths. These rows are separate from source-wide coverage except for the seven loose files. VM execution semantics remain unknown. See T07-notes.md. |

At the AHTB checkpoint, source-wide status was **SCANNED 27,824; DECODED 21,091; FAILED 0; UNKNOWN 6,733; PENDING 0; UNSUPPORTED 0; registered decoded outputs 77,712**. Field-pocket, battle-pocket, item-hash, and grammar structural decodes later advanced that intermediate checkpoint to **SCANNED 27,824; DECODED 21,103; FAILED 0; UNKNOWN 6,721; PENDING 0; UNSUPPORTED 0; 77,724 registered outputs**; the final integrated replay totals are recorded below. The UNKNOWN count includes 3,181 `.bin` files, 698 `.gfbcol`, mixed shader/font/sequence formats, and five extensionless ExeFS files. All seven loose `.amx` sources are DECODED; the 705 members are indexed under the already decoded `script_amx.gfpak` and do not count as separate RomFS sources. GFBCol now has a version 2 schema-free root-vector and child-table-envelope JSON view, but all 698 sources remain UNKNOWN at the semantic/source-coverage level. The `.bin` coverage includes trainer, personal, wild/event encounter, evolution, mega-evolution, and move records; it is not one homogeneous format.

The independent typed-asset audit checked all **1,664 PNG/GLB outputs** (1,344 PNG and 320 GLB), including mirrored relative paths, source/output hashes, PNG CRCs and row lengths, and GLB geometry; it reported 0 output failures. Earlier archive, game-data, asset, and BNK checks covered the prior **76,984 receipts**. The AMX batch added 712 JSON receipts; targeted verification rehashed **1,410/1,410** outputs associated with the archive (705 raw members and 705 JSONs) plus **7/7** loose outputs, all with `bad=0`, `failed=0`, and `errors=[]`. At the AHTB checkpoint, its 15 verified outputs brought the total to **77,712 registered outputs**; field-pocket, battle-pocket, item-hash, and nine grammar decodes advanced that intermediate checkpoint to **77,724**. The later exhaustive replay below verified 78,104 receipts and confirms zero failed source rows; the earlier Blender model failure was resolved by the exact-source-hash compatibility patch described later in this file.

The scanner's 15,849 unidentified/short signature bucket is separate from decoder coverage and does not claim that those files share a format. GFBCol retains UNKNOWN field types/schema despite its generic root-table view; the 698-file relative-target candidate report only records aligned in-bounds calculations. The AMX catalog has seven loose files plus 705 receipt-bound archive members; all passed the exact-build header/opcode checks and now have cell/instruction-index JSON. Only the seven loose files count as separate RomFS sources; the 705 members are children of the already decoded `script_amx.gfpak`. Runtime command execution and semantics remain unknown. Structured animation/particle JSON is not a rendered asset.

Regression evidence at the prior checkpoint was 91 tests. The prior full suite passed **99/99** under WSL CPython 3.12.3 and Windows CPython 3.12.13. The latest WSL suite passes **132/132**; native Windows CPython 3.12.13 ran all 132, with 131 passed and one symlink-permission skip. The Windows run had exposed and fixed a GFBCol mirrored-path normalization bug on repeated conversion; the WSL and Windows suites cover it. The append-only run journal, bounded-run preservation, exact source-list selection, learnset and collision structure processing, worker receipt handling, grammar offset validation, and dry-run behavior are covered by CLI and unit checks. Output receipts, source hashes, per-file commands and decoder results are in ignored `manifests/`, `logs/`, `decoded/`, and `work/`; game binaries are not tracked in Git. The WSL and PowerShell entry points are in `scripts/Start-Research.sh` and `scripts/Start-Research.ps1`; see T11 for wrapper execution evidence.

T10 now has static resource-loading paths plus locally rechecked exchange-communication paths in the exact 1.0.2 `main`. The personal path reaches a `0x54`-stride buffer copy, matching 82,320 bytes = 980 × `0x54` and pinned pkNX. The exact encounter path reaches its cached path object, request vtable, and conditional `nn::fs::OpenFile`/`GetFileSize` then `nn::fs::ReadFile` helpers; the encounter call supplies a zero cache pointer, selecting the direct-read branch if dispatch occurs. Runtime branch selection and successful I/O remain unverified. New message traces locally verify a `0x10`-byte outgoing header, identifier/sequence-based receive queue filtering, the exchange state machine's two-record count, selected-record update calls, and clone-dispatch cases. PokeLDN labels informed the comparison targets only; the local code was rechecked and no protocol behavior is claimed beyond the static paths. GO Park message loading reaches `common/go_park.dat` in two local functions; all ten localized DAT/TBL pairs are marked `DECODED` and their source, companion, and output hashes rechecked with zero mismatches. The English output contains 92 unique IDs and has one unpaired label. Related particle/archive branches are static resource-path evidence only. The only direct `nn::fs::MountSaveData` caller found in the named-function references is a queued resource worker that first checks `IsSaveDataExisting`; its relationship to the player's primary save is unresolved. Current source-wide coverage is **SCANNED 27,824; DECODED 21,456; FAILED 0; UNKNOWN 6,340; PENDING 0; UNSUPPORTED 28; 78,104 receipts**. T03 is now validated: the pinned pkNX headless GameManagerGG worker processed 1,963 inputs, matched 4,663 raw records/files against existing mirrored exports, and confirmed identical before/after source hashes. T07 remains IN_PROGRESS for runtime semantics and partially opaque fields. Remaining work is tracked in `tasks/INDEX.md`: a source-backed standalone GFBCol schema plus renderer coverage (T08); Wwise event/media/sequence mapping (T09); and GO Park communication, player save ownership/write calls, catch/RNG/PID/EC/shiny, runtime paths, and broader RTTI/function-field recovery (T10). Current output coverage is substantial but does not complete the full research goal.

### T10 continuation — RNG and capture candidates (2026-10-29)

Read-only Ghidra analysis of the exact 1.0.2 `0/main` (SHA-256
`1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8`)
located a 624-word, MT19937-compatible RNG core at `0x71004e0150`, initialized
through `nn::os::GenerateRandomBytes` by integer/float wrappers. One local
random selector/callback chain was followed, along with the direct RNG
callers; none establishes a Pokémon encounter or capture use. The local
function/string table pairs `CaptureCall` with `0x71001a61e0` and
`GetCaptureResult` with `0x71001a64c0`; both decompilations terminate in
opaque request/state operations without revealing a probability formula or
direct RNG call. A `PID=` text reference resolves to NEX endpoint diagnostics
(`CID`, `PID`, `URL`), not a Pokémon identifier. Reproduction commands and
boundaries are recorded in `docs/research/T10-notes.md`; the focused Ghidra
scripts are tracked. No binary, output, or coverage count changed in this
pass. Current source-wide totals remain **SCANNED 27,824; DECODED 21,068;
FAILED 1; UNKNOWN 6,755; PENDING 0; UNSUPPORTED 0**. Capture outcomes,
encounter RNG, Pokémon PID/EC/shiny generation, save ownership/write, GO Park
communication, and runtime execution remain open.

The next exact-main follow-up traced the capture-named API entries into a 0x99-byte request/state layer. Their only recovered incoming references are the function-pointer table slots; no direct code-call references were found, though indirect dispatch remains possible. A neighboring state machine uses shared request wrappers and does not call either entry directly. No capture-result consumer or probability logic was recovered. Counts remain **SCANNED 27,824; DECODED 21,068; FAILED 1; UNKNOWN 6,755; PENDING 0; UNSUPPORTED 0**. See `docs/research/T10-notes.md` for addresses and the successful Ghidra reproduction command.

### T10 script API registry xref follow-up — 2026-10-29

The read-only Ghidra 12.2 registry pass confirmed the local table/name pairs
`MapChangeCore_`, `CaptureCall`, and `GetCaptureResult` at
`0x710153c870..0x710153c890`. Scanning the 144-byte table range and its page
references produced one direct instruction reference into the range:
`0x71001a61d4` computes the `MapChangeCore_` name pointer at
`0x710153c878`. Context windows for unowned page-base references show
neighboring page-relative offsets being written to object fields, rather than
an indexed walk of the function/name range; one mixed context remains
unclassified. No direct code-call reference to the two capture-named function
entries was recovered in this bounded search. Generic or indirect dispatch
remains possible; the table lookup/dispatcher and runtime consumer are
unresolved. Ghidra saved `/main` successfully and emitted no decompile
failures. This pass changes no decoder coverage or output receipts: totals
remain **SCANNED 27,824; DECODED 21,068; FAILED 1; UNKNOWN 6,755; PENDING 0;
UNSUPPORTED 0; 76,984 registered outputs**. Exact addresses and the
reproduction command are in `docs/research/T10-notes.md`.

### T09 continuation — static event-to-WEM map (2026-10-29)

`UV_PROJECT_ENVIRONMENT=/tmp/lgpe-research-venv uv run lgpe map-audio-events`
processed the actual 265 BNK/XML manifest pairs, verified each current BNK source
SHA-256 and streamed XML SHA-256 against recorded receipts, then wrote 2,552
event/action rows to ignored `manifests/wwise_event_media.jsonl`. All banks report
Wwise version 128 and have distinct Bank IDs. The output records 2,476 events,
2,251 distinct event-to-WEM path pairs, 1,127 referenced WEM IDs out of 1,134
audio-manifest WEM rows, and 2,438 receipt-backed WAV references. It keeps field
offsets, target IDs, declared Bank IDs, object classes, and source/output hashes;
names remain unknown because `wwnames.db3` is absent.

Unresolved rows are explicit: 138 targets are absent from their declared bank,
27 HIRC IDs are globally ambiguous, 5 IDs are not in the loaded HIRC index, 5
targets are zero/missing, 66 rows have no reachable media, and 1,160 rows contain
media IDs with no decimal WEM-manifest filename match. Seven WEM IDs do not
appear in these event graphs. The map reports static HIRC reachability only; it
does not establish playback, switch/sequence selection, probabilities, or event
names. Four unit tests cover the mapper's match/ambiguity/hash behavior; the
unit suite passed **67/67** at this map checkpoint. Current source-wide coverage remains
**SCANNED 27,824; DECODED 21,068; FAILED 1; UNKNOWN 6,755; PENDING 0;
UNSUPPORTED 0**; this analysis adds no conversion rows.

### T08/T11 GFBCol verification retry — 2026-10-29

A Windows-native PowerShell 7 run of `scripts/Verify-Collisions.ps1` completed
`uv run lgpe verify-collisions` over the actual local ROMFS without the WSL
`/mnt/x` RPC stall: `catalogued=698`, `manifest_rows=698`,
`outputs_verified=698`, `failed=0`, `pending=0`, exit code 0. This full CLI
check rehashed source/output data and reconstructed each recorded root-table
view. The initial WSL invocation remains incomplete; no source or output
coverage count changed. Current totals remain **SCANNED 27,824; DECODED
21,068; FAILED 1; UNKNOWN 6,755; PENDING 0; UNSUPPORTED 0**. Details and the
reproduction command are in `docs/research/T08-notes.md`.


### T03 continuation — read-only GameManagerGG worker (2026-10-29)

`uv run lgpe crosscheck-gamemanagergg` built the pinned worker with Windows .NET 10.0.403 and parsed personal, move, learnset, evolution, and mega-evolution data from the exact 1.0.2 RomFS. It wrote JSONL reference records and complete input SHA-256 maps under ignored `work/gamemanagergg/run-20261028T214446Z/`. The PS7 wrapper `scripts/Crosscheck-GameManagerGG.ps1` then built natively and ran the same CLI into `run-20261028T220208Z/`; the native build had 9 upstream warnings and 0 errors. Both before/after maps contain 1,963 identical source hashes, and both independent verifier runs matched 4,663 record/file raw byte sequences to production JSON. Personal (980), moves (743), learnsets (980), and mega-evolution files (980) reassembled exactly. EvolutionSet7 normalized 360 negative signed forms to zero during pkNX parsing; the corresponding raw bytes remain in JSONL, and all 980 files matched the existing decoder's source-backed normalization. The full suite passed after adding the receipt-wrapper regression test: **63/63 tests**. No source or production manifest status count changed.

### T08 exact-main GFBCol loader search — 2026-10-29

Ghidra 12.2 PUBLIC searched the exact local `0/main`, SHA-256
`1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8`, at image
base `0x7100000000`. A tracked script searched defined strings and initialized
memory for ASCII/UTF-16LE GFBCol, GFBMDL, animation, particle, and collision
names; the report records 183 matching strings, 65 xrefs, and 13 functions,
with zero literal `gfbcol`/`.gfbcol` matches. Collision toggle names reference
data but do not establish a GFBCol loader; model-path references reach
`FUN_710022aec0` but are GFBMDL-only evidence. This result excludes neither
hashed lookup nor generic dispatch. The two tested RomFS GFBCol hashes and
precise evidence are in `docs/research/T08-notes.md`. No source, outputs, or
coverage status changed; all 698 GFBCol records remain semantic `UNKNOWN`.

### T09 actual embedded Wwise media samples — 2026-10-29

The Wwise v128 parser uses each actual bank's sequential chunk table and
`DIDX`/`DATA` offsets to copy exact bounded WEM payloads, then validates and
decodes WAV with vgmstream r2168. Five sample BNKs produced a 369-member index;
9 members across all 5 banks now have WEM and PCM16 WAV outputs, **360 PENDING,
FAILED 0, UNKNOWN 0, UNSUPPORTED 0**. Targeted verification checked **23/23**
receipts (`bad=0`, no errors, exit 0). The initial WSL run was terminated after
4:53 blocked in `p9_client_rpc`; the Windows-native PowerShell retry completed.
Full top-level source coverage remains **SCANNED 27,824; DECODED 21,068; FAILED
1; UNKNOWN 6,755; PENDING 0; UNSUPPORTED 0**. Registered output receipts now
total **74,790**, up from the previous 74,772 checkpoint. New focused tests
pass **8/8**; the full current suite passes **75/75**. Full 265-bank
embedded-media extraction and WAV decoding remain in progress. See
`docs/research/T09-notes.md` and `tasks/INDEX.md` for exact sample IDs,
metadata, commands, and validation.

### T09 full bank index and 20-member tranche — 2026-10-29

The Windows-native `decode-bnk-media --limit 20 --execute` run read and
source-hash-checked all **265** BNKs, recording **257 INDEXED banks, 8
NO_INTERNAL_MEDIA banks, and 1,109 DIDX members**. With the revised
round-robin sampling, the selected tranche covered 20 distinct banks. Across
the current manifest, **23 members are DECODED/DECODED_EXISTING_VERIFIED;
1,083 are PENDING; 3 are UNSUPPORTED; FAILED 0; UNKNOWN 0**. The three
unsupported records are 14,106-byte `230260104` prefetch fragments in
`BGM_Common.bnk`, `BGM_Event.bnk`, and `FieldFootsteps_Normal.bnk`. Their local
wwiser XML marks `StreamType=1 (PrefetchStreaming)` and `uInMemoryMediaSize=
14106`; every indexed slice equals the first 14,106 bytes of the 388,742-byte
loose `230260104.wem` (SHA-256
`b0e136537c2bda562ad7b41ab707ce9133c5e59645249e987fba5fde66ec214d`). The
fragments are preserved as exact `.prefetch.bin` outputs with index/source
receipts; they are not mislabeled or sent to vgmstream as complete WEM files.

The Windows-native `Verify-Outputs.ps1` source-list run checked **65/65**
outputs for the 20-bank tranche with `bad=0`, no errors, `failed=0`,
`unsupported=3`, and exit code 0. Registered output receipts now total
**74,821**. The full unit suite passes **77/77**. Top-level RomFS/ExeFS coverage
remains **SCANNED 27,824; DECODED 21,068; FAILED 1; UNKNOWN 6,755; PENDING 0;
UNSUPPORTED 0**; the three unsupported Wwise prefetch fragments are reported
in the separate `bnk-media` member manifest. The remaining 1,083 compatible
members were queued for the all-member execution. Detailed per-bank/member rows,
source lists, and reproducible commands are recorded in T09 notes.

### T09 completed embedded-media extraction — 2026-10-29

`decode-bnk-media --limit 0 --execute` completed for all 265 Wwise v128 banks.
The member manifest contains **1,103 DECODED/DECODED_EXISTING_VERIFIED, 6
UNSUPPORTED prefetch fragments, 0 FAILED, 0 UNKNOWN, 0 PENDING**. The bank
manifest contains **257 INDEXED, 8 NO_INTERNAL_MEDIA, 0 FAILED**. Each of the
six fragments is one of two WEM IDs repeated in three banks, and matches the
byte prefix of its complete loose WEM; raw `.prefetch.bin` outputs preserve the
indexed slice and source/index/hash evidence. No partial file was renamed as a
complete `.wem` or converted to WAV.

The all-265-source verifier checked **2,477/2,477** associated outputs with
`bad=0`, `errors=[]`, `failed=0`, `unsupported=6`, exit 0. `Refresh-Coverage.ps1`
updated coverage to **27,824 SCANNED; 21,068 DECODED; 1 FAILED; 6,755 UNKNOWN;
0 PENDING; 0 top-level UNSUPPORTED; 76,984 registered outputs**. All **78 unit
tests pass**. The WSL 9P stall, Windows-native retry, complete member counts, six
prefetch cross-checks, source lists, and commands are in
`docs/research/T09-notes.md`; top-level coverage does not count the six internal
prefetch fragments as independent scanned game sources.

### T09 static event-to-DIDX cross-reference — 2026-10-29

The regenerated schema-v2 `manifests/wwise_event_media.jsonl` cross-joins
reachable media records to internal media by exact `(BankHeader ID, sourceID)`
and `(bnk_media.bank_id, bnk_media.media_id)`. It additionally requires each
member receipt's source SHA-256 to match the independently rehashed BNK. The run
parsed/hash-checked all **265/265** BNKs and XML outputs, indexed **1,109**
internal-media manifest rows with **0 source-hash mismatches**, and linked
**1,190** event-reachable media references to **1,109/1,109 unique DIDX
members**. Those occur in **1,161 event records**; **1,170** references have
verified internal WAV receipts and **20** reference six exact prefetch
fragments, correctly retained as non-decodable standalone media. Existing
external-WEM mapping is unchanged: 2,552 event/action rows, 2,251 event-to-loose
WEM pairs, and 2,438 receipt-backed external WAV references. No runtime playback
or probability claim follows. Focused mapping tests pass 8/8, covering positive
and negative bank-scoped joins, stale source hashes, prefetch fragments, and
prior HIRC/WEM cases. The full suite passes **82/82** after these additions.
Global source/output totals remain **SCANNED 27,824;
DECODED 21,068; FAILED 1; UNKNOWN 6,755; PENDING 0; 76,984 registered
outputs**; this map adds links to existing receipts, not new decoded outputs.

### T10 encounter-owner and RNG-path follow-up — 2026-10-29

Two additional read-only Ghidra 12.2 scripts ran against the exact 1.0.2
`0/main`, SHA-256
`1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8`; a
post-analysis Windows hash check returned the same value. `FUN_710013b650`
has one direct code xref in this project, from `FUN_7100005bd0` at
`0x7100005e74`. It allocates a `0x1120` object and calls the encounter-path
initializer `FUN_710012a730`, then stores the result in parent slot `+0x98`.
The next helper `FUN_710013bfa0` links other objects under mutexes and does not
read that slot, so the encounter consumer remains unidentified.

The random path is now followed from `FUN_7100ce4e90` through
`FUN_7100ce67e0`, `FUN_7100cfd450`, and `FUN_7100cfda50` to RNG wrappers
`FUN_71004e02c0`/`FUN_71004e0040` and callback insertion at `FUN_7100d030d0`.
The local code compares an opaque `+0x24` float against the random wrapper,
optionally draws below the opaque `+0x20` bound, and combines the result with
`+0x1c`; those fields and the callback owner remain unnamed. This pass found
no static link to the encounter object or direct reference to its path from
the selected RNG functions. It does not establish encounter weights, capture
probability, PID/EC, or shiny logic. New reproducible scripts are
`scripts/ghidra/InspectEncounterConsumer.java` and
`scripts/ghidra/InspectRngSelectionParents.java`; successful commands and exact
addresses are in `docs/research/T10-notes.md`. Source coverage is unchanged at
**SCANNED 27,824; DECODED 21,068; FAILED 1; UNKNOWN 6,755; PENDING 0;
UNSUPPORTED 0; 76,984 registered outputs**. The 82-test unit suite remains
green; it does not cover Ghidra script runtime.

### T10 shared capture-helper caller follow-up — 2026-10-29

Normal Ghidra full-program analysis completed and saved the existing
`LGPE102-main` project. The run emitted constructor-recovery and unread-address
diagnostics; the original extracted `0/main` SHA-256 was checked afterward and
remains `1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8`.
Six additional callsites to `FUN_710028fa10` were then recovered in local
candidate function bodies. Their state branches pass the literals `area01`,
`t001r01`, or `s001r01` and opaque constants. This confirms the helper is
shared beyond `CaptureCall`, but does not identify request semantics or show
that these callers perform capture/encounter logic. The literal tokens match
three independently decoded ROMFS archives (`area01.gfpak`, 179 members;
`s001r01.gfpak`, 228; `t001r01.gfpak`, 210) and corresponding model paths;
this is a name cross-reference only, not a decoded request schema.
`FUN_7100210e20` concretely copies a qword, scalar, two qword pairs, and a
64-byte-bounded string into local offsets `+0x00`, `+0x08`, `+0x20/+0x28`,
`+0x30/+0x38`, and `+0x40`. Those slots remain unnamed; the surrounding
`0x99`-byte copy does not establish a complete schema. The five candidate
boundaries and their callsites are recorded in `docs/research/T10-notes.md`;
the first decompilation has a type-propagation warning, with no script-level
decompile failure. The Python suite passed **82/82**; it does not cover the
Ghidra scripts. No result consumer or catch formula was found. Source-wide
totals remain **SCANNED 27,824; DECODED 21,068; FAILED 1; UNKNOWN 6,755;
PENDING 0; UNSUPPORTED 0; 76,984 registered outputs**.

### T10 request byte-span cross-check — 2026-10-29

Ghidra 12.2 headless successfully reran the smaller exact-main decompilation
set for `FUN_7100210de0`, `FUN_7100210e20`, `FUN_710024a230`,
`FUN_710024a4a0`, and `FUN_710028fa10`; the 5,412-byte caller
`FUN_71002fab90` was excluded from decompilation to avoid its roughly 58 KB
output. The 0x99-byte `FUN_710028fa10` copy starts at decompiler local
`local_100`: an 8-byte prefix, 4-byte value, a 0x80-byte array starting at
offset `+0x10`, and 9 tail bytes at `+0x90..+0x98`. The initializer and copier
write specific array slots and a 0x40-byte-bounded string at array offset
`+0x40`; the copied storage contains bytes not explicitly written in the
shown code. This is a byte-span map, not a request type or semantic schema.
The app log reports a successful save and no `DECOMPILE_FAILED`; exact
commands and write-by-write offsets are in `docs/research/T10-notes.md`.
Source-wide counts remain **SCANNED 27,824; DECODED 21,068; FAILED 1; UNKNOWN
6,755; PENDING 0; UNSUPPORTED 0; 76,984 registered outputs**. T10 remains
`IN_PROGRESS`.


### T10 capture-result entry write-path follow-up — 2026-10-29

The `GetCaptureResult`-named registry function at `0x71001a64c0` was
re-decompiled in Ghidra 12.2 against the exact 1.0.2 `main`. It reads the
qword at `param_2 + 8`, writes it to opaque state offset `+0xc8`, clears a
16-bit value at `+0xd0`, then calls a helper that stores `0x0c` at
`param_1 + 0xa4`; its C-level return is zero. The fallback decompilation uses
unresolved global labels `_DAT_000000c8` and `_DAT_000000d0`. This clarifies
the local data flow but does not identify the state fields, result format, or
runtime caller. The successful v8 run had no `DECOMPILE_FAILED` and saved
`/main`; the reproduction command and limits are in `docs/research/T10-notes.md`.
Source totals remain **SCANNED 27,824; DECODED 21,068; FAILED 1; UNKNOWN
6,755; PENDING 0; UNSUPPORTED 0; 76,984 registered outputs**. T10 remains
`IN_PROGRESS`.

### AMX decoder and cross-platform regression update — 2026-10-29

The Windows-native `decode-amx --execute` run processed all 712 catalog rows:
7 loose `.amx` sources and 705 members of `script_amx.gfpak`. All 712 emitted
compact-cell/instruction-index JSON, passed the validator recovered from the
exact LGPE 1.0.2 `main` (SHA-256
`1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8`), and
reported 0 failures. Archive verification rehashed 1,410/1,410 raw-member and
JSON receipts; loose-source verification rehashed 7/7 receipts; both reported
`bad=0` and no errors. The first prototype's false rejects were caused by an
incomplete two-cell opcode table; the final complete batch was rerun after
recovering that table from `FUN_710066ff20`. The CLI hashes the actual local
ExeFS `main` and refuses an `--execute` run unless its SHA-256 matches the
exact 1.0.2 build.

At the AMX batch checkpoint, source coverage was **SCANNED 27,824; DECODED 21,075; FAILED 1; UNKNOWN 6,748; PENDING 0; UNSUPPORTED 0**, with **77,696** registered outputs. The 99-test suite passed under WSL CPython 3.12.3 and Windows CPython 3.12.13 at that checkpoint. The Windows run also found and fixed a GFBCol path-separator mismatch on repeated batch execution; the mirrored manifest now uses normalized source-relative paths on both platforms. The one FAILED source at that checkpoint was the Blender model conversion issue later resolved in the T08 follow-up.

### T10 RTTI cross-check — 2026-10-29

The pinned PokeLDN parser decompressed the read-only local `0/main` (SHA-256
`1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8`) to a
0x160c030-byte memory-offset image (SHA-256
`32ff708cc634829aeb2e39a5f39eb156d20e16237c5996f5e1299a905ffe68e9`). Its
segment table matched the NSO header: text `(0x0, 0xd32ba8)`, rodata
`(0xd33000, 0x7f317c)`, and data `(0x1527000, 0xe5030)`. The RTTI helper found
269 `nn::pia` class names and 2,112 named virtual-function targets. Ghidra
12.2 independently verified all **276/276** type-info name strings/pointers,
**472/472** vtable headers, and **2,729/2,729** method pointers with zero
mismatches. The same pass found 269 `nn::nex` classes and 1,388 named targets;
Ghidra verified **324/324** type-info records, **500/500** vtable headers,
and **2,128/2,128** method slots with zero mismatches. At this RTTI cross-check, source-wide totals were **SCANNED 27,824; DECODED 21,075; FAILED 1; UNKNOWN 6,748; PENDING 0; UNSUPPORTED 0; 77,696 registered outputs**. RTTI names describe networking-library types; they do not identify
Pokémon field layouts or prove runtime reachability. T10 remains IN_PROGRESS.


### T10 NEX dispatch target follow-up — 2026-10-29

A version-guarded Ghidra pass checked three RTTI-derived NEX vtable entries in the same saved program for the exact local 1.0.2 `main`. `MatchmakeExtensionClient::vfunc8` at `main+0xb36610` calls `MatchMakingClient::vfunc8` at `main+0xb402f0`, which calls `SecureConnectionProtocolClient::vfunc23` at `main+0x50d730`. The latter contains pointer access at `+0x88` and an exclusive-monitor update of a referenced value at `+8`; referent semantics remain unknown. The nearby `nn::pia::clone::CloneProtocol::vfunc2` target `main+0x51c100` is a `ret`; the separate trade/clone switch is at `main+0x51c110`, with three static callers. No trade semantics are inferred from adjacency. Reproduction scripts are `scripts/ghidra/InspectPokeLdnMethodTargets.java` and `scripts/ghidra/InspectNexMatchmakingChain.java`; both enforce the recorded `main` SHA-256 and program path. The observation added no resource conversion receipts; at this pass coverage was **SCANNED 27,824; DECODED 21,075; FAILED 1; UNKNOWN 6,748; PENDING 0; UNSUPPORTED 0; 77,696 registered outputs**. T10 remains `IN_PROGRESS`.


### T07 unknown item DAT sample attempts — 2026-10-29

Three actual `UNKNOWN` inputs were retried: `bin/pokelib/item/battle_pocket.dat` (1,058 bytes), `field_pocket.dat` (1,058 bytes), and `item_hash_to_index.dat` (16,740 bytes). `UV_PROJECT_ENVIRONMENT=/tmp/lgpe-research-t07-venv uv run lgpe decode-gamedata --root .. --sources-file /tmp/lgpe-t07-unknown-samples.txt --execute` exited 0 with 0 decoded and 0 failed; all three rows remain `UNKNOWN`. The direct item decoder rejected each because the files are not exactly 0x24-byte GameManagerGG item records, and no output JSON was emitted. The note records source hashes, header bytes, pinned pkNX evidence, and the `/tmp` uv environment workaround for the `/mnt/x` symlink restriction. T07 remains `IN_PROGRESS`; its domain count remains 9,993 decoded / 13 unknown.

### T08 Blender model retry — 2026-10-29

The last failed source, `bin/field/model/s001r01/s001r0101_00.gfbmdl` (SHA-256 `8077968c4a0a0d59071df2c26bdcdecef53dd537cae814988b3d570bd45d24ff`), crashed Blender 5.1.2 at mesh 27 `plant17` while setting custom normals. A hash-gated adapter patch skips only that call for that exact source and fails closed if the pinned importer snippet changes. The resulting mirrored GLB is 5,518,860 bytes, SHA-256 `b764d3e281320ef516f982ef489309b975f638a714fa831429e10ee4c2f945c9`, and validates as 76 meshes / 96 primitives / 199 nodes. A previously successful control model exported unchanged with a matching output hash. This preserves geometry but omits application of `plant17`'s custom normals, so shading may differ. Three targeted compatibility tests pass; full asset validation reported 1,665 outputs and 0 failures. The complete 102-test WSL suite passes. Current coverage is **SCANNED 27,824; DECODED 21,076; FAILED 0; UNKNOWN 6,748; PENDING 0; UNSUPPORTED 0; 77,697 outputs**. T08 remains `IN_PROGRESS` because GFBCol high-level schemas and other format semantics remain open.

### T09 unmatched loose WEM follow-up — 2026-10-29

The real event-media mapper re-parsed 265/265 banks with 0 failures, 2,552 event/action rows, 2,251 event-to-loose-WEM path pairs, 1,190 same-bank DIDX joins, and all 1,109 internal DIDX members reached. Seven loose WEM IDs still have no direct same-ID DIDX entry or byte-identical internal bank member; this does not establish they are unused. Three selected sources were independently decoded by pinned vgmstream r2168, and their RIFF/WAVE hashes match the existing WAV receipts exactly. Event ownership and runtime playback remain unproven; `wwnames.db3` is absent. Source-wide coverage remains **SCANNED 27,824; DECODED 21,076; FAILED 0; UNKNOWN 6,748; PENDING 0; UNSUPPORTED 0; 77,697 outputs**. T09 remains `IN_PROGRESS`.


### T07 grammar DAT and unpaired asset.tbl probe — 2026-10-29

All nine real `bin/message/grammar/*.dat` files were attempted with the verified LGPE message decoder and the unpaired `bin/message/asset.tbl` as a read-only candidate. Five nonempty DATs failed the LGPE message header gate; four 2-byte DATs failed the minimum-header check. The `asset.tbl` source is 336,463 bytes with 8,290 parsed AHTB labels (840 common, 4,540 script, 2,910 debug) and no grammar path components. The upstream pokedat CLI also failed on English, French, and JPN without emitting JSON. As a positive control, paired English `go_park.dat/.tbl` decoded to 92 lines and one unpaired label. No manifest or source outputs changed: T07 remains 9,993 decoded / 13 unknown / 0 failed / 0 pending; grammar DATs and `asset.tbl` stay `UNKNOWN`.

### T08 GFBCol source-backed schema cross-check — 2026-10-29

Five actual floor, wall, zone, encounter, and large `.gfbcol` sources were rehashed against their path-mirrored JSON outputs and receipt rows; relative paths, hashes, and `UNKNOWN` labels matched. All five share the recorded generic root/vtable envelope but the slot bytes remain untyped. Pinned Switch-Toolbox `3fcb87f1fea25ad56db139b0d9577db591f54118` matched upstream master at the time of the read-only check; a source search found no standalone GFBCol reader. The available GFBMDL `CollisionGroup` table cannot be reused: its inline six-float `BoundingBox` occupies 24 bytes at offset 16, while the standalone GFBCol root object is 20 bytes. This rejects that particular schema reuse only; all 698 GFBCol sources remain high-level `UNKNOWN` and their existing generic JSON indexes are unchanged. T08 remains `IN_PROGRESS`.


### T10 encounter request-object setup cross-reference — 2026-10-29

A version-guarded Ghidra 12.2 run rechecked `main+0x13b650`, `main+0x13bfa0`, and the request-object helper targets in the exact local 1.0.2 program (base `0x7100000000`, source SHA-256 `1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8`). It confirms allocation and storage of the `0x1120`-byte request at `+0x98`, then setup of nested pointers at `request+0x58+0xe8` and `request+0x58+0xf0` through small pointer/state setters before `FUN_710013bfa0`. No record/table consumer or confirmed runtime read was identified; the fields stay opaque. Script: `scripts/ghidra/InspectEncounterResourceHelpers.java`; Ghidra decompiled all targets and saved `/main`. Coverage remains **SCANNED 27,824; DECODED 21,076; FAILED 0; UNKNOWN 6,748; PENDING 0; UNSUPPORTED 0; 77,697 outputs**. T10 remains `IN_PROGRESS`.

### T10 encounter read completion follow-up — 2026-10-29

A version-guarded Ghidra 12.2 pass on the exact 1.0.2 `main` advanced the encounter path from `FUN_710012a730` at `main+0x12a730` through `FUN_71000adc70` at `main+0xadc70`, request read vtable slot `+0x40`, `nn::fs::ReadFile`, and `nn::fs::CloseFile`. The path stores its request handle at owner offset `+0x1e8`; the allocated buffer is at request `+0x170`. Its callback function-object slots are initialized to zero, so the traced constructor waits for the request instead of registering a per-request callback. `FUN_7100023970` only closes the file. A strong but unconfirmed parser candidate at `main+0x2fdf90` traverses a buffer through `*param_2+0x98 → +0x1e8 → +0x170`; its static pointer arithmetic matches the actual 70-table FlatBuffer root vector in `encount_data_p.bin`, and it has a direct caller at `main+0x2f8a50`. Its root pointer is not tied to the owner created by `FUN_710013b650`, so no encounter-record consumer is verified. Relative dword hits resolve to `.rodata.1` FDE ranges and `.rela.dyn`/`.data` metadata, with no dispatch-table reference in the tested encodings. Load/configuration remains distinct from record parsing. The Ghidra script is `scripts/ghidra/InspectEncounterReadPath.java`; its final exact-hash run had zero decompile failures and saved `/main`. Source coverage remains **SCANNED 27,824; DECODED 21,076; FAILED 0; UNKNOWN 6,748; PENDING 0; UNSUPPORTED 0; 77,697 registered outputs**. T10 remains `IN_PROGRESS`.

### T10 encounter candidate call arguments — 2026-10-29

On the exact-hash saved Ghidra program, `TraceEncounterCandidateArguments.java` decompiled `FUN_71002f8a50` and `FUN_71002fdf90` with no failures. The parser candidate has one direct incoming reference, from `main+0x2f8e2c` in `main+0x2f8a50`; that caller has zero direct incoming references in Ghidra's saved reference database. Its call passes through the same two parameters, after `FUN_71002fd8a0` returns zero, then calls `FUN_7100300e40`. In the candidate's row-lookup path, the compared qword comes from opaque object offset `+0x3c0` (`plVar61[0x78]`); the adjacent mode value comes from `+0x3d0` (`plVar61[0x7a]`). The qword matches the archive row's first field (`ZoneID`) in the source/decoder check. This strengthens the lookup-candidate interpretation but leaves both caller dispatch/reachability and `*param_2+0x98` owner identity unresolved. Exact source hash remains `1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8`; latest log: `logs/ghidra-encounter-candidate-arguments-v4-script.log` and `logs/ghidra-encounter-candidate-arguments-v4-app.log`. Coverage remains **SCANNED 27,824; DECODED 21,076; FAILED 0; UNKNOWN 6,748; PENDING 0; UNSUPPORTED 0; 77,697 outputs**. T10 remains `IN_PROGRESS`.

### T10 encounter duration/rate lookup helper cross-check — 2026-10-29

`InspectEncounterLookupHelpers.java` decompiled two directly called functions in the exact-hash 1.0.2 Ghidra program with no failures. Both follow `PTR_DAT_71015fad08 → +0x98 → +0x1e8 → +0x170`, iterate the loaded root vector, and compare field 0 with the supplied key. Ghidra showed direct candidate calls to `FUN_7100315260` at `main+0x300bf0` and `FUN_71003154a0` at `main+0x2fe3c0`; the second helper also has a caller at `main+0x301210` in `FUN_7100300e40`. The pinned LGPE `wild.fbs` schema names field 0 `ZoneID`. After normalizing the decompiler's row-base expression (actual vtable starts four bytes after the local row-base variable), `FUN_7100315260` selects `GroundSpawnDuration` / `WaterSpawnDuration` / `SkySpawnDuration` (schema fields 5/13/36); `FUN_71003154a0` selects `GroundTableEncounterRate` / `WaterTableEncounterRate` / `SkyTableEncounterRate` (fields 6/14/37). Candidate flags test mode 2 for water and mode 3 for sky; other combinations take the ground branch. The first helper writes its selected value to state offset `param_1+0x840` (initialized to 10), and the second returns a 32-bit selected field. `scripts/research/check_encounter_lookup_fields.py` rehashed the actual `encount_data_p.bin` and mirrored decoded JSON and matched all 70 rows' `ZoneID` and six duration/rate fields (490/490; absent FlatBuffer fields use zero defaults). This is a static encounter-data accessor chain; it still does not prove runtime reachability of the orphaned caller or identify the candidate's local `*param_2+0x98` object with the global owner. Coverage remains **SCANNED 27,824; DECODED 21,076; FAILED 0; UNKNOWN 6,748; PENDING 0; UNSUPPORTED 0; 77,697 outputs**. T10 remains `IN_PROGRESS`.

### T10 encounter buffer traversal candidate — 2026-10-29

Using the exact local LGPE 1.0.2 `main` (SHA-256 `1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8`), the five-offset instruction scan found 7,288 matches in 2,217 functions. Review narrowed to 22 functions with non-stack loads of both `+0x1e8` and `+0x170`; Ghidra decompiled those plus direct caller `main+0x2f8a50` with no failures. `main+0x2fdf90` reads `*param_2+0x98`, then follows `+0x1e8` and `+0x170` to a buffer, which it parses as a root table with a vector of 32-bit table offsets while calling `main+0x3154a0` and updating an opaque state pair. Applying that pointer arithmetic to the actual `encount_data_p.bin` root yields offset `0x0c`, vtable at `0x06`, root field 0 at `0x04`, vector at `0x14`, and length 70, matching the local `EncounterArchive` output and pinned pkNX schema. The row loop's first-field qword matches the first decoded row's `ZoneID` (`0x8702ad7e67f535c3`; table `0x6b18`, vtable `0x6ac0`, field offset `0x38`), consistent with T07's pinned `wild.fbs` field 0 name; this is a binary/decoder/schema cross-check, not evidence of runtime buffer identity. `FUN_710013b650` separately stores the `encount_data_p.bin` initializer object in its owner's `+0x98` slot. This strongly supports a parser-candidate match, but `*param_2` is not statically connected to that owner, so the function is not yet a verified encounter consumer. A scan of initialized memory found no absolute qword reference to the candidate/helper functions; it found the known initializer function pointer at `0x7101527458`, showing the scan's expected positive control. No resource outputs changed; counts remain **SCANNED 27,824; DECODED 21,076; FAILED 0; UNKNOWN 6,748; PENDING 0; UNSUPPORTED 0; 77,697 registered outputs**. Reproduction commands and limits are in `docs/research/T10-notes.md`. T10 remains `IN_PROGRESS`.


### T10 encounter-slot selection follow-up — 2026-10-29

A SHA-guarded Ghidra 12.2 run (`TraceEncounterCandidateArguments.java`, v7
logs) on the exact LGPE Pikachu 1.0.2 `main` (SHA-256
`1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8`)
expanded the `main+0x2fdf90` static candidate trace. Its row mode selects
`EncounterTable.GroundTable`, `WaterTable`, or `SkyTable` (pinned `wild.fbs`
fields 10, 18, 41; default/2/3 modes respectively). The per-slot code reads
the `EncounterSlot` `Species`, `Probability`, and `Form` fields. It stores the
probability in the second 32-bit word of each 16-byte candidate record; the
selector starts at that word, advances by four words per record, rolls an
RNG-derived sum modulo 100, and picks the first cumulative probability above
the roll. This establishes what the static candidate code does, not that the
candidate is reachable during gameplay. An additional helper
`FUN_71001c4840` returns small values from opaque offsets `+0x11f8/+0x11fa`;
return value 2 changes the candidate's level handling, but the input fields
and runtime meaning remain unidentified.

`python3 scripts/research/check_encounter_lookup_fields.py` now parses the
actual `encount_data_p.bin` FlatBuffer, follows all three slot vectors for all
70 zone rows, and compares 16 zone scalars plus `Probability`, `Species`, and
`Form` for every nested slot with the existing decoded JSON and pinned pkNX
schema. It passed **5,110 scalar comparisons across 70 rows and 1,330 nested slot rows**, plus **210 Probability-sum checks** against each row’s `GroundTableRandChanceTotal`, `WaterTableRandChanceTotal`, and `SkyTableRandChanceTotal`. All matched; active/inactive totals were Ground 53×100/17×0, Water 21×100/49×0, and Sky 41×100/29×0. Source
SHA-256 is `3dac771dffee508ff8fea41d255326640aefb67c88c2d96fd1ecda7b82b1ce46`;
JSON SHA-256 is `23e429a0470a356cffe44e323e8977db0e29c94c09937758676051980df077a2`;
`wild.fbs` SHA-256 is
`0f1e114b4ef92986bb674c341dfe75e418d257f5d4a2eb6997c8b9ca629e2a1b`. The
checker also passed `python3 -m py_compile`; the full WSL unittest suite passed
102/102 with `UV_PROJECT_ENVIRONMENT=/tmp/lgpe-research-t07-venv uv run python -m unittest discover -s tests -v`.
The Ghidra pass returned exit 0,
verified the exact `main` hash, had no decompilation failures, and saved `/main`;
reproduce with:

```powershell
cmd.exe /c 'D:\Tool\ghidra\ghidra_12.2_PUBLIC\support\analyzeHeadless.bat work\ghidra-main\project LGPE102-main -process main -noanalysis -scriptPath scripts\ghidra -postScript TraceEncounterCandidateArguments.java -scriptlog logs\ghidra-encounter-candidate-arguments-v7-script.log -log logs\ghidra-encounter-candidate-arguments-v7-app.log'
```

The candidate still has only the direct incoming call from `main+0x2f8a50`,
whose direct incoming-reference count is zero; its local root buffer remains
untied to the encounter request owner. No live runtime trace or probability
semantics beyond the static code/data match is claimed. No source game data or
decoded outputs changed. Totals remain **SCANNED 27,824; DECODED 21,076;
FAILED 0; UNKNOWN 6,748; PENDING 0; UNSUPPORTED 0; 77,697 registered
outputs**. T10 remains `IN_PROGRESS`.


### T10 encounter caller range-record cross-check — 2026-10-29

The SHA-guarded `ScanEncounterVirtualTargetPointers.java` Ghidra pass also
found relative-dword candidates in `.rodata.1` for four exact-build functions:
`main+0x13c3040 → main+0x2f8a50`, `main+0x13c3268 → main+0x2fdf90`,
`main+0x13c45b8 → main+0x315260`, and
`main+0x13c45e0 → main+0x3154a0`. At each entry, the next dword is respectively
`0x41c`, `0x2ea4`, `0x240`, and `0x16c`, matching the four Ghidra function
body byte counts (1052, 11,940, 576, and 364). That adjacency identifies these
hits as function-range metadata candidates, not evidence of an indirect call
or runtime dispatch. Ghidra still reports zero direct incoming references to
`FUN_71002f8a50`; the parser has one direct call from that function. This
rechecks and narrows the earlier relative-pointer scan without changing the
reachability caveat. Reproduce with the existing `ScanEncounterVirtualTargetPointers.java`
headless command in this note and inspect
`logs/ghidra-encounter-pointer-representations-v3-script.log`.

No source files or decoded outputs changed. Coverage remains **SCANNED 27,824;
DECODED 21,076; FAILED 0; UNKNOWN 6,748; PENDING 0; UNSUPPORTED 0;
77,697 registered outputs**. T10 remains `IN_PROGRESS`.

### T10 derived encounter roll intervals — 2026-10-29

Added and ran `UV_PROJECT_ENVIRONMENT=/tmp/lgpe-research-t07-venv uv run lgpe
encounter-weights` against the actual local 1.0.2 files. The CLI verifies the
source encounter FlatBuffer, its mirrored decoded JSON, pinned pkNX `wild.fbs`
schema/commit, and exact-hash `0/main`; it reparses every row, compares the
complete parsed object with the JSON (7,982 scalar leaves), and rehashes inputs
after processing. The output CSV has **1,330 per-slot rows** with source
FlatBuffer offsets, source/schema/tool hashes, table/zone/mode/slot coordinates,
probability, and `[start,end)` ranges derived from the `main+0x2fdf90` static
candidate's modulo-100 cumulative selector. Output CSV SHA-256:
`5fa6e10403634d79d46c822bbfb8fedc622126f0510c332e5094a59528a32b4d`. The
CLI read back the CSV and verified 1,330/1,330 rows and all 210/210
mode/table groups for slot order, contiguous intervals, and probability sums.

All 70 table rows and 210 mode vectors were included; mode totals were Ground
53×100/17×0, Water 21×100/49×0, and Sky 41×100/29×0. The existing exact
source/schema checker also passed 5,110 scalar/slot comparisons and 210
probability-sum checks. The candidate and its caller remain
`UNVERIFIED_RUNTIME`: the caller has no direct incoming references in the
saved Ghidra database, and its root buffer is not connected to the constructed
encounter resource owner. This is a derived static report, not a source decode
or a confirmed gameplay probability model. Full suite: **105/105 passed**.
Source-wide counts are unchanged: **SCANNED 27,824; DECODED 21,076; FAILED 0;
UNKNOWN 6,748; PENDING 0; UNSUPPORTED 0; 77,697 registered outputs**. T10
remains `IN_PROGRESS`.

An additional SHA-guarded, read-only Ghidra 12.2 pass inspected the encounter
mode helper at `main+0x1c4840` in the exact local 1.0.2 `main`
(`1bf36681…03f1b8`). Its two signed-short inputs at `+0x11f8/+0x11fa` remain
unnamed; the observed return values are 0/1/2 under raw numeric conditions.
Eight direct references were recorded, including the parser candidate at
`main+0x2fdf90`; its `== 2` path enables additional record-relative checks.
The source values and runtime role are unresolved, and encounter caller
reachability remains unverified. Reproduction: run
`powershell.exe -ExecutionPolicy Bypass -File scripts/ghidra/Run-InspectEncounterModeHelper.ps1`.
No source or decode receipts changed. Coverage remains **SCANNED 27,824;
DECODED 21,076; FAILED 0; UNKNOWN 6,748; PENDING 0; UNSUPPORTED 0; 77,697
registered outputs**. T10 remains `IN_PROGRESS`.

The follow-up inspection traced the two encounter-helper shorts to
`FUN_71001c47d0` at `main+0x1c47d0`: it accepts inputs 76, 77, 79, and 900–902,
then writes the input to `+0x11f8` and a paired value (200, 100, or 250) to
`+0x11fa`. Its only direct call is at `main+0x1957fc`, in code Ghidra has not
assigned to a function; that call reads its input from `[x20+8]`. The six
values' semantics remain unnamed. This strengthens the field data-flow
evidence but does not resolve runtime encounter behavior. The fresh coverage
command and 105/105 test result are recorded in T10 notes. Counts remain
**SCANNED 27,824; DECODED 21,076; FAILED 0; UNKNOWN 6,748; PENDING 0;
UNSUPPORTED 0; 77,697 registered outputs**. T10 remains `IN_PROGRESS`.

T10 update (2026-10-29): a second exact-main Ghidra pass verified function
registry names `UseEncountAuxItem_`, `GetEncountAuxState_`, and
`GetRemainingEncountAuxStepCount_` beside code containing the setter call.
The six accepted values align with actual decoded English item-name entries
for Repel, Super/Max Repel, Lure, and Super/Max Lure. The paired short values
are 100/200/250; interpreting them as remaining steps is plausible from the
registered method name but remains unconfirmed. Source files, decoded outputs,
and receipts were unchanged. Coverage: SCANNED 27,824; DECODED 21,076; FAILED
0; UNKNOWN 6,748; PENDING 0; UNSUPPORTED 0; 77,697 outputs. WSL tests: 105/105.
The new `check_aux_item_crosswalk.py` verified the six source/output hashes,
byte-exact `raw_hex`, item-name indices, and receipts. T10 remains
`IN_PROGRESS`; exact addresses, hashes, and the runtime caveat are in
`docs/research/T10-notes.md`.

T10 update (2026-10-29): exact-build decompilation now confirms the encounter
aux pair's static lifecycle. `main+0x1c48b0` decrements the signed short at
`+0x11fa` while positive; `main+0x1c48d0` clears the adjacent 32-bit state word.
`main+0x3066d0` classifies the state and clears it after the decrement reaches
zero, using the stored item ID. The registered `GetRemainingEncountAuxStepCount_`
name and decoded item crosswalk support the remaining-step interpretation;
runtime cadence and reachability remain unverified. Coverage remains SCANNED
27,824; DECODED 21,076; FAILED 0; UNKNOWN 6,748; PENDING 0; UNSUPPORTED 0;
77,697 outputs. Full tests: 105/105. T10 remains `IN_PROGRESS`.

T10 update (2026-10-29): the countdown path's exact direct call chain now
reaches `FUN_71002fab90` (`main+0x2fab90`) through the function
`FUN_71002f8a50` (`main+0x2f8a50`), which has zero direct incoming references.
The caller's `main+0x2fae4c` update call is guarded by an unlabelled byte bit;
its function also calls the encounter parser candidate. This links static
control flow, not runtime execution or a confirmed per-step cadence. The large
caller decompilation warned that type propagation did not settle, so only raw
call references and instruction windows were used. Coverage unchanged:
SCANNED 27,824; DECODED 21,076; FAILED 0; UNKNOWN 6,748; PENDING 0;
UNSUPPORTED 0; 77,697 outputs. The full WSL suite passed 105/105. T10 remains
`IN_PROGRESS`.

T10 update (2026-10-29): the expiry path reaches the shared item-index helper
`FUN_71001c95f0`, with 31 direct references including the encounter parser
candidate and the aux expiry handler. It selects an opaque per-item table and
returns a packed 15-bit value; its semantics remain unknown. The result and
item ID flow to a shared keyed-record builder. The supplied key was not found
in decoded message JSON, so it is not labeled as a text ID. No data files or
manifests changed. SCANNED 27,824; DECODED 21,076; FAILED 0; UNKNOWN 6,748;
PENDING 0; UNSUPPORTED 0; 77,697 outputs. Full tests: 105/105. T10 remains
`IN_PROGRESS`.

T10 update (2026-10-29): followed the expiry record helper through
`FUN_710017b940` to its allocation/update branches. Those write opaque fields;
no message or gameplay semantics are proven, and one decompile has an indirect
jump-table warning. Ghidra exited 0 against main SHA-256
`1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8`; no
source data or manifests changed. SCANNED 27,824; DECODED 21,076; FAILED 0;
UNKNOWN 6,748; PENDING 0; UNSUPPORTED 0; 77,697 outputs. Full tests: 105/105.
T10 remains `IN_PROGRESS`.

T10 update (2026-10-29): at the parser candidate's `main+0x2fe270` callsite,
raw instructions pass `0x36a` to the shared lookup after an opaque constant
comparison; the lookup result controls a branch. The caller function has zero
direct references, and the parser decompile warns that type propagation does
not settle, so semantics and runtime reachability remain open. Ghidra exited 0
on the recorded 1.0.2 main hash. SCANNED 27,824; DECODED 21,076; FAILED 0;
UNKNOWN 6,748; PENDING 0; UNSUPPORTED 0; 77,697 outputs. Tests: 105/105.
T10 remains `IN_PROGRESS`.

T10 update (2026-10-29): independently re-decoded the original English
`itemname.dat/.tbl` pair and reproduced the existing JSON byte-for-byte. Its
row `0x36a` is labeled “Silph Scope”; this is a text-index cross-reference,
not a confirmed gameplay interpretation of the parser branch. Exact source,
companion, and output hashes are recorded in `docs/research/T10-notes.md` and
`manifests/outputs.jsonl`. Coverage unchanged: SCANNED 27,824; DECODED 21,076;
FAILED 0; UNKNOWN 6,748; PENDING 0; UNSUPPORTED 0; 77,697 outputs. T10 remains
`IN_PROGRESS`.

T10 update (2026-10-29): added and ran
`scripts/research/check_encounter_parser_label.py`. It re-decodes the actual
English message pair, matches the mirrored JSON byte-for-byte, and verifies
the 1.0.2 source/companion/output hashes and receipt for `0x36a` → “Silph
Scope”. This verifies the localized label only. Coverage unchanged: SCANNED
27,824; DECODED 21,076; FAILED 0; UNKNOWN 6,748; PENDING 0; UNSUPPORTED 0;
77,697 outputs. T10 remains `IN_PROGRESS`.

## Latest incremental verification — 2026-10-29

The actual `manifests/files.csv` inventory contains **15 unpaired AHTB `.tbl` sources**. A full stored-hash survey matched FNV-1a on **3,105/3,105 rows across 14 tables**; the 8,290 `asset.tbl` hashes did not match and remain unclassified. The decoder retains them without hash-method assumptions. The new `tbl_labels` decoder preserves each row index, 64-bit stored hash, label byte length, raw label bytes, and a CP1252 display string. Three real samples (`AreaNameHashTable.tbl`, `ZoneNameHashTable.tbl`, `asset.tbl`) decoded first; then the tracked source list `docs/research/source_lists/ahtb-unpaired-15.txt` decoded all 15 with zero failures. All 15 output paths preserve the source-relative directory and stem, with `.json` replacing `.tbl`; output bytes re-parsed identically and source/output hashes were registered. The game-data manifest now has 10,008 DECODED and 12 UNKNOWN rows (10,020 total). The nine grammar DAT files and three non-record item DAT files remain UNKNOWN. `asset.tbl` is an AHTB label table, not a verified text grammar.

`scripts/research/check_ahtb_zone_crossrefs.py` independently re-parses all 15 outputs, checks hashes/receipts/path mapping and exact-source ExeFS `main` SHA-256 `1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8`. It verifies all **257/257** ZoneName table labels against 64-bit FNV-1a and cross-checks three constants observed in Ghidra: `0x97deb1f2d0a83282` → row 134 `t005r0305`; `0x194d955fbf0a7685` → row 255 `gogo_park01`; and `0xd8652ab502b422c7` → row 256 `gogo_play01`. Ghidra records the first comparison at `main+0x2fe260`, followed by an opaque lookup call at `main+0x2fe270`; the parent candidate at `main+0x2f8a50` contains the latter two constants. These link stored hashes to byte labels only. The caller still has no direct incoming reference, so runtime reachability and gameplay meanings are not established. Reproduce the static inspection with `powershell.exe -ExecutionPolicy Bypass -File scripts/ghidra/Run-InspectEncounterModeHelper.ps1`; its latest local log is `logs/ghidra-encounter-mode-helper-v1-app.log`.

At that research checkpoint, source coverage was **SCANNED 27,824; DECODED 21,092; FAILED 0; UNKNOWN 6,732; PENDING 0; UNSUPPORTED 0; 77,713 registered outputs**. The full WSL suite then passed **112/112**. T06's paired message decoding and generic AHTB label decoding are validated as structural output; T07 and T10 runtime/gameplay semantics remain `IN_PROGRESS`.

The hash-method follow-up did not change output coverage or decoder results: **SCANNED 27,824; DECODED 21,091; FAILED 0; UNKNOWN 6,733; PENDING 0; UNSUPPORTED 0; 77,712 outputs**. `asset.tbl` remains `DECODED` at the structural AHTB-label layer; its hash method and message semantics are UNKNOWN.


### T07/T10 `field_pocket.dat` static reader and real decode — 2026-10-29

A read-only, SHA-guarded Ghidra 12.2 pass against the exact local LGPE Pikachu
1.0.2 `main` (base `0x7100000000`, SHA-256
`1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8`) traced
`FUN_710073b950`'s `field_pocket.dat` resource suffix through
`FUN_710071cec0` and `FUN_71000adc70`. The initializer copies the returned
resource bytes into `.bss` slot `0x710163ea48`; the slot is uninitialized in
the static image. `FUN_710071d1b0` bounds indices below `0x422` and returns the
indexed byte's low three bits for mode `0xb`; `FUN_710071d210` checks the same
indexed byte's sign bit. A later exact-source cross-check confirms the numeric
low-three-bit value as pkNX `Item.PocketField` for all 1,058 items. Human-readable
pocket labels and bit-7 meaning remain unresolved.
The matching actual RomFS file is 1,058 bytes, SHA-256
`07a1d8da834d426c8de16f3c4bd7d28307bc86a9e217ebf5170b09316797402b`.

The new `field_pocket()` decoder produced the path-mirrored JSON
`decoded/1.0.2/romfs/bin/pokelib/item/field_pocket.json` (SHA-256
`91afa237944aa961b959dc4f46c507ffda45f475d9fe161295661e8b1e91436a`). The
1,058 output rows preserve exact indices and bytes; all raw bytes reassemble,
low-three-bit and high-bit projections match the accessors, and the observed
`pocket_field` counts are `[23, 60, 99, 8, 14, 24, 53, 777]`. The manifest and
single output receipt match both source and output hashes. A pinned pkNX
GameManagerGG `Item.PocketField` comparison independently matched 1,058/1,058
records with zero mismatches. The selected-source batch decoded 1/1 with 0
failures; `uv run lgpe verify` reported `registered=1`, `verified=1`, `bad=0`,
`failed=0`. The complete WSL suite passes **112/112**. After regeneration,
`uv run lgpe plan` wrote 27,824 source rows
and marked `field_pocket.dat` `DECODED` with its exact 1.0.2 static-reader
method; `battle_pocket.dat` was subsequently decoded from a separate exact-source
pkNX value match; `item_hash_to_index.dat` remains `UNKNOWN`.

At that field-pocket stage, the game-data manifest was **10,009 DECODED / 11
UNKNOWN / 0 FAILED**. The current manifest and source-wide coverage after the
separate battle-pocket follow-up are recorded below. The `field_pocket.dat`
reader remains a version-specific static-code result, not runtime evidence or
a human-readable pocket enum. T07 and T10 remain `IN_PROGRESS`.

### T07 `battle_pocket.dat` initial bounded recheck — before value comparison

The exact 1.0.2 source is 1,058 bytes, SHA-256
`9e7f1132f2a67da6cd4dde7ac5bb9b96e094ca52b346d56c72544c2e885ac226`.
`gamedata_decode.item()` rejects this file because the pinned pkNX
GameManagerGG item-record path accepts only `0x24`-byte records. A tracked
single-source batch run (`docs/research/source_lists/battle-pocket-1.txt`)
reported `decoded_outputs=0`, `failed=0`; this source was size-gated before a
decoder (`selected=0`) and remains `UNKNOWN` with no mirrored JSON output.
The refreshed 27,824-row plan now gives this path the specific method
`no exact-build reader confirmed; pkNX item records require 0x24 bytes` and
status `UNKNOWN` at that earlier point; the later exact-source value comparison
and decode are recorded in the latest section below.

A bounded exact-main string search at SHA-256
`1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8` found
only `_pocket.dat` at file offset `0x7917c6`; it found no full
`battle_pocket.dat` literal. This does not exclude dynamic path construction
or a generic loader, so no unsupported-format claim is made. At that point,
coverage was SCANNED 27,824; DECODED 21,092; FAILED 0; UNKNOWN 6,732; PENDING
0; UNSUPPORTED 0; 77,713 registered outputs. The latest value-map decode and
coverage are recorded below. T07 remains `IN_PROGRESS`.

### T07 `item_hash_to_index.dat` cross-version probe — 2026-10-29

The exact 16,740-byte source SHA-256 is
`a9050fef634aa1bc2dfe34cd48781bc6357498f05133e2ac63a463be2b5f9fc0`. Pinned
pkNX `ItemHash8.GetItemHashTable` (commit
`d191cd0e5c05f2af81d9a41c1f1d82e6621b351a`, GPL-3.0) reads a count and 16-byte
rows, but its file mapping and only source caller are SWSH-only. The actual
C# cross-version probe accepted the file shape (`1,046` rows; size
`4 + count * 0x10`) and produced 1,044 dictionary entries. Row-word counts,
duplicate key `1057`, all-zero trailing words, and the output hash are saved
in ignored `work/itemhash-crossversion-probe.json`; this is not an LGPE
decoder result.

The tracked single-source batch produced `selected=0`,
`decoded_outputs=0`, `failed=0`; the source remains `UNKNOWN` and no JSON or
receipt exists. The plan now states that pkNX `ItemHash8` is SWSH-only and the
LGPE reader is unverified. A raw string scan of exact ExeFS modules found no
literal filename but cannot exclude dynamic loading. Coverage remains
SCANNED 27,824; DECODED 21,092; FAILED 0; UNKNOWN 6,732; PENDING 0;
UNSUPPORTED 0; 77,713 registered outputs. The full WSL suite passes 112/112.
T07 remains `IN_PROGRESS`.

### T07/T10 `field_pocket.dat` pkNX value cross-check — 2026-10-29

The exact 1.0.2 JSON export now uses `pocket_field` for the byte's low three
bits. Pinned pkNX commit `d191cd0e5c05f2af81d9a41c1f1d82e6621b351a` was run
against the exact RomFS `item000.dat`–`item1057.dat` set using
`Item.FromBytes(...).PocketField`; the SHA-guarded C# comparison reports
**1,058 records, 0 mismatches** against `FUN_710071d1b0`'s `raw_byte & 0x07`.
The checked `main` SHA-256 is
`1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8`, and
`field_pocket.dat` SHA-256 is
`07a1d8da834d426c8de16f3c4bd7d28307bc86a9e217ebf5170b09316797402b`.
The ordered concatenation of all 1,058 `item000.dat`–`item1057.dat` records
has SHA-256 `c15d85a4aba08aeebdceace89ba5344cd9c5068bef78cc6f448115f462f64e0f`.
The byte-preserving mirrored output is 121,874 bytes with SHA-256
`91afa237944aa961b959dc4f46c507ffda45f475d9fe161295661e8b1e91436a`.
The re-run replaced only the derived JSON after validating its prior raw-byte
round-trip and hashes; no extracted source bytes changed. The selected batch
decoded 1/1 and receipt verification returned `registered=1`, `verified=1`,
`bad=0`, `failed=0`.

This confirms the numeric `pocket_field` projection; no human-readable pocket
enum or bit-7 meaning is claimed. At that point, coverage was **SCANNED 27,824;
DECODED 21,092; FAILED 0; UNKNOWN 6,732; PENDING 0; UNSUPPORTED 0; 77,713
registered outputs**. The later battle-pocket follow-up updates the totals below. The first full-suite run caught a stale plan-method
assertion after the method text was refined; after updating the assertion, the
complete WSL regression suite passes **112/112**. T07 and T10 remain
`IN_PROGRESS`.

### T07/T10 `battle_pocket.dat` exact-source comparison and decode — 2026-10-29

The local source is 1,058 bytes with SHA-256
`9e7f1132f2a67da6cd4dde7ac5bb9b96e094ca52b346d56c72544c2e885ac226`. The
pinned pkNX GameManagerGG `Item.PocketBattle` comparison used commit
`d191cd0e5c05f2af81d9a41c1f1d82e6621b351a`, exact-build `main` SHA-256
`1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8`, and
ordered `item000.dat`–`item1057.dat` SHA-256
`c15d85a4aba08aeebdceace89ba5344cd9c5068bef78cc6f448115f462f64e0f`. Its
report is `CANDIDATE_MATCH`: **1,058 comparisons, 0 mismatches**. The exact
byte values are 0: 1,028, 1: 22, and 2: 8. The resulting JSON preserves each
index and byte and names only the numeric field `pocket_battle`; it does not
assign enum labels or claim an exact-main loader.

The selected-source batch decoded 1/1 with 0 failures. Receipt verification
reported `registered=1`, `verified=1`, `bad=0`, `failed=0`. The mirrored output
`decoded/1.0.2/romfs/bin/pokelib/item/battle_pocket.json` is 91,416 bytes with
SHA-256 `635e644885b545a0ad883f9d7082e56985909bed8d5e15d78f44c8ec32506197`;
the C# probe also reassembles its `raw_hex` and checks all 1,058 JSON records.
The regenerated plan reports the source as `DECODED` by the value-matched
byte-map method while keeping main-loader status explicit as unconfirmed.

Current game-data coverage is **10,010 DECODED / 10 UNKNOWN / 0 FAILED** of
10,020 sources. Source-wide totals are **SCANNED 27,824; DECODED 21,093;
FAILED 0; UNKNOWN 6,731; PENDING 0; UNSUPPORTED 0; 77,714 registered
outputs**. The remaining game-data UNKNOWNs are nine grammar DATs and
`item_hash_to_index.dat`. The complete WSL suite passes **114/114**. T07 and
T10 remain `IN_PROGRESS`.

## Latest incremental verification — 2026-10-29

`item_hash_to_index.dat` remains `UNKNOWN`. A loss-preserving structural
candidate report joins the candidate 32-bit value at `+8` for 1,046/1,046
records to the actual English `itemname` line index; one index (`1057`) is
duplicated, 1,045 distinct message IDs are referenced, and 13 of 1,058 message
line indexes are unreferenced. The paired `itemname.dat`/`.tbl` bytes were
re-decoded with pinned pokedat and the result exactly matched the existing
JSON. The candidate table's schema, hash algorithm, and LGPE consumer are
still unknown. The raw-row report stays under ignored `work/`.

Targeted WSL `lgpe verify` first exposed historical Windows UNC absolute paths
in `outputs.jsonl`. The verifier now maps those receipts only after checking
their path suffix against a locally derived mirrored source/output path; it
then verifies the local files and hashes. The real itemname receipt now passes at **1/1** with `bad=0`; one real
`script_amx.gfpak` member receipt, including its local container hash, also
passes **1/1** through an isolated temporary project. A broader 1,410-row WSL
receipt scan was stopped after more than five minutes because per-member path
resolution on the mapped 9P drive made no timely progress; no batch success is
claimed. Regression tests cover Windows UNC source, output, and container paths.
Full WSL suite: **121/121 passed**. Source coverage is unchanged: **SCANNED 27,824;
DECODED 21,093; FAILED 0; UNKNOWN 6,731; PENDING 0; UNSUPPORTED 0; 77,714
registered outputs**. T07 remains `IN_PROGRESS`.

### T11 native PowerShell verification — 2026-10-29

Windows PowerShell 7 used the configured absolute `uv.exe` fallback and
`scripts/Verify-Outputs.ps1` against the same X: dump and project. The first
full-manifest pass checked **77,714 receipts**, verifying **77,697** in
27m17s. Its 17 path errors were the final WSL-generated `/mnt/x/...` receipts
being misread as `X:\mnt\x\...`; no hash mismatch was reported for the other
rows. The verifier was fixed to map a WSL POSIX path only after confirming it
matches the exact expected local path below the configured root. The focused
list at `docs/research/source_lists/posix-receipt-smoke.txt` then passed
**17/17** on native Windows with 0 bad, failed, unsupported, or hash-mismatch
rows. The same focused list also passed **17/17** under WSL, where the 9P
mount's canonical directory case is checked. Across those checks, **all
77,714 registered outputs have verified source/output hashes**. The earlier
AMX sample still passes **1,410/1,410**.

`scripts/Test-Project.ps1` ran **125 tests** under Windows CPython 3.12.13:
124 passed and one symlink test was skipped because symlink creation is
unavailable to this host. WSL CPython 3.12.3 passes all **125/125**. The new
runner captures stdout/stderr from the native `uv.exe` process and uses a
temporary Windows environment when `uv` is absent from PATH. No ROM-source
bytes or decoded outputs changed. Source coverage remains **SCANNED 27,824;
DECODED 21,093; FAILED 0; UNKNOWN 6,731; PENDING 0; UNSUPPORTED 0; 77,714
registered outputs**.

### T06 `asset.tbl` literal path cross-reference — 2026-10-29

The new `scripts/research/check_asset_tbl_path_xrefs.py` re-decoded the actual
8,290-entry AHTB source and confirmed byte-for-byte reproduction of the
existing JSON and source/output manifest hashes. It compared literal
`bin/message/<label>` candidates with the current 27,818-path RomFS inventory:
**5,380 exact `.dat` matches, all 5,380 with same-stem `.tbl` companions;
2,910 no-match labels under the literal `debug` path component; 0 case-only,
ambiguous, or invalid matches.** Each of ten languages has 829 labels, 538
matching `.dat` paths and 291 unmatched `debug` labels. Full indexed results
are in ignored `work/asset-tbl-path-xref.json`; stored hash algorithm and
runtime use remain unknown. The existing `asset.tbl` row remains DECODED;
no resource coverage counts changed. Current totals remain **SCANNED 27,824;
DECODED 21,093; FAILED 0; UNKNOWN 6,731; PENDING 0; UNSUPPORTED 0; 77,714
registered outputs**.

### T07 grammar DAT probe — 2026-10-29

The new `scripts/research/probe_grammar_dat.py` read all nine actual grammar
DAT files and tested them with pinned pokedat
`bd423b2cad9aa852fddb796bbba3c5e7b381289b` and the existing LGPE message
decoder. **SCANNED 9; DECODED 0; FAILED 0; UNKNOWN 9.** Five nontrivial DATs
fail the LGPE message header/key checks; four localized files are exactly two
bytes (`00 00`) and fail as truncated inputs. All nine lack paired TBL files,
and their source hashes remained unchanged. The UTF-16 tree snapshot, scan
catalog, and actual source directory list the same nine names; scan sizes
match every source file, while the tree snapshot contains no byte sizes or
hashes. The English `itemname.dat`
positive control parses as 1,058 lines. The machine-readable probe is in
ignored `work/grammar-probe.json`; errors and hashes are in
`docs/research/T07-notes.md`. No grammar parser or format specification has
been established, so these inputs remain UNKNOWN. Overall totals remain
**SCANNED 27,824; DECODED 21,093; FAILED 0; UNKNOWN 6,731; PENDING 0;
UNSUPPORTED 0; 77,714 registered outputs**. T07 remains `IN_PROGRESS`.

### T07/T02 WSL receipt batch completed — 2026-10-29

The prior interrupted `script_amx.gfpak` receipt scan is superseded. After
adding a cached containment resolver for shared output directories and
streaming the output JSONL manifest, the real WSL command
`UV_PROJECT_ENVIRONMENT=/tmp/lgpe-research-wsl-venv uv run lgpe verify --root .. --sources-file docs/research/source_lists/container-receipt-wsl-smoke.txt`
finished with **1,410 registered; 1,410 verified; 0 bad; 0 failed; 0
unsupported** (about 4 min 28 sec on the mapped 9P drive). The resolver still
rejects leaf symlinks and parent paths outside each allowed root, and foreign
Windows UNC receipts are checked against the locally derived mirror suffix.
All **125/125** WSL unit tests pass. This verifies receipts and bytes for the
selected AMX archive outputs; it does not decode additional resources or
resolve AMX semantics. Current source-wide totals remain **SCANNED 27,824;
DECODED 21,093; FAILED 0; UNKNOWN 6,731; PENDING 0; UNSUPPORTED 0; 77,714
registered outputs**. T07 remains `IN_PROGRESS`.

### T07/T10 exact-main item-hash reader and real decode — 2026-10-29

The earlier raw `strings` negative was caused by scanning the packed ExeFS
`main` bytes: the file is an NSO beginning `NSO0`. Ghidra 12.2's Switch loader
mapped the SHA-guarded Pikachu 1.0.2 `main` (base `0x7100000000`, SHA-256
`1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8`) and
exposed the path at `main+0xf02a31`. Its xref at `main+0x1d4538` lands in
`FUN_71001d4510`. The function passes the path through `FUN_71001d4ff0` and
`FUN_71000adc70`, reads the buffer from request-object `+0x170`, uses a u32
count at file offset 0, walks 0x10-byte rows, uses each qword at `+0` in
hash-map lookup/insertion, and stores the low 16 bits of the qword at `+8` as
a `short`. The function's direct call comes from `FUN_71001d35e0` at
`main+0x1d364c`; the parent is called at `main+0x5c88` and `main+0x1d638c`.
These are static references only and do not prove runtime execution or the
hash/value semantics.

The actual RomFS table is 16,740 bytes, SHA-256
`a9050fef634aa1bc2dfe34cd48781bc6357498f05133e2ac63a463be2b5f9fc0`.
The actual batch command:

```sh
UV_PROJECT_ENVIRONMENT=/tmp/lgpe-research-env uv run lgpe decode-gamedata --root .. --sources-file docs/research/source_lists/item-hash-1.txt --execute
```

decoded 1/1 source with 0 failures. The path-mirrored JSON contains 1,046 rows and preserves the full
source and each raw row; it is 281,338 bytes, SHA-256
`db0dbd0f9340a94456c3ec8a2fe7b817035f91decc399fef32ddf41d53e0f2ad`.
Targeted `uv run lgpe verify` returned **registered=1, verified=1, bad=0,
failed=0, unsupported=0**. The low-16-bit projection numerically joins all
1,046 rows to the verified English `itemname` message lines: 1,045 distinct
values, 1057 occurs twice, and 13 lines are unreferenced. The report retains
`field_semantics_status: UNKNOWN`; no consumer semantics are assigned.

Game-data status is **10,020 SCANNED; 10,011 DECODED; 0 FAILED; 9 UNKNOWN; 0
PENDING; 0 UNSUPPORTED**. Source-wide status is **SCANNED 27,824; DECODED
21,094; FAILED 0; UNKNOWN 6,730; PENDING 0; UNSUPPORTED 0; 77,715 registered
outputs**. WSL CPython 3.12.3 passes **127/127** tests; native Windows CPython
3.12.13 reports **127 run, 126 passed, 1 symlink-permission skip**. Reproduce the static analysis with:

```powershell
pwsh.exe -NoProfile -File scripts/ghidra/Run-InspectItemHashReferences.ps1
```

Run the candidate-to-message cross-reference with:

```sh
uv run python scripts/research/check_item_hash_index_crossref.py
```

T07/T10 remain `IN_PROGRESS`.

### T08 schema-free GFBCol root-slot probe — 2026-10-29

The read-only Windows command `pwsh.exe -NoProfile -File scripts/Probe-GFBCol-Offsets.ps1` inspected all **698 actual GFBCol sources** from the inventory and recorded a SHA-256 for each. All four root-table slots were present in every source. When each raw slot u32 is treated as a hypothetical forward-relative displacement, **2,792/2,792 candidate targets** are within the source and 4-byte aligned; the first u32 at each candidate target also passes a one-byte minimum-bound check. Per-slot first-u32 counts are slot 0: 1→603 / 2→81 / 3→14; slot 1: 1→692 / 2→4 / 3→2; slot 2: 1→692 / 2→4 / 3→2; slot 3: 8→698. These are candidate observations only; no vectors, element strides, field names, or collision meanings are assigned, and coverage remains **SCANNED 27,824; DECODED 21,094; FAILED 0; UNKNOWN 6,730; PENDING 0; UNSUPPORTED 0; 77,715 receipts**. The ignored report `work/gfbcol-relative-target-probe.json` has SHA-256 `72f545463c7c8996c568ff55ecad88432ea2c97662d72a5dc3f592f4267e1c6b`. WSL's attempt was interrupted in `Path.resolve()` on the mapped 9P tree; the native PowerShell wrapper completed using the separate Windows uv environment. The latest full suite passes **128/128** under WSL CPython 3.12.3; Windows CPython 3.12.13 reports **128 run, 127 passed, 1 symlink-permission skip**. T08 remains `IN_PROGRESS`.

### T07 grammar structural decoder and exact-build path evidence — 2026-10-29

The prior grammar probe rejected the files only as inputs to the LGPE message
DAT/TBL reader; this pass separately decoded all nine actual
`bin/message/grammar/*.dat` files with a path-specific structural reader. The
three-file smoke batch (English, Italian, JPN) decoded and verified 3/3. The
tracked nine-file list then decoded all 9 with **0 FAILED**, and
`uv run lgpe verify` returned **9 registered, 9 verified, 0 bad, 0 failed,
0 unsupported**. The one-to-one outputs are
`decoded/1.0.2/romfs/bin/message/grammar/<language>.json`, preserving source
stem and relative directories. Each JSON carries the exact source `raw_hex`,
raw segment bytes, and opaque interstitial bytes. Its `raw_hex` reassembles to
the corresponding source exactly. The previous read-only probe's hashes match
all nine batch source hashes; the post-decode source check also passed. Per-file
source hashes, sizes, segment counts, and output hashes are in
`docs/research/T07-notes.md` and the local game-data/output manifests.

Observed file facts: the first byte matches the number of u16 little-endian
absolute offsets in the table at byte offset 2; in the five nonempty files,
the first payload offset matches `2 + 2*count + count*byte_1`; offsets are
increasing and UTF-16LE aligned, and each bounded segment decodes to
NUL-terminated UTF-16LE. Four files are exactly two-byte `00 00` zero-offset
forms. Across the set, **SCANNED 9; DECODED 9; FAILED 0; UNKNOWN 0** at the
structural-output layer, totaling 3,372 bytes, 52 segments and 230
NUL-delimited fragments. The second header byte, interstitial semantics,
grammar rules, and reason for empty locale files remain UNKNOWN; this is not a
message-text decode or a recovered parser.

Ghidra 12.2 was run against the exact LGPE Pikachu 1.0.2 NCA
`2b7730a9e56498bbafac2002d4908c6b`, `main` SHA-256
`1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8`,
loaded at `0x7100000000`. It found 9 defined grammar strings, all 9 direct
string references in `FUN_71001ae750` (`main+0x1ae750`), and that function's
calls to path builder `FUN_710004deb0` and resource helper
`FUN_71000adc70` (`main+0xadc70`). The only direct incoming call to this
function is from `FUN_7100005bd0` (`main+0x5bd0`) at `main+0x61d0`; that
startup caller itself has a data reference at `main+0x1527458`. This static
reference chain does not prove execution. No parser or consumer was recovered.
The SHA-guarded reproducer is
`scripts/ghidra/Run-InspectGrammarDataReferences.ps1`; machine output is in the
ignored `logs/ghidra-grammar-data-xrefs-v1-script.log`.

The plan now lists the grammar-specific method and the verified `DECODED`
coverage status for each of the nine paths. Game-data totals are **SCANNED
10,020; DECODED 10,020; FAILED 0; UNKNOWN 0; PENDING 0; UNSUPPORTED 0**.
Current source-wide totals are **SCANNED 27,824; DECODED 21,103; FAILED 0;
UNKNOWN 6,721; PENDING 0; UNSUPPORTED 0; 77,724 receipts**. WSL CPython
3.12.3 passes **132/132** tests; the native Windows wrapper ran all 132, with
131 passed and one symlink-permission skip. T07/T10 remain `IN_PROGRESS`;
structural parsing and static path loading do not establish runtime use or
grammar semantics.


### T09 SESD BSEQ full batch — 2026-10-29

The actual RomFS scan found 381 `.bseq` sources; all 381 passed a local `SESD`
magic and version-3 gate. The pinned pbseqtool adapter converted 353 supported
battle sequences to mirrored JSON and retained all original input bytes in
`raw_hex`. Its independent audit checked 381 source paths/hashes and 353 JSON
outputs; 52 round-tripped byte-exactly, 301 normalized, and all 353 had equal
structured output after serialization/reparse. Output verification passed
353/353 with `bad=0`. The 28 sources under `bin/demo/sequence` failed the
upstream parser and are `UNSUPPORTED` under the pinned README's demo/cutscene
limitation; exact parser exceptions are retained, without calling those inputs
malformed. Full suite: 135/135 tests.

Current source-wide totals are **SCANNED 27,824; DECODED 21,456; FAILED 0;
UNKNOWN 6,340; PENDING 0; UNSUPPORTED 28; 78,077 output receipts**. Reproduce
with `uv run python scripts/research/refresh_bseq_scan_signatures.py --root ..`
to refresh the 381 observed headers, then `uv run lgpe decode-sequences --limit
0 --execute --sources-file docs/research/source_lists/t09-bseq-381.txt`, then
`uv run lgpe verify
--sources-file docs/research/source_lists/t09-bseq-381.txt` and
`uv run python scripts/research/check_bseq_outputs.py`. Detailed source hashes,
tool revision, byte-roundtrip state, limits, and demo parser errors are in
`docs/research/T09-notes.md`; T09 remains `IN_PROGRESS` for event ownership,
sequence-to-Wwise playback, and runtime sequence behavior.

### T09 BSEQ-to-Wwise static cross-reference — 2026-10-30

`scripts/Map-Sequence-Audio.ps1` ran the actual `lgpe map-sequence-audio`
workflow through native PowerShell 7/Windows `uv` because the WSL process
entered kernel file-I/O wait while resolving the mapped X: tree. The successful
native run rehashed **265/265 BNK source/XML pairs**, checked all **381** BSEQ
source rows and all **353** supported JSON outputs (including their embedded
`raw_hex` against current source bytes), and parsed all **2,552** existing
Wwise event/action rows against the verified bank hashes. It emitted **949**
play-event parser-field rows to ignored
`manifests/bseq_wwise_events.jsonl` (**4,645,758 bytes; SHA-256
`1d12a2fbe58b49cdb11dd6122161ee49134d4528a40950c98713103775b0098e`**).

All **268/268** `BelugaSoundLoadBank` parser-field literals exactly equal a
local BNK filename stem (233 distinct literals). The **949**
`BelugaSoundPlaySe` parser-field literals produce **658** distinct FNV-1
32-bit IDs; **768** occurrences have an event-ID candidate in a bank whose
filename stem exactly matches a bank-name literal from that same sequence,
and **181** have candidates only outside those sequence-referenced banks.
Each row retains sequence source/output hashes, group and command indexes,
parser parameters, event ID/index, matching bank and XML hashes, and reachable
WEM/DIDX/WAV receipts when the existing Wwise map supplies them. Event names
remain unknown because `wwnames.db3` is absent. The command dictionary's
meaning, bank-loading behavior, event invocation, playback, and sequence timing
remain unverified. This is a cross-reference of local parser fields and Wwise
IDs, not evidence of runtime execution.

Follow-up on the **181** outside-bank occurrences found **172** with no
`BelugaSoundLoadBank` parser field and **9** with an exact local bank-name
reference whose bank lacks that ID. The parsed Wwise candidates include 173
incidences in `Battle_System_Common.bnk`, 37 in `System_Common.bnk`, and two
each in the two partner-Pokémon voice banks; 33 occurrences have multiple
global-bank candidates. These are static ID placements only.

The regenerated Wwise map also writes **7** loose-WEM rows to
`manifests/wwise_unreferenced_wem.jsonl`. All **265/265** successful BNK/XML
pairs were parsed; none of the seven WEM IDs appears as a `sourceID` in any
parsed HIRC media object. Their seven loose WEM source hashes and seven WAV
output hashes were all rechecked; all WAV outputs exist. The sidecar is 6,728
bytes (SHA-256
`ffc4b6a704e8c580014520ab502c2733a03b9292a8a3b08cf92073fd60a2ace7`). This
closes the local event/HIRC sourceID search for those IDs but does not establish
whether another game code path uses them.

At this mapping-only checkpoint, the mapper added no decode coverage; the
source-wide status was **SCANNED 27,824; DECODED 21,456; FAILED 0; UNKNOWN
6,340; PENDING 0; UNSUPPORTED 28; 78,077 receipts**. The focused mapper tests
passed **3/3**, the focused Wwise map tests passed **9/9**, and the then-current
full WSL CPython 3.12.3 suite passed **140/140**, including the exhaustive-run
ordering regression. At that point, an exhaustive `run` had not yet been
repeated after adding orchestration; the completed integrated replay below
supersedes that status and reports **78,104/78,104 receipts verified**.
Reproduce the mapper on Windows with
`pwsh -NoProfile -File scripts/Map-Sequence-Audio.ps1`; on WSL, set
`UV_PROJECT_ENVIRONMENT=/tmp/lgpe-research-wsl-venv` and run
`uv run lgpe map-sequence-audio --root ..` where the project and source are
mounted (native Windows is recommended on this mapped X: tree).

### Integrated exhaustive run replay — 2026-10-29/30

The first Windows-uv attempt passed the WSL `/mnt/x/...` root and failed before
scanning because Windows interpreted it as a UNC path under `\\192.168.1.5\j`;
that is an invocation-path failure, not a source decode failure. The corrected
native-root run completed under journal run ID
`3854a69f321f49ea9eaeff9e2a80633f`, using
`uv.exe run lgpe run --root "X:\ROMS\Nintendo Switch\Pokemon\Pokemon Lets Go Pikachu" --limit 0 --timeout 600 --execute`.

Its inventory checkpoint completed at **SCANNED 27,824**, with **0** scan
access anomalies. Snapshot comparison found **27,819 matched paths, 5
scan-only paths, and 0 snapshot-only paths**; the five are the extensionless
ExeFS files `main`, `rtld`, `sdk`, `subsdk0`, and `subsdk1`. The live archive
manifest contains **1,017 DECODED containers / 59,121 members, 0 FAILED, 0
UNKNOWN, 0 PENDING, and 0 UNSUPPORTED**; the archive-stage journal checkpoint
was written at `2026-10-29T17:36:06Z`. The learnset checkpoint followed at
`2026-10-29T17:37:30Z`: **980/980 members DECODED, 0 FAILED, 0 PENDING, and 0
UNKNOWN**. Game-data checkpoint at `2026-10-29T17:46:44Z`: **10,020 decoded
outputs, 0 FAILED, 0 PENDING, 0 UNKNOWN**. This includes 5,380 paired
messages, 15 AHTB tables, 9 grammar DATs, and all selected pkNX-style record
groups. BNK checkpoint at `2026-10-29T17:46:51Z`: **265/265 banks DECODED, 0
FAILED, 0 PENDING, 0 UNKNOWN**. Texture checkpoint at `2026-10-29T17:47:40Z`:
**1,344/1,344 DECODED, 0 FAILED/PENDING/UNKNOWN/UNSUPPORTED**. Model checkpoint
at `2026-10-29T17:48:13Z`: **321/321 DECODED, 0
FAILED/PENDING/UNKNOWN/UNSUPPORTED**. Animation checkpoint at
`2026-10-29T17:48:41Z`: **455/455 DECODED, 0
FAILED/PENDING/UNKNOWN/UNSUPPORTED**. Particle checkpoint at
`2026-10-29T17:49:37Z`: **1,160/1,160 DECODED, 0
FAILED/PENDING/UNKNOWN/UNSUPPORTED**. Collision checkpoint at
`2026-10-29T17:50:11Z`: **698/698 root-table outputs verified, 0 FAILED, 0
PENDING, and 698 schema UNKNOWN**. Audio checkpoint at
`2026-10-29T17:51:23Z`: **1,134/1,134 WEM outputs DECODED, 0 FAILED, 0
PENDING**. AMX header catalog checkpoint at `2026-10-29T17:51:37Z`:
**712/712 static headers passed, 0 header rejects or failures**; the catalog
labels bodies `UNKNOWN_BODY_DECODER_NOT_IMPLEMENTED` until the separate body
decoder runs. AMX body decoder checkpoint at `2026-10-29T17:53:05Z`: **712/712
DECODED, 0 FAILED, 0 UNKNOWN**, including 7 loose files and 705 archive
members. The result records exact LGPE 1.0.2 `main` SHA-256
`1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8`; runtime
semantics remain open. BSEQ checkpoint at `2026-10-29T17:53:15Z`: **381
scanned; 353 DECODED; 28 UNSUPPORTED demo/cutscene sequences; 0 FAILED; 0
PENDING**. BNK-media checkpoint at `2026-10-29T17:55:00Z`: **1,109 members
indexed, 1,103 DECODED_EXISTING_VERIFIED, 6 UNSUPPORTED prefetch fragments, 0
FAILED/PENDING/UNKNOWN**. The Wwise event map checkpoint at `17:55:04Z` parsed
265/265 banks and produced 2,552 event/action rows, 2,251 event-to-WEM pairs,
1,190 event-to-DIDX references, and 1,170 verified internal WAV references.
The BSEQ map checkpoint at `17:55:16Z` reverified 353 supported sequences and
produced 949 play-event rows: 768 candidates in sequence-referenced banks and
181 only outside them. The seven loose WEMs without event-graph reachability
still have zero HIRC `sourceID` matches across the 265 local banks. Exact
current manifest byte counts and hashes are recorded in
`docs/research/T09-notes.md`. Sample registration checked 302 selected receipts
and classified the expected 34 unsupported samples (six prefetch fragments
plus 28 BSEQ demo/cutscene inputs). The run completed at
`2026-10-29T18:15:13Z` with exit code 0. Full receipt verification checked
**78,104/78,104 outputs**, `bad=0`, `errors=[]`. Refreshed global coverage is
**SCANNED 27,824; DECODED 21,456; FAILED 0; UNKNOWN 6,340; PENDING 0;
UNSUPPORTED 28; 78,104 decoded outputs**.

The PS7 wrapper initially read an empty `$LASTEXITCODE` when invoked through
WSL, because that PowerShell process did not launch child executables with the
call operator. `scripts/Start-Research.ps1` now starts uv using
`System.Diagnostics.ProcessStartInfo.ArgumentList`, waits for it, and reads
its exit code. PowerShell parser validation and a child-process smoke check
both pass; the corrected full run used native Windows uv directly. `uv
sync` exited 0 (with the inherited invalid `SSL_CERT_DIR` warning). No writes
from this run target the original game root; generated files are confined to
the research project. The complete native-uv test suite then passed
**140/140 tests**, with one expected skip because symlink creation is
unavailable on this host.

### T08 GFBCol structural expansion — 2026-10-30

The GFBCol adapter advanced from root-only indexing to version 2 structural
JSON. Against the actual 698-file 1.0.2 RomFS corpus, the root layout matched
698/698; root slots 0–2 each resolved to bounded vectors whose elements all
validated as table envelopes, for **2,219** child tables total. Root slot 3
had count 8 in every file; all **5,584** four-byte entries are retained raw
because none validate as child-table envelopes. `verify-collisions` checked
**698/698** outputs, 698 root views, 698 nested views, and 2,219 child-table
envelopes, with `failed=0`, `pending=0`, and `errors=[]`. All 698 source rows
remain `UNKNOWN`; this structural result does not establish field names,
scalar/vector element types, geometry, or collision semantics.

The pipeline exercised a real five-file smoke set, the first 20 sources, and
the full 698-source set; each batch had zero failures. Native Windows `uv`
was used because recursive WSL `/mnt/x` traversal entered a 9P I/O wait; the
Windows pass completed without touching source files. The updated
`lgpe coverage` report remains **SCANNED 27,824; DECODED 21,456; FAILED 0;
UNKNOWN 6,340; PENDING 0; UNSUPPORTED 28; 78,104 decoded outputs**. The
collision views remain in the UNKNOWN column.

The added structural decoder, bounded v1-to-v2 output migration, and recovery
from an interrupted manifest upgrade pass the full native Windows suite:
**142 tests passed, one expected symlink-creation skip**. Evidence, sample
hashes, and reproduction commands are in `docs/research/T08-notes.md`.

### T10 exact-build spawn RNG follow-up — 2026-10-30

A Ghidra 12.2 `-noanalysis -readOnly` pass used the locally extracted Pikachu
1.0.2 `0/main`, guarded by SHA-256
`1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8` and base
`0x7100000000`. It confirmed two xoroshiro128+ `(24,16,37)` state pairs in
`FUN_71002fdf90` and linked one pair's bounded draw to the previously
cross-checked encounter-rate helper. The other pair is gated by an opaque mode
value and has a modulo-10,000 `<=4` test followed by a numeric three-way
selection (`0x90..0x92`). The external address `main+0x2fdfc0` is an instruction
inside that function, not a function entry. Its parent `FUN_71002f8a50` has zero
direct incoming references in the saved database; state initialization,
seeding, and runtime reachability remain unverified. This pass provides no
PID/EC/shiny or capture formula evidence. Reproduce with
`powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/ghidra/Run-InspectSpawnRngContext.ps1`;
the Ghidra script and ignored run logs are linked from
`docs/research/T10-notes.md`. No source or decoder outputs changed. Global
coverage remains **SCANNED 27,824; DECODED 21,456; FAILED 0; UNKNOWN 6,340;
PENDING 0; UNSUPPORTED 28; 78,104 outputs**; T10 remains `IN_PROGRESS`.

### T10 exact-build candidate accessor follow-up — 2026-10-30

On the SHA-guarded Pikachu 1.0.2 `0/main` (`1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8`, base `0x7100000000`), Ghidra 12.2 `-noanalysis -readOnly` decompilation shows `FUN_7100218470` copies four qwords from `+0x3e8`, `+0x3f0`, `+0x3f8`, and `+0x400` (32 bytes total) before calling metadata helper `FUN_71000d4af0`. The latter uses `FUN_71000b84d0` and `FUN_71000d22b0` to match descriptor values against indexed metadata rows, initializes its output to numeric `0x69`, and can return a 32-bit row payload with small side fields. Selector and payload labels remain unknown. Thus `0x90..0x92` are still not assigned species/gameplay meaning. Recursive inspection of the actual decoded `encount_data_p.json` found no slot `Species` values in that range (0 hits across its 70 tables and nested vectors), so that file supplies no positive field-label cross-check. Reproduce with `pwsh.exe -NoProfile -ExecutionPolicy Bypass -File scripts/ghidra/Run-TraceSpawnEntityValue.ps1`; ignored Ghidra decompilations are saved under `logs/ghidra-spawn-entity-value-v1-functions/`. No source or decoded output changed. Coverage remains **SCANNED 27,824; DECODED 21,456; FAILED 0; UNKNOWN 6,340; PENDING 0; UNSUPPORTED 28; 78,104 outputs**; T10 remains IN_PROGRESS.

### T10 candidate descriptor construction trace — 2026-10-30

A literal-offset store scan of the exact SHA-guarded main examined 29,483 Ghidra functions and 2,243,719 instructions. It found 352 store instructions across common object offsets, so hits alone were not treated as field evidence. The useful hit, `FUN_71002175e0`, was then verified by direct xrefs and the candidate constructor path: it reads optional fields from its FlatBuffer table argument and writes four qwords to object offsets `+0x3e8`, `+0x3f0`, `+0x3f8`, and `+0x400`. Its only direct call site in the saved database is `FUN_710026f930` at `main+0x26f974`; that function is called from `FUN_71002334d0` at `main+0x233530`.

The exact-build candidate `FUN_71002fdf90` allocates a `0x10d0`-byte object and calls `FUN_71002334d0` at `main+0x3008a4` with a table reached through a FlatBuffer vector. In that same candidate, four direct calls to `FUN_7100218470` compare its result with values derived by the RNG branch. This statically links a candidate object-construction path to the 32-byte descriptor read by the value helper. It does not reveal the four schema field names, identify the input FlatBuffer resource, or prove that this function runs at runtime. The constructor vtable groups at `PTR_DAT_71015fe9d8` and `PTR_DAT_71015fe9e0` have null type-info pointers at the inspected address points; this route did not yield RTTI class names.

Reproduce the focused writer scan and vtable check with `pwsh.exe -NoProfile -ExecutionPolicy Bypass -File scripts/ghidra/Run-ScanSpawnEntityDescriptorWrites.ps1` and `pwsh.exe -NoProfile -ExecutionPolicy Bypass -File scripts/ghidra/Run-InspectSpawnEntityVtables.ps1`. The full helper/constructor/candidate decompilation pass is reproduced with `scripts/ghidra/Run-TraceSpawnEntityValue.ps1`. All passes guarded the same local Pikachu 1.0.2 `main` hash and base and used `-noanalysis -readOnly`. No data exports changed. The source-table check remains zero `Species` hits for `0x90..0x92`; the selected values and accessor payload stay UNKNOWN. Coverage is unchanged: **SCANNED 27,824; DECODED 21,456; FAILED 0; UNKNOWN 6,340; PENDING 0; UNSUPPORTED 28; 78,104 outputs**. T10 remains IN_PROGRESS.

### T10 shared spawn-state consumer follow-up — 2026-10-30

The caller `FUN_71002f8a50` directly calls candidate `FUN_71002fdf90` at `main+0x2f8e2c`, followed by `FUN_7100300e40` at `main+0x2f8e38`. The latter independently uses the same `+0x80/+0x88` xoroshiro128+ `(24,16,37)` state pair and calls `FUN_71003154a0`, so the pair is shared across these consecutive static handlers. The dispatcher has zero direct incoming refs in the saved Ghidra database and no direct reads/writes of those state offsets; seed/init and runtime reachability remain unresolved. Reproduce using `scripts/ghidra/Run-TraceSpawnEntityValue.ps1`. Coverage remains **SCANNED 27,824; DECODED 21,456; FAILED 0; UNKNOWN 6,340; PENDING 0; UNSUPPORTED 28; 78,104 outputs**; T10 remains IN_PROGRESS.

An additional SHA-guarded `-noanalysis -readOnly` Ghidra scan inspected 2,839,329 instructions in the executable block of the same local 1.0.2 `main`; 91,789 were `ADR`/`ADRP`. None had rendered operands containing `2f8`, so no PC-relative code-address construction to the page containing `main+0x2f8a50` was found. Together with the zero direct xrefs and prior absolute/relative initialized-memory scan, this narrows static references checked so far but does not rule out runtime registration, uninitialized tables, or indirect computation. Reproduce using `scripts/ghidra/Run-ScanSpawnDispatcherAddressMaterialization.ps1`; it records ignored logs under `logs/`. No source or decoded outputs changed. Coverage remains **SCANNED 27,824; DECODED 21,456; FAILED 0; UNKNOWN 6,340; PENDING 0; UNSUPPORTED 28; 78,104 outputs**; T10 remains IN_PROGRESS.

A separate instruction scan of that `main` found 199 same-base 64-bit store groups covering `+0x80/+0x88/+0x90/+0x98`; `FUN_71002fdf90` was the positive control. The shared offsets are too common to identify an initializer, so state seeding remains unresolved. `scripts/ghidra/Run-ScanSpawnRngStateStores.ps1` reproduces the SHA/base-guarded, read-only scan. No source or decoded outputs changed. Coverage remains **SCANNED 27,824; DECODED 21,456; FAILED 0; UNKNOWN 6,340; PENDING 0; UNSUPPORTED 28; 78,104 outputs**; T10 remains IN_PROGRESS. The full WSL2 regression suite also passed: `UV_PROJECT_ENVIRONMENT=/tmp/lgpe-research-t07-venv uv run python -m unittest discover -s tests -v` completed **146/146 in 8.582s**, including the local hash-pinned cross-reference integration test.

The updated `uv run lgpe spawn-rng-crossref` report hash-checks local 1.0.2 personal, ordinary encounter, and event-static sources/decoded outputs, exact `main`, pinned pkNX enum and resource mapping sources, and the guarded Ghidra trace scripts. Values `0x90..0x92` match personal `index`/`GoSpecies` 144–146; both ordinary tables have 0/1,820 target `Species` hits. The decoded `event_encount.bin` has 10 `EncounterStatic7b` rows; indexes 2–4 contain matching `Species` values 144–146 at form 0, level 50. Ghidra statically traces the event path through `main+0x2ba7c0`, a 64-byte record builder at `main+0x2baa10`, and lookup helper `main+0x2baba0`, whose three direct call references are separately recorded in the report. The completion path reaches `main+0x28f430` but has no direct call to RNG candidate `main+0x2fdf90`; accessor semantics and candidate runtime reachability remain unresolved. The report remains `CORRELATED_UNASSIGNED`. The latest WSL2 suite passes 146/146 in 9.680s. Coverage remains **SCANNED 27,824; DECODED 21,456; FAILED 0; UNKNOWN 6,340; PENDING 0; UNSUPPORTED 28; 78,104 outputs**; T10 remains IN_PROGRESS.

### T10 event handler row cross-reference — 2026-10-30

The schema-v3 `spawn-rng-crossref` report now verifies the actual 640-byte event source row-by-row against mirrored JSON `raw_hex`, then checks source offsets against the exact-build Ghidra normalization and branch values. The `main+0x2baa10` builder zero-extends the source `u16 Species` at `+0x08` to internal `u32` `+0x08`, and moves source `Form` at `+0x0a` to internal `+0x0c`. The `main+0x28f430` consumer condition pairs `(Species=133, Form=1)` and `(Species=25, Form=8)` match event source rows 1 (Eevee, level 5) and 0 (Pikachu, level 5), respectively. It then reads a byte from opaque object offset `+0x111` through `main+0x1ca030`: a first read of zero writes `1` to normalized Gender at `+0x14`; a first nonzero read followed by a second read of one writes `2`. Pinned pkNX `EncounterStatic7b.cs`/`FixedGender.cs` map those values to Male/Female, while both source rows begin as Random. The two pinned source hashes and Ghidra v2 logs are recorded in T10 notes and the v3 report. Pinned pkNX C# export and field comparison freshly validated 10 records × 39 properties with zero mismatches. This is static code/data evidence; the opaque input's meaning, runtime execution, and gameplay outcome remain unknown, and no connection to the separate RNG candidate is established. The WSL full suite passes **146/146 in 7.696s**, including the four focused cross-reference tests; `uv run lgpe spawn-rng-crossref` passes. Global counts remain **SCANNED 27,824; DECODED 21,456; FAILED 0; UNKNOWN 6,340; PENDING 0; UNSUPPORTED 28; 78,104 outputs**.


### T10 event opaque-byte setter trace — 2026-10-30

The schema-v4 `spawn-rng-crossref` report now records the exact-build getter/setter for opaque object byte `+0x111`. Ghidra's static caller instruction at `main+0xf058` passes constant 1, while a decompiled switch case in the same function shows a boolean expression derived from two values; the decompilation also warns that type propagation did not settle. This discrepancy is explicitly `UNRESOLVED`; the object roots differ between the event handler and setter caller, so object identity and any RNG-to-setter flow remain unproven. The exact 1.0.2 `main` hash, Ghidra script/wrapper hashes, and reproduction commands are in `docs/research/T10-notes.md`. Focused tests: **4/4**. Full WSL2 suite: **146/146**. Source-wide coverage: **SCANNED 27,824; DECODED 21,456; FAILED 0; UNKNOWN 6,340; PENDING 0; UNSUPPORTED 28; 78,104 outputs**. T10 remains `IN_PROGRESS`.


### T10 setter caller data slot — 2026-10-30

A read-only Ghidra follow-up finds the setter caller `FUN_710000e420` has one saved-database incoming DATA xref: writable `.data` cell `main+0x15278b8` contains its entry address. The cell has zero direct incoming references, and its adjacent qwords are untyped; no table or dispatch semantics are assigned. This is not a call edge and does not establish runtime reachability. The exact evidence and hashes are in T10 notes; report schema v5 preserves this as unverified. Full WSL2 suite: **146/146 in 9.198s**. Coverage: **SCANNED 27,824; DECODED 21,456; FAILED 0; UNKNOWN 6,340; PENDING 0; UNSUPPORTED 28; 78,104 outputs**. T10 remains `IN_PROGRESS`.


### T10 setter-caller page-base reference check — 2026-10-30

A read-only exact-build Ghidra pass found 375 broad references to the 4 KiB page base `main+0x1527000` (178 DATA, 197 PARAM, 82 owner labels), but the specific pointer slot `main+0x15278b8` still has no direct incoming references. The page references do not prove an access to that qword or runtime dispatch. Report schema v6 records the counts and retains UNKNOWN semantics. Full WSL2 tests: **146/146 in 9.681s**. Coverage: **SCANNED 27,824; DECODED 21,456; FAILED 0; UNKNOWN 6,340; PENDING 0; UNSUPPORTED 28; 78,104 outputs**. T10 remains `IN_PROGRESS`.


### T10 event-state owner reference — 2026-10-30

The event-state function FUN_710028f300 has a writable .data cell at main+0x1547368 that stores its address; that function directly calls the loader, readiness helper, and event consumer. The cell has zero direct incoming references. Its page's five references resolve in inspected contexts to other offsets, not this cell. No vtable type or runtime-dispatch claim is assigned. Full WSL2 tests: **146/146 in 9.015s**. Coverage: **SCANNED 27,824; DECODED 21,456; FAILED 0; UNKNOWN 6,340; PENDING 0; UNSUPPORTED 28; 78,104 outputs**. Schema v7 retains CORRELATED_UNASSIGNED; T10 remains IN_PROGRESS.


### T10 event-state code target boundary — 2026-10-30

A v15 SHA-guarded Ghidra 12.2 pass inspected the eight qwords at main+0x1547348 in the exact Pikachu 1.0.2 main (SHA-256 1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8, base 0x7100000000). Six qwords have DATA references to code addresses. Ghidra FunctionManager defines functions at main+0x11160 and main+0x28f300; main+0x2a90, main+0x28f2e0, main+0x28f2f0, and main+0x28f6c0 have decoded instructions but no exact or containing function in the saved database. This is address-boundary evidence only; the qword run's type and runtime dispatch remain UNKNOWN. The pointer cell main+0x1547368 still has no direct incoming reference; its page references do not target that cell. The report is schema v8 and remains CORRELATED_UNASSIGNED. Reproduce with pwsh.exe -NoProfile -ExecutionPolicy Bypass -File scripts/ghidra/Run-InspectEventEncounterPathXrefs.ps1; ignored v15 logs are recorded in T10 notes. Focused tests pass 4/4; full WSL2 tests pass 146/146 in 9.707s. A fresh coverage command confirms **SCANNED 27,824; DECODED 21,456; FAILED 0; UNKNOWN 6,340; PENDING 0; UNSUPPORTED 28; 78,104 outputs**. T10 remains IN_PROGRESS.

### T08 exact-build GFBCol address observations — 2026-10-30

The read-only main scanner verifies the exact 1.0.2 NSO hash and all three decompressed-segment header hashes across 23,113,044 bytes. It finds zero hits for eight bounded ASCII/UTF-16LE tokens and validates six `col_*` strings whose raw ADRP/ADD/BL sequences target `main+0xb660`. This does not prove a GFBCol loader or parameter semantics. The representative 840-byte wall sample and mirrored JSON hashes were rechecked; all 698 GFBCol sources remain UNKNOWN. Focused GFBCol main-reference tests: **8/8**. Current global counts, freshly confirmed with `uv run lgpe coverage`: **SCANNED 27,824; DECODED 21,456; FAILED 0; UNKNOWN 6,340; PENDING 0; UNSUPPORTED 28; 78,104 outputs**. See `docs/research/T08-notes.md`.

### T10 event xref and capture-candidate follow-up — 2026-10-30

The v17 exact-main Ghidra report adds incoming DATA reference counts for the six code targets in the event-state window: 1,175 references to `main+0x2a90`, 65 to `main+0x11160`, and one matching data-cell reference for each of four other targets. Target types and runtime dispatch remain UNKNOWN; `spawn-rng-crossref` is schema v9 and remains CORRELATED_UNASSIGNED. A separate read-only capture request/getter investigation statically links a getter result buffer to the existing event-table lookup/copy helpers, but does not establish capture probability, RNG linkage, or result meaning. Current counts are **SCANNED 27,824; DECODED 21,456; FAILED 0; UNKNOWN 6,340; PENDING 0; UNSUPPORTED 28; 78,104 outputs**. See `docs/research/T10-notes.md`.

### T09 raw demo BSEQ audio candidates — 2026-10-30

`uv run lgpe map-demo-audio` creates the ignored 1,970,898-byte `manifests/bseq_demo_audio_candidates.json` sidecar. It rehashes the 28 UNSUPPORTED demo/cutscene inputs (264,964 bytes), parses 265 original Wwise v128 banks, and validates 206 bounded raw `Play_`/`Stop_` string ID candidates against type-4 HIRC objects. It also rehashes 22 linked BNK XMLs and 248 linked media receipts. The three actual sample paths resolve to local HIRC objects and their DIDX/DATA/WEM/WAV receipts; one 3,300-byte source has no bounded literal candidate. Dry-run produces the same report SHA-256 `737e041908a7535830e75a482e1a7770f5019615fc2dc20f367e7a75844a8529`. No parser classification or decoded output changed; all 28 remain UNSUPPORTED, and record boundaries, command meanings, loading, invocation and playback remain UNKNOWN. Focused tests: **9/9**; all BSEQ tests: **15/15**. Native Windows regression suite: **163 total, 162 passed, 1 expected symlink skip**. Coverage remains **SCANNED 27,824; DECODED 21,456; FAILED 0; UNKNOWN 6,340; PENDING 0; UNSUPPORTED 28; 78,104 outputs**. See `docs/research/T09-demo-audio-candidates-2026-10-30.md`.

### Native Windows integrated replay — 2026-10-30

`scripts/Start-Research.ps1 -Limit 0 -Timeout 600 -Execute` completed on the
actual local 1.0.2 dump as run ID `bd3965f5d2a84bed9a87d6037be75d1f` at
`2026-10-30T14:31:44+08:00`, exit code 0. Inventory found **27,824** source
files with zero access anomalies; **27,819** snapshot paths matched, with five
scan-only extensionless ExeFS files (`main`, `rtld`, `sdk`, `subsdk0`,
`subsdk1`) and zero snapshot-only paths. The completed source-wide coverage is
**SCANNED 27,824; DECODED 21,456; FAILED 0; UNKNOWN 6,340; PENDING 0;
UNSUPPORTED 28; 78,104 registered decoded outputs**.

The same executed batch decoded **1,017 archive containers / 59,121 members**,
the 980-member learnset pack, **10,020** game-data outputs, 1,134 WEM-to-WAV,
265 BNK-to-XML, 1,344 BNTX-to-PNG, 321 model-to-GLB, 455 animation JSON,
1,160 particle JSON, 698 schema-unknown GFBCol root views, and all 712 AMX
catalog entries with the exact-build opcode/bounds validator. Of 381 BSEQ
inputs, 353 were decoded and 28 remain UNSUPPORTED. The 265-bank media pass
decoded 1,103 internal members and preserved six prefetch fragments as
UNSUPPORTED. Receipt verification checked **78,104/78,104** outputs with
`bad=0` and `errors=[]`; source-wide failures remain zero. The full native
Windows suite ran **163 tests** in 16.912 seconds: 162 passed and one
symlink-permission test was skipped. The six BNK prefetch fragments plus 28
BSEQ sources account for the 34 failed-or-unsupported sample registrations;
they are not decoder failures.

This run confirms the prior coverage totals and end-to-end receipt integrity;
it does not resolve the 6,340 UNKNOWN sources, the 698 GFBCol schemas, BSEQ
semantics, or unresolved runtime/gameplay paths in T10. The run checkpoints are
in ignored `manifests/runs.jsonl`; detailed Wwise receipts and map counts are in
`docs/research/T09-notes.md`.

The historical run journal had one malformed line at line 228: its JSON prefix
was truncated, leaving the visible `d936bc40678f4ab38bb519f2a66c6e2b` run ID,
sequence 0, `RUNNING` status, and timestamp. Before repair, the exact journal
bytes (SHA-256 `52e346f027f5592871aa597bef3dfb283236e490ba2fa33b1f9466abe4191cdc`)
were copied to ignored `work/journal-repair-2026-10-30/runs.jsonl.original`;
the backup hash matches. `scripts/research/Repair-RunJournal.ps1` replaced only
that invalid row with a parseable `RECOVERED` record. It recovers the command
`verify` from the same run's sequence-1 `COMPLETED` event; the original
sequence-0 detail arguments were lost and remain explicitly unavailable. The
raw fragment and its SHA-256 are retained in the recovery record. The repaired
journal parses as **558 valid JSONL records** and has SHA-256
`9016352dd1affc36561e572b11c500290c1420fef8f33147f7ce08e7a932f152`.

### T07 localized sort-string follow-up — 2026-10-30

`uv run lgpe profile-sort-string --root ..` ran against the actual 1.0.2 RomFS.
It scanned **81** `bin/app/sort_string` sources, matched all 81 paths to
`manifests/files.csv`, and independently rehashed all 81 against its JSONL
manifest. Stage totals for this subset: **SCANNED 81; DECODED 0; FAILED 0;
UNKNOWN 81; PENDING 0; UNSUPPORTED 0**. No decoded files were created. All 81
lengths are even; all 27 sort-table u16le candidates are nonempty permutations
of `1..N`. This is only a byte-level hypothesis, not a verified schema or
decoder. Exact 1.0.2 `main` xrefs establish language-specific filename loads
and raw byte-buffer storage, but the direct table parser/access was not found.
The evidence and command are recorded in `docs/research/T07-notes.md`; the
Ghidra wrapper is `scripts/ghidra/Run-InspectSortStringReferences.ps1`.

The separate personal-data `bin/pokelib/personal/monsname.dat` was not
included in this 81-file profile; its later decode and updated coverage are
recorded below. At the time of this profile, source-wide coverage was
**SCANNED 27,824; DECODED 21,456; FAILED 0; UNKNOWN 6,340; PENDING 0;
UNSUPPORTED 28; 78,104 outputs**. Focused profiler tests pass **5/5**; the
WSL2 full suite passes **168 tests and 70 subtests**. The pytest invocation
used a temporary uv environment, `PYTHONPATH=.`, disabled pytest cache writes
on the mapped drive, and a process-scoped safe-directory entry for the pinned
pkNX Git checkout.

### T07 personal `monsname.dat` follow-up — 2026-10-30

The actual 24,384-byte `bin/pokelib/personal/monsname.dat` was decoded through
the pinned pokedat `TextFile` parser (commit
`bd423b2cad9aa852fddb796bbba3c5e7b381289b`, GPL-3.0), wired into the
path-mirrored game-data batch. No `.tbl` companion exists, so labels/hashes
remain unavailable; JSON contains source-order index/text pairs and `raw_hex`.
The one-source batch reports **SCANNED 1; DECODED 1; FAILED 0; UNKNOWN 0;
PENDING 0; UNSUPPORTED 0**. `lgpe verify` checked **1 registered / 1 verified,
0 bad, 0 failed, 0 unsupported**.

Independent JPN common text comparison found **803/803** same-index prefix
matches against its 810 decoded lines, with seven reference-only trailing
entries. `uv run lgpe check-personal-monsname --root ..` rehashes both source
and output pairs and writes `manifests/personal_monsname_crossref.json`.
Source hash: `69ad057bd964a21629646e4e694a705ee69d0c919ba1cf2b13ec0e58f7c6a2a8`;
decoded output hash: `270d56ccbcb21bd231b6cbaea76e86e733f816c6ef75be86d99b4acac7166e5a`.
This validates text extraction and content correspondence without assigning
labels or identifying a relationship to localized `sort_string` indexes.

After `uv run lgpe coverage`, source-wide totals are **SCANNED 27,824; DECODED
21,457; FAILED 0; UNKNOWN 6,339; PENDING 0; UNSUPPORTED 28; 78,105 outputs**.
The 81 localized sort-string DATs remain UNKNOWN. Six focused decoder/batch/
cross-reference tests pass; WSL2 full regression suite passes **174 tests and
70 subtests in 85.56 seconds**.

### T07 exact-main `zukan_sort` array decode — 2026-10-30

A separate SHA-guarded Ghidra 12.2 trace on the actual Pikachu 1.0.2
`0/main` recovered ten `zukan_sort_*.bin` paths from pointer table
`main+0x15520b8`. `FUN_7100b09900` requests those ten indexed resources through
`FUN_71003775e0` (`main+0x3775e0`); that loader derives the element count from
the loaded byte length divided by two. `FUN_7100377800` (`main+0x377800`)
reads `u16` values at the loaded buffer plus `index*2`, and a caller at
`main+0xb0acd0` uses that accessor. This directly validates the array element
width and little-endian representation for `bin/app/zukan_data/bin/` only.
Element semantics remain UNKNOWN, and static references do not prove runtime
execution. The 81 `bin/app/sort_string/*.dat` files remain UNKNOWN; the
zukan-data accessor does not establish their format.

`zukan_sort_data` exports u16 values with source offsets and raw bytes while
preserving the entire input; batch outputs are one-to-one `.json` mirrors. The
tracked ten-row evidence file is `manifests/zukan_sort_results.jsonl` (SHA-256
`1a888080b288c862585c1de93b774db6bb785bed23aff25b11a6c19da5e813f2`). Real
source runs passed the three-file smoke (**3/3 decoded, 3/3 verified**) and
the full family batch (**10/10 decoded, 10/10 verified**). All ten source and
output hashes and both whole-file and per-entry raw-byte reassembly checks
passed. Six sources are 1,620 bytes / 810 entries; four are 2,240 bytes /
1,120 entries. Run lists and exact reproduction commands are in
`docs/research/T07-notes.md`.

The game-data manifest now reports **10,031 DECODED; 0 FAILED; 0 UNKNOWN;
0 PENDING** rows. Current source-wide totals are **SCANNED 27,824; DECODED
21,467; FAILED 0; UNKNOWN 6,329; PENDING 0; UNSUPPORTED 28; 78,115
registered outputs**. The unknown count still includes all 81 localized
`sort_string` DAT files. The complete WSL2 suite passes **177 tests and 70
subtests in 85.46 seconds**. No source game files changed.

### T07 localized sort-string consumer trace — 2026-10-30

A second read-only Ghidra 12.2 pass used the same exact Pikachu 1.0.2 `main`
SHA-256 (`1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8`)
and base `0x7100000000`. It decompiled 12 exact-build item/waza vtable targets
recovered from the saved database's vtable references; 11 missing function
boundaries were temporary and discarded on close. The examined targets are
destructor/thunk/resource-lifecycle routines and do not read candidate array
contents.

A bounded executable-instruction scan checked 2,839,329 instructions for
offset immediates `0x340`, `0x348`, `0x350`, `0x358`, `0x360`, and `0x368`,
offsets observed in the generic sort-resource helper. It found 3,515 candidate
instructions across the executable, including 86 in `main+0xb00000` through
`main+0xb3ffff`. Those constants occur in unrelated object layouts, and no
pointer/dataflow link from these hits to the localized sort buffers was
established. This scan therefore provides no element-width or endian evidence
for `bin/app/sort_string/*.dat`.

The localized family remains **SCANNED 81; DECODED 0; FAILED 0; UNKNOWN 81;
PENDING 0; UNSUPPORTED 0**. Source-wide coverage and game-data counts are
unchanged: **SCANNED 27,824; DECODED 21,467; FAILED 0; UNKNOWN 6,329;
PENDING 0; UNSUPPORTED 28; 78,115 registered outputs** and **10,031
game-data DECODED**. Reproduce with
`pwsh.exe -NoProfile -ExecutionPolicy Bypass -File scripts/ghidra/Run-TraceLocalizedSortVtableAccess.ps1`
and
`pwsh.exe -NoProfile -ExecutionPolicy Bypass -File scripts/ghidra/Run-TraceSortResourceFieldUses.ps1`.


### Native Windows exhaustive replay after zukan-sort integration — 2026-10-30

The native Windows `uv` run `701ee9b309994a7a902f51b8c9ff2dba` completed
with exit code 0 at `2026-10-30T09:37:01Z` (17:37:01 China Standard Time).
Command: `uv run lgpe run --root .. --limit 0 --execute --full-sha256`, using
CPython 3.12.13 in a temporary project environment. The complete captured
stdout is in ignored `logs/full-exhaustive-replay-native-20261030.stdout.log`;
stderr contains only two non-fatal warnings about inherited `SSL_CERT_DIR`.

The full-hash inventory scanned **27,824** files with **0 anomalies**. The
source snapshot comparison matched **27,819** paths, with **0 snapshot-only**
and five scan-only entries: ExeFS `main`, `rtld`, `sdk`, `subsdk0`, and
`subsdk1` (the supplied snapshot enumerates RomFS only). Source-wide totals:
**SCANNED 27,824; DECODED 21,467; FAILED 0; UNKNOWN 6,329; PENDING 0;
UNSUPPORTED 28**. The output receipt manifest contains **78,126 unique paths**;
all **78,126/78,126** were rehashed successfully with **bad=0** and
`errors=[]`.

Stage checkpoints report **1,017 archive containers / 59,121 members**,
**980 learnset members**, **10,031 game-data outputs**, **265 BNK/XML**,
**1,344 BNTX/PNG**, **321 models/GLB**, **455 animation JSON**, **1,160
particle JSON**, **698 GFBCol root envelopes** (all schema UNKNOWN), **1,134
WEM/WAV**, and **712 AMX decodes**. BSEQ coverage is **353 decoded / 28
UNSUPPORTED / 0 FAILED**; internal BNK media is **1,103 decoded / 6
UNSUPPORTED / 0 failed**. The six BNK fragments and 28 BSEQ sources account for
the 34 unsupported sample registrations.

A preceding WSL2 full-hash attempt (`d677ad0ae1714781a02994ba8f6b9ad4`) was
interrupted after the `/mnt/x` scan stalled on the network-backed mount; it
was replaced by the completed native Windows run above. No source game files
were modified. The exact runtime summary and final journal status are recorded
in ignored `manifests/runs.jsonl` and `manifests/coverage.summary.json`.

### T07 localized sort-table/message cross-reference — 2026-10-30

Ran `uv run lgpe crossref-sort-string --root ..` on the actual RomFS. It
rehashes all 81 localized DATs against `files.csv` and
`sort_string_candidates.jsonl`; for each of the 27 sort tables it also
rehashes the same-locale message source and decoded JSON against their
DECODED game-data manifest rows. **27/27** candidate arrays, interpreted only
for this content check as little-endian u16, are complete permutations of
`1..N`; **0/27** big-endian interpretations are such permutations. Every
candidate value joins the companion JSON's same-numbered `line.index`, and
all 27 message ID prefixes match the item/monsname/waza family.

The output is a cross-reference manifest, not converted game data:
`manifests/sort_string_message_crossrefs.jsonl` and
`manifests/sort_string_message_crossrefs.summary.json`. Exact-main Ghidra
evidence still lacks the consumer's direct element read, so the localized
subset remains **SCANNED 81; DECODED 0; FAILED 0; UNKNOWN 81; PENDING 0;
UNSUPPORTED 0** and no receipt was added. Source-wide totals remain
**SCANNED 27,824; DECODED 21,467; FAILED 0; UNKNOWN 6,329; PENDING 0;
UNSUPPORTED 28; 78,126 outputs**. The focused unittest module passes **5/5**.
See `docs/research/T07-notes.md` for ordering checks and reproduction details.

### T07 exact-main sort-resource follow-up — 2026-10-30

The read-only Ghidra trace at exact Pikachu 1.0.2 `main` hash
`1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8`
decompiled 24 functions. It confirms owner `+0x20` is the helper used by the
u32-count/u16-search query, and that helper loads `zukan_chi/sty/nex/evo` data.
The three `monsname_*sort*.dat` resources are requested into a distinct child
object at owner `+0x28`; the query trace provides no direct read of those
buffers. No element layout is assigned and no output receipt was added.
Therefore the localized subset remains **SCANNED 81; DECODED 0; FAILED 0;
UNKNOWN 81; PENDING 0; UNSUPPORTED 0**. Global coverage remains **SCANNED
27,824; DECODED 21,467; FAILED 0; UNKNOWN 6,329; PENDING 0; UNSUPPORTED
28; 78,126 outputs**. Reproduce with
`pwsh.exe -NoProfile -ExecutionPolicy Bypass -File scripts/ghidra/Run-TraceSortStringAccessorLink.ps1`.

### T07 localized-sort vtable expansion — 2026-10-30

The exact-main read-only Ghidra rerun decompiled 41 functions and created 16
temporary boundaries that were discarded on close. The added child-resource
vtable methods forward to generic release helpers; the added derived-list
methods access bounds, callback state, and list bytes. No direct read from the
three localized sort DAT buffers was recovered. SCANNED/DECODED/FAILED/UNKNOWN
for the localized subset remains **81/0/0/81**, with **0 PENDING / 0
UNSUPPORTED** and no output receipt. Global totals remain **27,824 / 21,467 /
0 / 6,329**, **0 PENDING / 28 UNSUPPORTED**, with **78,126 outputs**. See
`docs/research/T07-notes.md` for exact addresses, the main hash, and the
reproduction command.

### T07 localized sort resource decode — 2026-10-30

Ghidra 12.2 v12 read-only analysis of the exact Pikachu 1.0.2 `main`
(SHA-256 `1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8`)
reports language `AARCH64:LE:64:v8A`, decompiled 53 functions, and discarded
16 temporary function boundaries. It traces the item, monsname, and waza three-file requests into shared loader
`main+0x374530`; `main+0x374a90` reads indexed little-endian u16 values from
the second resource, and `main+0x374ad0` reads u16 pairs from the third.

`uv run lgpe decode-gamedata --root .. --limit 0 --execute --sources-file
configs/sort_string_sources.txt` processed the actual 81-file inventory:
**SCANNED 81; DECODED 54; FAILED 0; UNKNOWN 27; PENDING 0; UNSUPPORTED 0**.
All 54 outputs are mirrored `.json` files and passed source/output SHA-256,
receipt, and raw-byte round-trip checks. The 27 `*_initial_index.dat` files
remain UNKNOWN because no element read has been identified. `gamedata.jsonl`
now has **10,112 rows: 10,085 DECODED, 27 UNKNOWN**. Global coverage is
**SCANNED 27,824; DECODED 21,521; FAILED 0; UNKNOWN 6,275; PENDING 0;
UNSUPPORTED 28; 78,180 outputs**. The full unittest suite passed **187/187**;
the five cross-reference tests passed again after the status-report update.
Targeted verification completed with **54/54 verified, bad 0, errors []**.
An unfiltered all-output verifier attempt was interrupted after 5:30 on mapped-
drive I/O (exit 130); the prior native-Windows full verification covered
78,126 outputs before the 54 additions. See T07 notes for commands, hashes,
and Ghidra evidence.

### T07 exact first-resource accessor boundary — 2026-10-30

A Ghidra 12.2 v13 `-noanalysis -readOnly` pass checked the exact Pikachu
1.0.2 `main` (`1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8`,
base `0x7100000000`, `AARCH64:LE:64:v8A`). It decompiled all 12 functions in
`main+0x373e00..main+0x374b80`. The item/monsname/waza request callers prove
that `*_initial_index.dat` is the first resource. The shared loader caches its
pointer/byte length at `+0x350/+0x358`, but the known in-range readers access
only the second resource (`main+0x374a90`, `+0x374ac0`) and third resource
(`main+0x374ad0`). No first-resource element read appeared in this bounded
helper scan or the traced owner consumers. Actual sample sizes are even, but
that alone does not establish a format; no decode was attempted and the 27
files remain `UNKNOWN` with no JSON output.

Localized subset: **SCANNED 81; DECODED 54; FAILED 0; UNKNOWN 27; PENDING 0;
UNSUPPORTED 0**. Global source coverage is unchanged: **SCANNED 27,824;
DECODED 21,521; FAILED 0; UNKNOWN 6,275; PENDING 0; UNSUPPORTED 28; 78,180
outputs**. The filtered Ghidra excerpt is retained at
`docs/research/evidence/sortstring-resource-v13.txt`; see T07 notes for the
request order and reproduction command.


### T07 first-resource offset scan (initial field hypothesis) — 2026-10-30

Ghidra 12.2 v17/v19 found **88** current FunctionManager bodies containing a
literal load operand `#0x350`; this raw immediate scan does not prove one
shared structure field. All 88 decompiled and 44 had a C line containing the
literal `0x350`. Four incoming references from localized owner/request ranges
were found: three family requests call `main+0x374530`; the owner edge to
`main+0xb06f10` was later shown by v19 ADRP context to load static addresses
`0x7101609350/9358`, not a resource buffer. No first-resource element read
was identified; this bounded search does not exclude unowned bytes or
indirect access patterns. The 27 first-resource files stay UNKNOWN, with no
outputs. Localized subset: **SCANNED 81; DECODED 54; FAILED 0; UNKNOWN 27;
PENDING 0; UNSUPPORTED 0**. Global: **SCANNED 27,824; DECODED 21,521;
FAILED 0; UNKNOWN 6,275; PENDING 0; UNSUPPORTED 28; 78,180 outputs**.
Evidence: `docs/research/evidence/sortstring-pointer-field-v17.txt`; full
analysis notes and reproduction command: `docs/research/T07-notes.md`.


### T07 owner-side immediate provenance correction — 2026-10-30

The earlier v17 `#0x350` function count was a raw operand match, not a
confirmed resource-field inventory. Exact-main Ghidra v19 disassembled the
owner call target `main+0xb06f10`: ADRP bases point to page `0x7101609000`,
so its `#0x350/#0x358` loads access static addresses `0x7101609350/9358`,
then feed owner members `+0x18e0/+0x18e8`. This false positive is removed from
the first-resource reader hypothesis. The three localized request callers
to `main+0x374530` remain the confirmed loader/cache paths; no element reader
was found. The 27 first-resource files remain UNKNOWN, with no outputs.
Localized subset: **SCANNED 81; DECODED 54; FAILED 0; UNKNOWN 27; PENDING 0;
UNSUPPORTED 0**. Global: **SCANNED 27,824; DECODED 21,521; FAILED 0;
UNKNOWN 6,275; PENDING 0; UNSUPPORTED 28; 78,180 outputs**. Evidence:
`docs/research/evidence/sortstring-offset-context-v19.txt`.

### T09 MS ADPCM WAVE batch — 2026-10-30

The actual RomFS contains **318 `.wav` sources**; RIFF inspection verified all
318 as Microsoft ADPCM. Native Windows uv/Python 3.12.13 batches at 5, 20, and
all selected **5/5, 20/20, and 318/318**, respectively, with **0 FAILED**, **0
PENDING**, and **0 UNKNOWN**. The full manifest has 298 newly decoded PCM16
WAVs and 20 preexisting outputs that were freshly decoded to temporary files
and adopted only after byte-for-byte equality; existing targets were not
overwritten. Source SHA, mirrored target path, PCM16 integrity, channels, sample
rate, and source `fact` frame count all passed for 318/318 files. Targeted
`lgpe verify --sources-file docs/research/source_lists/wave-sources.txt`
verified **318/318 receipts**, `bad=0`, with no selected failure rows.
Refreshed source coverage is **SCANNED 27,824; DECODED 21,839; FAILED 0;
UNKNOWN 5,957; PENDING 0; UNSUPPORTED 28; 78,498 outputs**. A WSL `/mnt/x`
invocation stalled before source processing at path resolution; the completed
runs used Windows-native uv. Commands, exact sample hashes, output metadata,
and the pinned vgmstream release are in `docs/research/T09-notes.md`.
Focused wave, coverage, and pipeline tests passed **14/14**. The complete
native Windows CPython 3.12.13 suite passed **193 tests with one expected
symlink-permission skip and 72 subtests**. A prior WSL test run's sole failure
was Git's `dubious ownership` guard on the pinned pkNX checkout; the native
rerun passed.

T10 capture-result consumer follow-up (2026-10-30): a read-only, SHA-guarded Ghidra 12.2 pass on exact LGPE Pikachu 1.0.2 `0/main` decompiled 10/10 target functions (1,006 instructions; 32 direct calls; 0 failures). It traces the event lookup's 0x60-byte record into an object with offsets `+0x58`, `+0x298`, `+0x29c`, and `+0x2a0/+0x2a8`, plus an indexed 0xb8-byte nested object. The mapped bytes and branches are exact-build evidence only; field meanings, callback dispatch, capture outcome, RNG/PID/EC/shiny linkage remain UNKNOWN. Reproduce with `scripts/ghidra/Run-InspectCaptureResultConsumers.ps1`; hashes and detailed limits are in `docs/research/T10-notes.md`. Current global totals: **SCANNED 27,824; DECODED 21,839; FAILED 0; UNKNOWN 5,957; PENDING 0; UNSUPPORTED 28; 78,498 outputs**. T10 remains IN_PROGRESS.

T10 event-record pointer-pair cross-reference (2026-10-30): `uv run lgpe spawn-rng-crossref` now validates all 10 actual `event_encount.bin` rows against raw bytes and pinned pkNX `Ptr0..Ptr3` properties, then packs the four u32 values exactly as the Ghidra-traced consumer's two qwords. Rows 0, 1, 6, 8, and 9 match its observed constant-pair comparison; field meaning and runtime/capture outcome remain UNKNOWN. Report schema v10 stays `CORRELATED_UNASSIGNED`. Focused tests: **4/4**; full native-Windows regression: **194 tests, 1 skip**. Source-wide: **SCANNED 27,824; DECODED 21,839; FAILED 0; UNKNOWN 5,957; PENDING 0; UNSUPPORTED 28; 78,498 outputs**. T10 remains IN_PROGRESS.

T10 save/filesystem API census (2026-10-30): a SHA-guarded, read-only Ghidra 12.2 trace of exact LGPE Pikachu 1.0.2 `0/main` (SHA-256 `1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8`; base `0x7100000000`) found one direct `IsSaveDataExisting` call and one `MountSaveData` call in `main+0x24d70`. Direct `CommitSaveData`, `EnsureSaveData`, `WriteFile`, `SetFileSize`, and `DeleteFile` calls are zero in the saved reference model; indirect calls remain possible. The save worker has zero incoming references, so player-save ownership and runtime behavior remain UNKNOWN/UNVERIFIED. `uv run lgpe save-api-crossref` emits `manifests/save-api-crossref.json` (`STATIC_REFS_ONLY`); focused tests passed 5/5; full native Windows regression passed 199 tests with one skip (198 passed). Source-wide totals remain **SCANNED 27,824; DECODED 21,839; FAILED 0; UNKNOWN 5,957; PENDING 0; UNSUPPORTED 28; 78,498 outputs**. T10 remains IN_PROGRESS.

T10 save-worker pointer census (2026-10-30): exact-build, read-only Ghidra scanned 18 initialized memory blocks (23,113,044 bytes) for `main+0x24d70` and three save helpers. Absolute qword matches: **0**; image-offset dword candidates: **2**, both for `main+0x27200` in `.rela.plt` and `.hash`, unassigned as pointer evidence. A separate code pass scanned 2,839,329 instructions (91,789 ADR/ADRP) for the worker page and a same-register `ADD #0xd70` within 0x20 bytes; it found zero candidates. The worker still has no direct incoming reference; registration/player-save ownership/runtime remain UNKNOWN/UNVERIFIED. `uv run lgpe save-worker-pointer-scan` emits `manifests/save-worker-pointer-scan.json`. Focused tests: **4/4**; full native Windows regression: **203 tests, 202 passed, 1 skipped**. Source-wide totals remain **SCANNED 27,824; DECODED 21,839; FAILED 0; UNKNOWN 5,957; PENDING 0; UNSUPPORTED 28; 78,498 outputs**. T10 remains IN_PROGRESS.

T08 GFBCol token-helper follow-up (2026-10-30): a SHA-guarded Ghidra 12.2 `-noanalysis -readOnly` pass on exact Pikachu 1.0.2 `0/main` confirmed six `col_*` calls into `main+0xb660`. That 408-byte function has 225 incoming references, 102 instructions, and five direct calls; the six known callers have no defined owner functions. The decompiled helper exposes thread-local/global initialization and an FNV-1a loop but no standalone GFBCol schema or loading proof. The wrapper verified source hash unchanged and exact build; a literal `gfbcol` search across all 13 pinned tool-source checkouts returned zero hits. Full native Windows tests passed **203 with one expected skip**. GFBCol remains **SCANNED 698; DECODED 0; FAILED 0; UNKNOWN 698**; global coverage remains **SCANNED 27,824; DECODED 21,839; FAILED 0; UNKNOWN 5,957; PENDING 0; UNSUPPORTED 28; 78,498 outputs**. See `docs/research/T08-notes.md`; T08 remains IN_PROGRESS.

T09 BSEQ exception-chain follow-up (2026-10-30): a bounded native Windows rerun selected **28/28** demo/cutscene sequences, retained status `UNSUPPORTED`, emitted **0 JSONs**, and rehashed all 28 sources against existing manifest rows. The adapter now preserves the underlying cause hidden by pinned pbseqtool's `NameError`: 14 parser errors are UTF-8 `UnicodeDecodeError`, and 14 are `KeyError` at the LGPE command-reference lookup. No command meaning is assigned. Focused BSEQ tests: **5/5**; full native Windows suite: **205 tests, 204 passed, 1 expected skip**. Coverage remains **SCANNED 27,824; DECODED 21,839; FAILED 0; UNKNOWN 5,957; PENDING 0; UNSUPPORTED 28; 78,498 outputs**. T09 remains IN_PROGRESS. See `docs/research/T09-notes.md`.

T10 dispatcher-body incoming-edge audit (2026-10-30): read-only Ghidra 12.2 checked the full **1,052-byte** `FUN_71002f8a50` body in exact local Pikachu 1.0.2 `main` (SHA-256 `1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8`; base `0x7100000000`). It visited **2,839,329 instructions** and found **0 direct external call/jump targets** and **0 saved references** into any byte of the body. A static data sweep covered **17 readable non-executable blocks / 9,286,364 bytes**: **0 absolute qword pointers** and **10 relative arithmetic candidates from five slots**. One aligned slot matches the known function-range metadata pattern; two other aligned slots form part of an unassigned 8-byte sequence and have no xrefs; two unaligned hits are unreferenced byte matches. **96,971 computed branch instructions** remain unresolved, so runtime dispatch cannot be excluded. No decoder output changed. Global coverage remains **SCANNED 27,824; DECODED 21,839; FAILED 0; UNKNOWN 5,957; PENDING 0; UNSUPPORTED 28; 78,498 outputs**. See `docs/research/T10-notes.md`; T10 remains IN_PROGRESS.

T10 relative-candidate table-window xref follow-up (2026-10-30): extended the same SHA-guarded Ghidra script to query the saved reference database for every byte address from center−0x40 through center+0x40 (129 addresses inclusive) around each aligned relative candidate. All three windows had **0 references**, including the regular 8-byte-spaced candidate sequence and the previously observed range-metadata slot. This adds no static edge; it does not exclude computed/runtime registration. Source totals remain **SCANNED 27,824; DECODED 21,839; FAILED 0; UNKNOWN 5,957; PENDING 0; UNSUPPORTED 28; 78,498 outputs**. T10 remains IN_PROGRESS.


T09 BSEQ parser-cursor audit (2026-10-30): an actual bounded rerun selected 28/28 demo/cutscene sources; per-source diagnostics preserve parser offset, raw command header/ID, option words, parameter byte hash and visible ASCII evidence without assigning semantics. Independent checks confirmed source hashes 28/28, absent JSON targets 28/28, and diagnostic rows 28/28. Results remain **BSEQ: SCANNED 381; DECODED 353; FAILED 0; UNKNOWN 0; UNSUPPORTED 28; PENDING 0**. Parser causes split 14 `UnicodeDecodeError` (`2D00`×6, `2E00`×8; pinned `camFile:String:256`) and 14 `KeyError` (raw IDs `7461`×2, `6465`×2, `6D6F`×8, `2F72`×1, `EB03`×1). Native full regression: **207 tests, 1 expected symlink-permission skip**. Global coverage remains **SCANNED 27,824; DECODED 21,839; FAILED 0; UNKNOWN 5,957; PENDING 0; UNSUPPORTED 28; 78,498 outputs**. See `docs/research/T09-notes.md`; T09 remains `IN_PROGRESS`.


T08 Blender asset-open gate (2026-10-30): local Blender 5.1.2 build `ec6e62d40fa9` reopened the existing mirrored GLB for `bin/battle/waza/model/bg_out_side/out_side.gfbmdl` via `bpy.ops.import_scene.gltf`; result `FINISHED`, **30 mesh objects / 64 scene objects / 1,230 vertices / 1,010 polygons**. Source SHA-256 (`2874e77d…e5a1d2`) and GLB SHA-256 (`de379ea2…22769`) matched their receipts before and after; neither file changed. This checks application importability, not material parity or GFBCol semantics. T08 totals stay **BNTX 1,344 DECODED; GFBMDL 321 DECODED; GFBANM 455 DECODED; PTCL 1,160 DECODED; GFBCol 698 UNKNOWN**; no source coverage status changed. Latest global coverage: **SCANNED 27,824; DECODED 21,839; FAILED 0; UNKNOWN 5,957; PENDING 0; UNSUPPORTED 28; 78,498 outputs**. The T08 model/texture/animation target-application acceptance item is now checked; T08 remains `IN_PROGRESS` for unresolved GFBCol schema and related format semantics. See `docs/research/T08-notes.md`.

## Latest T10 update — NSO relocation cross-reference (2026-10-30)

The new `uv run lgpe nso-relocation-crossref` command validated exact local
Pikachu 1.0.2 `0/main` SHA-256
`1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8`, parsed
both decompressed file segments and the zero-filled `.bss` image with pinned
PokeLDN, and recorded **71,687** RELATIVE/RELR relocations. It found **0**
relocation targets inside the complete 1,052-byte spawn dispatcher body
`[main+0x2f8a50, main+0x2f8e6c)` and zero hits for three exact candidate
entries. Three capture API targets match their relocation slots. The JSON
manifest is `manifests/nso-relocation-crossref.json`; it records source/tool
hashes, both image hashes, each queried range and slot/addend, plus the
read-only Ghidra trace hashes. This corroborates static address material only;
dispatcher runtime reachability and RNG initialization remain unverified.

Focused tests passed **4/4**. The full native Windows CPython 3.12.13 suite
ran **211 tests: 210 passed, 1 expected symlink-permission skip**. Refreshed source
coverage: **SCANNED 27,824; DECODED 21,839; FAILED 0; UNKNOWN 5,957; PENDING 0;
UNSUPPORTED 28; 78,498 outputs**. The original `main` hash was identical
before and after parsing. T10 remains `IN_PROGRESS`.

## Phase 5 full receipt verification and status-exit fix — 2026-10-30

A native Windows `uv run lgpe verify` pass rehashed every output receipt in the
actual project: **78,498 registered / 78,498 verified; `bad=0`; `errors=[]`**.
The run initially exited 5 because the full-mode summary counted
`failed_or_unsupported` as a failure. Auditing `manifests/failures.jsonl`
showed **34 rows, all `UNSUPPORTED`, 0 `FAILED`**: 28 BSEQ demo/cutscene
inputs and six incomplete Wwise prefetch slices (two media IDs in three banks).
The six exact slices are preserved as `.prefetch.bin` with verified receipts;
they are not represented as complete WEM files.

`verify_samples` now reports `failed`, `unsupported`, and unclassified status
counts separately. Verification exits nonzero for invalid output receipts,
actual `FAILED` rows, or unclassified statuses; expected `UNSUPPORTED` rows do
not make a clean receipt verification fail. A real targeted CLI run over
`t09-bseq-unsupported28.txt` returned **0** with `bad=0`, `failed=0`, and
`unsupported=28`. Regression coverage exercises unsupported-only, failed,
mixed, and unrecognized failure statuses. The native Windows full suite ran
**212 tests: 211 passed, 1 expected symlink-permission skip**. The full
78,498-receipt hash pass occurred before this status-count-only fix; the
verification loop and source/output hashes were not changed.

Source coverage remains **SCANNED 27,824; DECODED 21,839; FAILED 0; UNKNOWN
5,957; PENDING 0; UNSUPPORTED 28; 78,498 outputs**.


## Phase 5 verifier rerun and durable summary — 2026-10-31

The native Windows full `verify` rerun after the status-exit fix is recorded in
`manifests/runs.jsonl` as run `7eb3dc1792e9483bb0fbb39af0b51d4e`: full mode
(`sources_file=null`) started at `2026-10-30T14:30:53Z` and completed at
`2026-10-30T14:51:16Z` with exit code **0**. The command's console JSON was
not retained when its tool session ended. The current output manifest contains
**78,498** receipt rows; the failure manifest contains **34 UNSUPPORTED and
0 FAILED** rows. The completed full-mode exit code, together with the verifier's
exit contract and current manifest counts, establishes zero bad receipts and
that all 78,498 registered receipts verified; the original run's exact JSON
summary is not claimed as captured output.

That run exposed an audit gap: standalone `lgpe verify` printed the summary but
did not persist it, unlike the `run` pipeline. `cmd_verify` now appends a
`CHECKPOINT` event named `verification` containing the full summary before
printing it. The new regression test first failed because the journal only
contained `RUNNING` and `COMPLETED`, then passed after the checkpoint was added.
A real native Windows targeted command over
`docs/research/source_lists/t09-bseq-unsupported28.txt` produced
`bad=0`, `registered=0`, `selected_sources=28`, `unsupported=28`,
`failed=0`, and exit 0; run `32b79f45bf0a4911a2838eb63b1f1e78` durably records
`RUNNING → CHECKPOINT → COMPLETED`, including that summary.

The native Windows CPython 3.12.13 full suite passed **213 tests: 212 passed,
1 expected symlink-permission skip**. Current coverage remains **SCANNED
27,824; DECODED 21,839; FAILED 0; UNKNOWN 5,957; PENDING 0; UNSUPPORTED 28;
78,498 outputs**. T11 remains `VALIDATED`; T07/T08/T09/T10 retain their
previous unresolved research limits.


## T08 GFBCol slot-3 candidate observation — 2026-10-31

The Windows-native, read-only slot-3 probe verified the inventory SHA-256 and
rehashed all **698** actual GFBCol sources against `manifests/files.csv`, with
**0 source failures**. All 698 slot-3 candidates contain eight raw u32 words;
there are 487 distinct vectors. The first word is 28 in all 698 files. Under
the explicitly hypothesis-only forward-relative interpretation, it targets
word 7 in all 698; target extents fit in bounds for all 698, with target-word
values 1 (692 files), 2 (4), and 3 (2). The detailed source hashes/raw-word
report is `work/gfbcol-slot3-candidate-probe.json`, SHA-256
`a77f6ba8770c0228b3c171c39eb7e3e253981dccfc60609ed10defc44dd3c2ac`.

These byte-level regularities do not assign an offset, count, scalar type, or
collision concept. A GFBMDL six-float BoundingBox in pinned Switch-Toolbox
does not establish a GFBCol schema; the co-located GFBMDL comparison is
partial and non-probative. GFBCol remains **SCANNED 698; DECODED 0; FAILED 0;
UNKNOWN 698**. `verify-collisions` independently rechecked **698/698**
existing outputs, 698 root views, 698 nested views, and 2,219 child table
envelopes with 0 failures/errors. Overall source coverage is unchanged at
**SCANNED 27,824; DECODED 21,839; FAILED 0; UNKNOWN 5,957; PENDING 0;
UNSUPPORTED 28; 78,498 registered outputs**.

The three new focused tests passed; the full Windows suite ran **216 tests:
215 passed, one expected symlink-permission skip**. The repeatable entry point
is `pwsh -NoProfile -File scripts/Probe-GFBCol-Slot3.ps1`. WSL was not used
for the full scan because `/mnt/x` path resolution stalled in the mapped 9P
filesystem; the native PowerShell 7 run completed with no source read errors.

## T09 sequence-literal Wwise event-label candidates - 2026-10-31

The native Windows `map-sequence-audio` run rehashed **265/265 BNK/XML pairs**
and **353/353 supported BSEQ source/JSON pairs**, then wrote a new separate
candidate-label sidecar. It contains **735 bank/event records**, **1,612 exact
FNV candidate links**, **658 distinct sequence literals/event-ID values**,
**768 links** to banks named by the same sequence's parser fields, **844 links**
outside those bank sources, **0 multi-literal conflicts**, and **0 supported
sequence rows without candidates**. Those link totals are per bank/event
candidate; the existing map separately counts 768 parser rows with a
sequence-bank candidate and 181 rows with candidates only outside.

All **735/735** existing Wwise `eventName` values stay null with
`UNKNOWN_WWNAMES_DB_ABSENT`; the sidecar marks them unchanged and does not
assign sequence fields as canonical event names. Command semantics, loading,
invocation, selection, timing, and playback remain unverified. The input map
has 949 rows / 4,645,758 bytes / SHA-256
`180085cd6fd4c3f0e42d57e0996ffde54595f7573a93ab710ff69695e5671df5`. The
candidate JSONL has 735 rows / 2,213,559 bytes / SHA-256
`8fd4ecc330b0fdadac8213b71560514ab2cccfd4b1eae97906ff05dc3abe03ea`; its
summary JSON SHA-256 is
`37781432ba020207218812f1c8338ac6735ee439fa286fafa15e42449bc54cd0`. The writer uses explicit UTF-8/LF to keep the manifest bytes stable across hosts.

The WSL `/mnt/x` invocation blocked in `p9_client_rpc` for 2:24 without
changing the reports; the native Windows PowerShell run completed with exit 0.
The full native suite passed **237 tests: 236 passed and one expected
symlink-permission skip** after adding the existing local Git directory and
`.EXE/.CMD` extensions to the test process environment. Refreshed coverage:
**SCANNED 27,824; DECODED 21,839; FAILED 0; UNKNOWN 5,957; PENDING 0;
UNSUPPORTED 28; 78,498 outputs**. T09 remains `IN_PROGRESS`.
## T08 GFBCol slot-0 string-shape probe and v3 migration - 2026-10-31

Actual 1.0.2 sources: **698/698 rehashed; 0 source failures**. The read-only probe examined **807** validated root-slot-0 child tables; **807** strict length-prefixed UTF-8/NUL-terminated candidates passed, **0 unresolved**, and **45** distinct strings were observed. This remains hypothesis-only: no field names or semantic types were assigned. Production decoder v3 recorded those candidates in mirrored JSON; the real batch completed smoke 5, then 20, then **698/698 converted and verified**, with **0 failures**. Independent collision verification checked **698/698** outputs, **2,219** child-table envelopes, **0 failed, 0 pending, 0 errors**. GFBCol status stays **SCANNED 698; DECODED 0; FAILED 0; UNKNOWN 698**.

Current full coverage: **SCANNED 27,824; DECODED 21,839; FAILED 0; UNKNOWN 5,957; PENDING 0; UNSUPPORTED 28; 78,498 outputs**. Full native Windows suite: **226 tests, 225 passed, 1 expected symlink-permission skip**. Details and reproduction commands are in docs/research/T08-notes.md. Raw hypothesis report: work/gfbcol-slot0-all-v3.json (SHA-256 aefc16776cae57d467172f66e7e9b1900cb2322823c26c8b7daf329fae5c5500).
## T08 exact-main/GFBCol literal cross-reference - 2026-10-31

The new uv run lgpe crossref-gfbcol-main command rehashed the exact Pikachu 1.0.2 main before and after, rehashed all **698/698** GFBCol inputs, and validated the existing read-only Ghidra 12.2 trace. Six exact main string/BL links target main+0xb660; the full GFBCol scan contained **807** bounded slot-0 string candidates over 807 tables and 45 distinct values. Four main tokens also occur as candidate text values, totaling **188** observations (col_wall 183, col_jump 2, col_sekichiku 1, col_safety 2); col_water and col_sky were absent. The match is literal equality only; the token handler is not proven to load GFBCol, and no field semantics were assigned. manifests/gfbcol-main-token-crossref.json is **112,184 bytes**, SHA-256 07721785de914eb08e8cdebf84e7c51a68a4597f83c8bbc26da2c3737092df7e. GFBCol stays **SCANNED 698; DECODED 0; FAILED 0; UNKNOWN 698**. Full suite: **233 tests, 232 passed, 1 expected symlink skip**. Global coverage: **SCANNED 27,824; DECODED 21,839; FAILED 0; UNKNOWN 5,957; PENDING 0; UNSUPPORTED 28; 78,498 outputs**. See docs/research/T08-notes.md.

## T09 unreferenced loose WEM ID audit — 2026-10-31

The native Windows `uv run lgpe map-sequence-audio --root ..` run now writes
`manifests/wwise_unreferenced_wem_id_audit.json`. It rehashed and reparsed
**265/265** actual BNK sources, validated all **1,109/1,109** DIDX rows against
the source chunk tables, rehashed **7/7** loose WEM/WAV receipt pairs, and
rehashed **381/381** BSEQ sources (**1,411,352 bytes**). The seven WEM IDs have
**0 HIRC matches across 265 banks, 0 DIDX entries, and 0 raw BSEQ byte hits**
across 11 listed u32/u64 endian and decimal/hex ASCII encodings. No identifier
meaning or runtime use is inferred. The deterministic report is 219,059 bytes,
SHA-256 `6c09824e2227bd490a572002a03be5da02ca46fed703e044f8e2168b527b3a6f`;
all input manifest hashes and per-source receipts are recorded inside it.

Focused audit tests: **3/3**. Full native Windows regression suite: **240
tests, 239 passed, 1 expected symlink-permission skip**. BSEQ remains
**381 SCANNED / 353 DECODED / 0 FAILED / 0 UNKNOWN / 28 UNSUPPORTED**; internal
BNK media remains **1,103 DECODED_EXISTING_VERIFIED / 6 UNSUPPORTED**. Global
coverage is unchanged: **SCANNED 27,824; DECODED 21,839; FAILED 0; UNKNOWN
5,957; PENDING 0; UNSUPPORTED 28; 78,498 outputs**. T09 remains `IN_PROGRESS`;
see `docs/research/T09-notes.md`.

## T09/T10 exact-build BSEQ resource path trace — 2026-10-31

Ran two actual Ghidra 12.2 PUBLIC `-noanalysis -readOnly` scripts against the
local LGPE Pikachu 1.0.2 `0/main`, image base `0x7100000000`, source SHA-256
`1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8`. The
string pass examined 10,469 defined strings, found 79 BSEQ/Wwise marker
matches and 99 references into 10 functions; all 10 decompiled, with 0
failures. A helper pass found and decompiled 11/11 selected path, object,
request, and queue functions. Exact `main+offset` evidence shows generated
`ew*.bseq` paths, `%s.bseq` selection and `ee000.bseq` fallback, an
`ee610`/`ee615` branch, then a BSEQ path object passed at `main+0x210494` to
the shared resource helper `main+0xadc70`. That helper calls the cache/request
routine at `main+0xa63a0`, submits through `main+0x276e0`, and waits through
`main+0x23880`. The defined-string scan found no
`BelugaSound*`, `SoundPostEvent`, `AK::SoundEngine`, or `SESD` marker. This
establishes only static path references and a generic resource request/queue
chain; the final BSEQ filesystem worker and physical read are unverified.
Sequence opcode behavior, Wwise event invocation, and runtime execution remain
UNKNOWN/UNVERIFIED. The separate encounter request's OpenFile route is not
transferred to the BSEQ request. Exact addresses, script hashes, log hashes,
and commands are in T09 and T10 notes.

The native PowerShell test wrapper was corrected after an actual integration
test exposed that its Python child inherited `PATHEXT=.CPL`, hiding the local
`git.exe` required to verify the pinned PokeLDN commit. It now locates Git and
adds missing standard executable suffixes only to its child process. The
rerun passed **240 tests, 239 passed, one expected symlink-permission skip**.
A fresh `UV_PROJECT_ENVIRONMENT=/tmp/lgpe-research-wsl-venv uv run lgpe coverage`
read the generated manifests and confirmed **SCANNED 27,824; DECODED 21,839;
FAILED 0; UNKNOWN 5,957; PENDING 0; UNSUPPORTED 28; 78,498 outputs**. T09 and
T10 remain `IN_PROGRESS`; no source binaries or decoded outputs changed.

## T09/T10 BSEQ request worker follow-up — 2026-10-31

Ran the updated SHA-guarded Ghidra helper script against the local exact-build
Pikachu 1.0.2 `0/main` in `-noanalysis -readOnly` mode. The final pass
validated the request vtable in program memory and decompiled **19/19**
selected functions with **0 failures**. The selected-path object on the
fresh-request path and null optional cache value are traced through the BSEQ
constructor and into the request fields; the shared loader can reuse a
request, but runtime reuse is unknown. On the immediate TLS-manager branch,
exact vtable targets
reach the `nn::fs::OpenFile`/`GetFileSize`, `nn::fs::ReadFile`, and conditional
`nn::fs::CloseFile` call sites. The alternate queue branch is present, but its
consumer and runtime branch selection are unverified; successful physical
I/O, BSEQ semantics, Wwise invocation/playback, and gameplay effects remain
UNKNOWN/UNVERIFIED. This updates the prior “worker unverified” note to
“conditional static worker edge verified”; it does not claim runtime success.

The source tree counts did not change: **SCANNED 27,824; DECODED 21,839;
FAILED 0; UNKNOWN 5,957; PENDING 0; UNSUPPORTED 28; 78,498 registered
outputs**. BSEQ coverage remains **381 SCANNED / 353 DECODED / 0 FAILED / 0
UNKNOWN / 28 UNSUPPORTED**. Full evidence, addresses, exact hashes, and
reproduction command are in `docs/research/T09-notes.md` and
`docs/research/T10-notes.md`. T09/T10 remain `IN_PROGRESS`.

## T09/T10 BSEQ object-vtable and selector trace — 2026-10-31

The SHA-guarded Ghidra helper now inspects the vtable installed by the BSEQ
object constructor and its direct path-selection callers. The exact 1.0.2
run decompiled **27/27** selected functions with **0 failures**. The first two
object-vtable slots lead to functions that reset/release request state; this
pass did not identify the consumer for the header fields at `+0x184/+0x18c`.
Exact callers select `fileName`-based and fixed `ee*.bseq`/`em*.bseq` resource
paths, with their branch values retained as raw code evidence. This advances
resource selection but does not verify command parsing, runtime branch
selection, playback, or gameplay meaning.

Asset counts are unchanged: BSEQ **381 SCANNED / 353 DECODED / 0 FAILED / 0
UNKNOWN / 28 UNSUPPORTED**; global **27,824 SCANNED / 21,839 DECODED / 0
FAILED / 5,957 UNKNOWN / 0 PENDING / 28 UNSUPPORTED / 78,498 outputs**. Full
addresses, bounds, hashes, and reproduction command are in T09/T10 notes.
T09/T10 remain `IN_PROGRESS`.

## T09/T10 exact-main BSEQ command-consumer trace — 2026-10-31

Actual sample `bin/battle/waza/sequence/ee000.bseq` was re-read at 124 bytes
(SHA-256 `1b38facf44af506167a588da86c5a6926704336178669248e022e250366cc88f`).
The pinned LGPE SESD v3 parser returned 1 group and 5 commands; both exact-byte
serialization and semantic reparse matched. The existing mirrored JSON's
source hash, output hash, and embedded source bytes verified after normalizing
Windows path separators in its manifest row. Its header carries frame value 29,
matching the first decoded label record's end frame.

The exact 1.0.2 `main` static trace now ties the BSEQ constructor at
`main+0x2103c0` to field readers and dispatchers at `main+0x210510` and
`main+0x210880`; direct callers include `main+0x80f4d0` and `main+0x81a790`.
The first reads the copied version/frame values, walks version-shaped command
records, and calls an owner virtual slot; the second performs a target-frame
record pass through the same callback slot. A whole-instruction immediate scan
reported 320 ambiguous uses in 142 functions; field identity was assigned only
after matching the constructor stores and caller chain. Ghidra 12.2 ran
`-noanalysis -readOnly`, rechecked the original `main` SHA-256 before/after,
and decompiled **31/31** selected functions with **0 failures**. The callback
target, command effects, successful runtime I/O, and playback remain unknown.

BSEQ counts: **381 SCANNED / 353 DECODED / 0 FAILED / 0 UNKNOWN / 28
UNSUPPORTED**. Global counts are unchanged: **27,824 SCANNED / 21,839 DECODED
/ 0 FAILED / 5,957 UNKNOWN / 0 PENDING / 28 UNSUPPORTED / 78,498 outputs**.
T09 and T10 remain `IN_PROGRESS`; see `docs/research/T09-notes.md` and
`docs/research/T10-notes.md`.

Post-update native regression: `pwsh.exe -NoProfile -File
scripts/Test-Project.ps1` exited 0 with **240 tests, 239 passed, and 1
expected symlink-permission skip**. The containment test's expected path
rejection was printed as a `ValueError`; the test runner reported `OK`.

## T09/T10 BSEQ delegate and dispatch update — 2026-10-31

Source coverage is unchanged: **27,824 SCANNED; 21,839 DECODED; 0 FAILED;
5,957 UNKNOWN; 0 PENDING; 28 UNSUPPORTED; 78,498 registered outputs**. BSEQ
coverage remains **381 SCANNED; 353 DECODED; 0 FAILED; 0 UNKNOWN; 28
UNSUPPORTED**. The exact 1.0.2 `main` SHA-256 remains
`1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8`.

A 40/40 read-only Ghidra helper pass and an 8/8 callback decompilation pass
resolved the constructed BSEQ delegate from controller `+0x3e0` through
sequence object `+0x190` to callback handler `main+0xaa0eb0`. `main+0x210510`
passes mode 0 to the pointer-table route; `main+0x210880` passes mode 1 to the
inline-switch route. The bounded handler-table scan found 256/256 executable
pointers with no terminator in range. The pinned parser dictionary has 227
unique IDs, all numerically joined to slots 0–226; all five commands in actual
`ee000.bseq` were mapped to exact-build targets and decompiled. The
`DummyLabel` target at `main+0xada060` is now byte-verified as a single
`ret` (`c0 03 5f d6`) with one DATA reference from slot 0. Manifest:
`manifests/bseq-runtime-dispatch.json`; detailed hashes and commands:
`docs/research/T09-notes.md` and `docs/research/T10-notes.md`.

The callback pass added five missing function boundaries to the local Ghidra
project database. Both passes verified the original `0/main` hash before and
after; no original game file or decoded asset output changed. Runtime dispatch,
the full handler-table length, command bounds, and command/gameplay semantics
remain UNKNOWN. T09/T10 remain `IN_PROGRESS`.

Focused tests for the new dispatch manifest parser passed **4/4**. Native
Windows full regression passed **244 tests: 243 passed, 1 expected
symlink-permission skip** via `pwsh.exe -NoProfile -File
scripts/Test-Project.ps1`.

## T08 exact-main GFBCol caller-candidate refinement — 2026-10-31

The SHA-guarded, read-only Ghidra 12.2 probe temporarily bounded the code at
`main+0x24f460..main+0x24f693` (564 bytes / 141 instructions). All six direct
`main+0xb660` calls pass the exact `col_wall`, `col_water`, `col_jump`,
`col_sky`, `col_sekichiku`, and `col_safety` literals. Decompilation records
the returned value at `+0x58`, a comparison with opaque `param_5`, per-token
counter writes at `+0x30..+0x44`, fallback `+0x48`, and total `+0x4c`. The
candidate has one incoming reference: a pointer stored in writable,
non-executable `.data` at `main+0x15437d8`; no instruction caller was found.
This is candidate-boundary and data-flow evidence only. GFBCol field names,
types, loader association, runtime reachability, and collision semantics stay
UNKNOWN; all **698** GFBCol sources remain `SCANNED`, with **0 DECODED, 0
FAILED, 698 UNKNOWN**.

The refreshed report
`manifests/gfbcol-main-token-crossref.json` is **552,293 bytes**, SHA-256
`ebc080de34c45bcab5889d7944d27a1d98561313445d4d264a8c9e89167947a8`. Its
`main.path` is relative to `game_root`; it contains 13,817 CRLF lines and no
bare LF, making output stable between Windows and WSL. The report preserves
the exact-main hash, all 698 per-source hashes and all 807 candidate observations, plus
the 6 token callsites, the temporary-boundary trace, and the script/wrapper/log
hashes. The original `main` hash remains
`1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8`.

The handler wrapper was run twice after clearing the append-only Ghidra script log; each run left exactly one SUMMARY, and cross-reference regeneration succeeded twice with the same report SHA-256. The owner trace parser reads every ENTRY_XREF line, including address-valued owners and assembly text, and requires its count to match the summary before accepting the single DATA reference.

Native Windows verification after the changes passed **14/14 focused tests** and
the full suite **251 tests: 250 passed, 1 expected symlink-permission skip**.
`verify-collisions` rehashed and verified **698/698** root and nested outputs,
including **2,219** child-table envelopes, with **0 failed/pending/errors**.
The latest coverage refresh remains **27,824 SCANNED; 21,839 DECODED; 0
FAILED; 5,957 UNKNOWN; 0 PENDING; 28 UNSUPPORTED; 78,498 registered outputs**.
An attempted WSL collision verification stalled in `p9_client_rpc` on the
`/mnt/x` mount; the native PowerShell verification completed successfully.
Reproduction and evidence hashes are in `docs/research/T08-notes.md` and the
manifest. No source or decoded output was changed.


## T10 exact-main BSEQ handler-byte correction and table scan — 2026-10-31

A SHA-guarded Ghidra 12.2 read-only probe corrects the earlier `br x16` note
for BSEQ `DummyLabel`: `main+0xada060` contains one AArch64 `ret` instruction
with bytes `c0 03 5f d6`, and its only saved incoming reference is the DATA
pointer at handler-table slot 0 (`main+0x15d4c70`). The original Pikachu
1.0.2 `main` SHA-256 remains
`1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8`; the
probe used `-noanalysis -readOnly` and checked the source before and after.

An extension beyond the prior 256-slot pointer scan inspected **1,096** mapped
values at indexes **256–1351**: **858** pointed to executable memory and **238**
did not. The configured eight-value non-executable run at 1344–1351 is a scan
stop condition only; adjacent executable pointers may be unrelated data, so
table length and ID bounds remain UNKNOWN. The report is
`manifests/bseq-dispatch-boundary.json`. Five new parser tests and four
existing dispatch tests pass. BSEQ coverage remains **381 SCANNED / 353
DECODED / 0 FAILED / 0 UNKNOWN / 28 UNSUPPORTED**. Overall coverage remains
**27,824 SCANNED / 21,839 DECODED / 0 FAILED / 5,957 UNKNOWN / 0 PENDING /
28 UNSUPPORTED / 78,498 outputs**; T10 remains `IN_PROGRESS`.
ROGRESS`.


### 2026-10-31 T10 capture-getter cross-reference checkpoint

The exact-build, Ghidra 12.2 read-only probe now includes the
`main+0x1a64c0` API wrapper and its `main+0x1aae40` callsite, as well as the
shared `main+0x28ee10` caller matrix. It decompiled 7 functions / 1,264
instructions with 0 failures and discarded one temporary function boundary.
One branch copies an opaque qword from `param_2+8` to a returned object at
`+0xc8`; outcome meaning, RNG linkage, and runtime reachability remain
UNKNOWN/UNVERIFIED. Focused tests pass 5/5; native full regression passes
**261 tests, 260 passed, one expected skip, in 64.747s**. No decoder state
changed. Coverage is **SCANNED 27,824; DECODED 21,839; FAILED 0; UNKNOWN 5,957;
PENDING 0; UNSUPPORTED 28; 78,498 outputs**. T10 remains `IN_PROGRESS`; see
`docs/research/T10-notes.md` and `manifests/capture-getter-callers.json`.

### T10 capture API resource literal search — 2026-10-31

Focused tests passed **3/3**. Native Windows full suite passed **264 tests (263 passed, 1 expected symlink-permission skip) in 40.392s**.

Native Windows `capture-api-resource-search` run on the exact local Pikachu 1.0.2 build (`main` SHA-256 `1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8`): **SCANNED 11,482 files / 35,631,062 bytes; DECODED 0; FAILED 0; UNKNOWN 0** for this bounded string-search operation. Scope: 10,770 RomFS message `.dat`/`.tbl`, 7 loose battle AI `.amx`, and 705 raw extracted `script_amx.gfpak` members. There were 0 literal occurrences of `CaptureCall` or `GetCaptureResult` across ASCII, UTF-16LE, and UTF-16BE. This does not alter source-wide decoder coverage: **SCANNED 27,824; DECODED 21,839; FAILED 0; UNKNOWN 5,957; PENDING 0; UNSUPPORTED 28; 78,498 registered outputs**. Report and reproduction details: `manifests/capture-api-resource-search.json` and `docs/research/T10-notes.md`. T10 remains `IN_PROGRESS`.

### T10 script-registry operand scan — 2026-10-31

Native Windows suite: **269 tests; 268 passed; 1 expected symlink-permission skip; 67.098s**.

Exact 1.0.2 `main`: **SCANNED 2,839,329 instructions; 13 explicit page-operand hits; DECODED 4/4 owner functions; FAILED 0 decompilations; UNKNOWN 4 distinct additional page-address roles**. Twelve hit contexts resolve to those four additional page offsets; one computes the `MapChangeCore_` name-pointer cell. The contexts do not show a computed `CaptureCall` or `GetCaptureResult` function slot. Runtime dispatch remains UNKNOWN. Report: `manifests/script-registry-operand-scan.json`; full source-wide totals remain **SCANNED 27,824; DECODED 21,839; FAILED 0; UNKNOWN 5,957; PENDING 0; UNSUPPORTED 28; 78,498 outputs**. T10 remains `IN_PROGRESS`.


### T10 exact-build registry cell values (2026-10-31)

The read-only Ghidra follow-up read **7/7 selected data cells** from the exact Pikachu 1.0.2 `main`; its SHA-256 stayed `1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8`. The CaptureCall and GetCaptureResult slots contain `main+0x1a61e0` and `main+0x1a64c0`; each has **0 saved incoming references** in the persisted Ghidra database. Four neighboring candidate cells resolve to **3 unique executable targets**; **DECODED 3/3** temporary function boundaries, each a 4-byte `ret`; **FAILED 0**. Roles of those cells and dynamic/runtime use of the API slots remain **UNKNOWN**. See `docs/research/T10-notes.md` and `manifests/script-registry-operand-scan.json`. Overall source coverage remains **27,824 SCANNED; 21,839 DECODED; 0 FAILED; 5,957 UNKNOWN; 0 PENDING; 28 UNSUPPORTED; 78,498 outputs**. T10 remains `IN_PROGRESS`.

### T07 localized sort-string verification refresh — 2026-10-31

Rechecked the saved v19 Ghidra code context against the trace script. The
u16 accessor at `main+0x377a20` belongs to the distinct `zukan_*` helper path
through `main+0x176940` / `main+0x377820`; it is not evidence for the first
resource of the localized loader at `main+0x374530`. The localized chain still
has two traced readers: `main+0x374a90` for the second resource and
`main+0x374ad0` for the third. The 27 `*_initial_index.dat` sources therefore
remain UNKNOWN.

Native Windows `uv run --offline --python 3.12 lgpe verify --root ..
--sources-file configs/sort_string_sources.txt` selected the 81 source paths
and rehashed all **54** receipt-backed source/output pairs:
**registered 54; verified 54; bad 0; errors []; failed 0; unsupported 0**.
The 27 UNKNOWN inputs have no output receipts. Localized totals remain
**SCANNED 81; DECODED 54; FAILED 0; UNKNOWN 27; PENDING 0; UNSUPPORTED 0**.
Global totals remain **SCANNED 27,824; DECODED 21,839; FAILED 0; UNKNOWN
5,957; PENDING 0; UNSUPPORTED 28; 78,498 outputs**. The first WSL attempt
was stopped after its Python process blocked in mapped-drive I/O; the native
Windows run completed. No game source or decoded output changed.

The NSO relocation test module passed **4/4** and the full native Windows
regression passed **269 tests with 1 expected symlink-permission skip** in
19.477 seconds. The final run used the temporary Python 3.12 environment and
explicitly propagated both Git's directory in `PATH` and `.EXE` in
`PATHEXT`; without `PATHEXT`, `shutil.which("git")` could not locate the
required executable in the launched Python process. The earlier failed
invocation was an environment setup issue; the corrected full rerun passed.

### T11 Windows one-click entrypoint and mapped-drive scan - 2026-10-31

Updated `scripts/Start-Research.ps1` to default native Windows uv runs to
`%TEMP%\lgpe-research-win-venv`, resolve Git from `PATH` or known local
install locations, and add `.COM`, `.EXE`, `.BAT`, and `.CMD` to `PATHEXT`
before `uv sync` and Python subprocesses. Added a regression test for this
ordering. The focused entrypoint test passed **1/1**; the full native Windows
suite passed **270 tests (269 passed, one expected symlink-permission skip) in
59.168 seconds**.

Ran `scripts/Start-Research.ps1 -Limit 1 -Timeout 120` against the actual
parent game directory. The wrapper selected the isolated Windows uv
environment, found `D:\Tool\Git\cmd\git.exe`, and `uv sync` succeeded.
The real `lgpe run` then scanned the mapped `X:` source root without emitting
its first scan checkpoint after about 13 minutes. Its Python worker used
roughly 90 seconds of CPU over that interval, consistent with prolonged
mapped-drive I/O. The process tree was stopped; journal run
`29068bac30c147c39cd3bae0ff746089` remains `RUNNING` with only sequence 0.
No scan summary or new source-coverage count was produced, and no original
game files or decoded outputs were changed. The last verified global totals
remain **27,824 SCANNED; 21,839 DECODED; 0 FAILED; 5,957 UNKNOWN; 0 PENDING;
28 UNSUPPORTED; 78,498 registered outputs**. Re-run this command on a local
fast filesystem or use the existing native per-domain wrappers and manifests
to avoid waiting on the mapped-root census.

### T11 cross-platform JSON report replay - 2026-10-31

Native Windows replay of `uv run lgpe capture-api-resource-search --root ..`
read **11,482 actual files / 35,631,062 bytes** under the selected message,
loose AMX, and extracted `script_amx.gfpak` scopes. It found **0 literal
occurrences** of `CaptureCall` or `GetCaptureResult`; the source `main` hash
was `1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8`.
The exact-main registry replay scanned **2,839,329 instructions**, retained
13 explicit operand hits across 4 owner functions, and reported **0
decompilation failures**. Both regenerated JSON reports match the committed
files byte for byte.

The CLI's shared `write_json` helper now specifies LF for its default newline
translation; the explicit GFBCol CRLF setting remains intact. Added byte-level
regressions to both CLI report tests. WSL focused runs passed **3/3** and
**5/5**; native Windows ran **270 tests, 269 passed, one expected
symlink-permission skip**. These report checks do not alter source-wide
coverage, which remains **27,824 SCANNED; 21,839 DECODED; 0 FAILED; 5,957
UNKNOWN; 0 PENDING; 28 UNSUPPORTED; 78,498 registered outputs**.

### T00/T01 full source inventory refresh - 2026-11-01

The native Windows rerun of doctor, `tree-catalog`, full `scan --root ..`,
`compare-tree`, and coverage completed against the actual extracted 1.0.2
parent. Both `0/` and `1/` were found. Scan coverage: **27,824 files (6
ExeFS / 27,818 RomFS), 0 access anomalies, 0 zero-byte files**; this header
scan used `full_sha256=false`. The snapshot comparison is **27,819 matched,
0 snapshot-only, 5 scan-only**. Those five are the known extensionless
ExeFS files `main`, `rtld`, `sdk`, `subsdk0`, and `subsdk1`, which the tree
CSV intentionally omits because it catalogs suffix-bearing entries. The
separately computed SHA-256 of `0/main` after the scan remains
`1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8`.

To reduce mapped-drive latency, source listing now uses a sorted
`os.scandir` traversal that excludes symlinks, and exhaustive scans probe in
bounded batches of eight while emitting rows in stable path order. `--limit`
scans remain sequential and exact. The real 10,771-file `bin/message`
enumeration took **10.583s** with the prior `rglob` checks and **0.054s** with
the new walk, with identical paths. A 1,000-file read-only probe sample took
**7.524s sequential / 0.448s with eight workers**, with identical metadata.
The full scan took **10m42.9s sequential / 1m51.2s concurrent** and returned
the same 27,824 paths. `snapshot_file_inventory.csv` now writes LF and
reproduces the committed bytes on Windows. The exact path reconciliation is
in `docs/catalog/scan_snapshot_diff.json`; the scan summary is in
`manifests/files.summary.json`.

The refreshed global decoder totals remain **27,824 SCANNED; 21,839
DECODED; 0 FAILED; 5,957 UNKNOWN; 0 PENDING; 28 UNSUPPORTED; 78,498
registered outputs**. WSL pipeline tests passed **8/8**. Native Windows full
regression passed **273 tests (272 passed, one expected symlink-permission
skip)**.

## BFOTF batch follow-up (2026-11-01)

The refreshed real-byte scan identified all **3 `.bfotf`** headers as BFOTF
and the single `num_00.bffnt` header as BFFNT. `uv run lgpe decode-fonts
--limit 1 --execute` selected one actual file; the subsequent `--limit 0
--execute` batch completed all three with **3 DECODED, 0 FAILED, 0 UNKNOWN,
0 PENDING**. Outputs preserve each original relative directory and basename,
changing only the extension to `.otf`. Their signatures are `OTTO`, and the
10/15/15 table directories and table ranges pass structural checks. Detailed
input/output byte counts and SHA-256 values are in `docs/research/T08-notes.md`
and the ignored `manifests/fonts.jsonl` / `manifests/outputs.jsonl`.

After the batch, `uv run lgpe verify --sources-file
work/font-verify-sources.txt` verified **3/3 receipts**, `bad=0`, `failed=0`.
Source rehashes match all three recorded hashes. The BFFNT source is explicitly
identified but remains **UNKNOWN**: its pinned BXFNT class has no validated
headless export path in this environment, so no decoded output is claimed.

The updated source-wide totals are **27,824 SCANNED; 21,842 DECODED; 0
FAILED; 5,954 UNKNOWN; 0 PENDING; 28 UNSUPPORTED; 78,501 registered
outputs**. Re-run `uv run lgpe scan`, `uv run lgpe plan`, `uv run lgpe
compare-tree`, and `uv run lgpe coverage` to reproduce the inventory and
counts. Tree reconciliation remains **27,819 matched, 0 snapshot-only, and
5 scan-only** (extensionless ExeFS files). The native Windows suite passed
**283 tests (282 passed, one expected symlink-permission skip)**, exit 0.

## BFOTF batch review hardening — 2026-11-01

Independent review found and reproduced batch reliability gaps. The
selected-source path builder records unsafe catalog paths instead of silently
dropping them, isolates source-resolution and `Path.resolve()` loop errors to
their rows, rejects decoded-root and output-path symlink/junction redirection,
and only removes a partial output after its filesystem identity matches the
current writer. Receipt persistence precedes the domain success manifest; a
rerun can re-decode and adopt a complete unreceipted output only after exact
source/output byte comparison. Legacy success rows without a receipt marker
look up central receipts by method, source, partition, and verifier-mapped
source/output path; invalid-root entries are replaced when a correct receipt
is rebuilt.

Native Windows regressions passed **14/14** for the font batch, including a
real `mklink /J` output-redirection case, selected and unselected path-loop
cases, an interrupted receipt case, a legacy manifest with a removed global
receipt, and a receipt that pointed to another project root. The full Windows
suite passed **294 tests: 293 passed, 1 expected symlink-permission skip**. No
actual source or output bytes changed; BFOTF remains **3 DECODED / 0 FAILED / 0
UNKNOWN** and BFFNT remains **1 UNKNOWN**. Global coverage is unchanged at
**27,824 SCANNED; 21,842 DECODED; 0 FAILED; 5,954 UNKNOWN; 0 PENDING; 28
UNSUPPORTED; 78,501 outputs**. See `docs/research/T08-notes.md`.

## BFFNT NX export — 2026-11-01

Read the pinned Switch-Toolbox BXFNT implementation and added a bounded,
headless adapter for the local NX `FFNT` version `0x04010000`. The real
`bin/font/num_00.bffnt` input (140,340 bytes) parses as six valid sections,
including 218 width entries and three character maps. Its TGLP references a
single 135,272-byte embedded BNTX at source offset `0x1000`; BNTX-Extractor
identifies BC4_UNORM at 512×512 and native FFmpeg produces a validated PNG.
The batch writes a path-mirrored JSON structure index and preserves the BNTX
and PNG at `num_00.bffnt.contents/Sheet_0.*`; it records source/output hashes
and three receipts. Other platform/version and multi-sheet variants remain
UNKNOWN/UNSUPPORTED. Full hashes and reproduction commands are in
`docs/research/T08-BFFNT-notes.md`.

Actual Windows execution: **1 BFFNT decoded, 0 failed, 0 unknown, 0
unsupported**; selected receipt check **3/3 verified, bad=0**. Source-wide
coverage is now **27,824 SCANNED; 21,843 DECODED; 0 FAILED; 5,953 UNKNOWN; 0
PENDING; 28 UNSUPPORTED; 78,504 outputs**. The source was only read; three new
derived outputs were written under `decoded/`.

After integrating the BFFNT batch and retry path, native Windows regression
passed **302 tests (301 passed, one expected symlink-permission skip)**. WSL
focused checks also passed: BFFNT parser/batch/CLI **7/7**, CLI pipeline
**9/9**, and BFOTF batch **14/14**.


Latest complete regression rerun: `GIT_CONFIG_COUNT=1
GIT_CONFIG_KEY_0=safe.directory GIT_CONFIG_VALUE_0='*' PYTHONPATH=src python3
-m unittest discover -s tests` passed **302/302** in WSL. The process-local Git
setting allows the exact pinned pkNX checkout to be read without changing
global configuration. A native Windows rerun reached all 302 tests but had one
environment error in the existing capture cross-reference CLI test: it could
not write `manifests/capture-getter-crossref-test.json` through the mapped UNC
share (`PermissionError` on `\\192.168.1.5\j\ROMS\...`); the remaining tests
passed and the expected symlink-permission case was skipped. This does not
affect the actual BFFNT decode or its 3/3 output verification. The BFFNT source
hash was rechecked as
`5a4228c020523d3f260be26ccae284dfff7a7af30b835ed73388e937d5bcc9bc`; the JSON,
BNTX, and PNG output hashes still match the decode manifest.


## Cross-platform test isolation follow-up — 2026-11-01

The capture cross-reference CLI test now creates a temporary project tree, copies
in the two provenance files whose hashes the CLI records, patches the CLI
project root for the invocation, and lets `TemporaryDirectory` remove the test
manifest. It no longer writes into the shared repository. The focused test
passed 5/5 on WSL. Re-running the native Windows suite with
`scripts/Test-Project.ps1` passed **302 tests (301 passed, one expected
symlink-permission skip)**, exit 0; the prior mapped-UNC `PermissionError` is
resolved. The WSL full suite remains **302/302 passed** with the process-local
Git safe-directory setting.
Coverage is unchanged at **27,824 SCANNED; 21,843 DECODED; 0 FAILED; 5,953 UNKNOWN; 0 PENDING; 28 UNSUPPORTED; 78,504 outputs**.
