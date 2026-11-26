# T09 — Real Wwise WEM decoding with vgmstream

Evidence date: 2026-10-28 (Asia/Shanghai). Actual read-only input root is
`../1.0.2/2b7730a9e56498bbafac2002d4908c6b_NCA/1/`.
WSL does not mount X:. Tests and tools were executed through Windows Python,
with an existing WSL directory as process cwd and explicit Windows paths.
No original files were changed; every sample was SHA256 checked before/after conversion.
Texture, model, animation, particle and WEM samples were expanded to bounded 20-file batches; a separate wwiser adapter now records BNK hierarchy XML.

Final batch state (2026-10-29): all 1,134 WEM sources have validated WAV outputs, and all 265 BNK sources have XML hierarchy outputs (245 newly parsed plus 20 previously verified); both batches have zero failed or pending sources. Animation and particle JSON are structure-only results; rendering remains unsupported. BNK event names are not inferred where wwiser has no name database.
## Source, executable and license

- Official upstream: [vgmstream](https://github.com/vgmstream/vgmstream).
- Source/release: **r2168**, exact source commit
  `d9875b1fff307e4759dfb85e49e3d5e6fb196f7c`.
  `git ls-remote https://github.com/vgmstream/vgmstream refs/tags/r2168` confirmed
  the release tag equals the already pinned local source HEAD.
- The source `COPYING` grants ISC-style permission with additional portions notices.
  The official Windows archive includes COPYING and open-source codec DLLs;
  retain all notices. No proprietary Wwise SDK or keys were used.
- CLI reports `vgmstream CLI decoder r2168 (Oct 25 2026)`.
- Download: [official vgmstream-win64.zip](https://github.com/vgmstream/vgmstream/releases/download/r2168/vgmstream-win64.zip).
- Archive SHA256: `692d45070852a35c1fa42726aa3c9de528e44eec925d37d99b1074256b99a229`.
- Installed only under ignored `tools/bin/vgmstream-r2168/`.
- The latest-release GitHub API lookup failed HTTP 403 rate limit exceeded.
  Official release HTML and its official download succeeded. This was a lookup
  failure, not a decoder failure.

## Actual source and output

- Original RomFS path: `bin/sound/NX64/wwise/bank/1001133599.wem` (368,150 bytes).
- Original SHA256: `a73d56ecf5db7dd8d9a6ab93080ddd1a5746fac4d37e4b65f853d856fc552022`.
- Output: `decoded/1.0.2/romfs/bin/sound/NX64/wwise/bank/1001133599.wav` (1,097,276 bytes).
- Output SHA256: `a117c721759309a25dbe11e6576a6958cd767df06d743c3316dcea203f3bbb93`.
- Validated metadata: `{"channels": 2, "sample_rate": 48000, "frames": 274308, "pcm_bytes": 1097232}`.

Original header begins `524946460e9e050057415645666d7420`.
vgmstream recognized Audiokinetic Wwise RIFF, **libopus Opus**, 48,000 Hz, stereo,
274,308 samples (**5.715 seconds**). `-i` suppresses loop repetition so the output
is exactly one stream pass. Python's WAV reader independently verified PCM16,
2 channels, 48,000 Hz, 274,308 frames and 1,097,232 PCM bytes. WAV total size is
1,097,276 bytes. Repeated fresh conversion matched the SHA256 above.
This verifies decoding/container structure and stream length; listening was not
performed. No blanket audio-format/BNK support claim follows from one sample.

## Reproduction

```powershell
$vgm = './tools/bin/vgmstream-r2168/vgmstream-cli.exe'
& $vgm -m '../1.0.2/2b7730a9e56498bbafac2002d4908c6b_NCA/1/bin/sound/NX64/wwise/bank/1001133599.wem'
& $vgm -i -o '<scratch>/out.wav' '../1.0.2/2b7730a9e56498bbafac2002d4908c6b_NCA/1/bin/sound/NX64/wwise/bank/1001133599.wem'
.venv/Scripts/python.exe -m lgpe_research.assets_decode --root . --execute
```

Actual adapter command/stdout/stderr:

```json
{
  "command": [
    "\\\\192.168.1.5\\j\\ROMS\\Nintendo Switch\\Pokemon\\Pokemon Lets Go Pikachu\\LGPE-Research\\tools\\bin\\vgmstream-r2168\\vgmstream-cli.exe",
    "-i",
    "-o",
    "\\\\192.168.1.5\\j\\ROMS\\Nintendo Switch\\Pokemon\\Pokemon Lets Go Pikachu\\LGPE-Research\\work\\wem-yx1d_jsr\\out.wav",
    "\\\\192.168.1.5\\j\\ROMS\\Nintendo Switch\\Pokemon\\Pokemon Lets Go Pikachu\\1.0.2\\2b7730a9e56498bbafac2002d4908c6b_NCA\\1\\bin\\sound\\NX64\\wwise\\bank\\1001133599.wem"
  ],
  "cwd": null,
  "returncode": 0,
  "stdout": "decoding \\\\192.168.1.5\\j\\ROMS\\Nintendo Switch\\Pokemon\\Pokemon Lets Go Pikachu\\1.0.2\\2b7730a9e56498bbafac2002d4908c6b_NCA\\1\\bin\\sound\\NX64\\wwise\\bank\\1001133599.wem\nsample rate: 48000 Hz\nchannels: 2\nchannel mask: 0x3 / FL FR\nstream total samples: 274308 (0:05.715 seconds)\nencoding: libopus Opus\nlayout: flat\nmetadata from: Audiokinetic Wwise RIFF header\nbitrate: 515 kbps\nplay duration: 274308 samples (0:05.715 seconds)\n",
  "stderr": ""
}
```

The adapter decodes into a temporary `work/wem-*` path, verifies WAV semantics,
then exclusively writes the correlated mirrored path. Existing output files are
validated and explicitly tagged as existing, never overwritten. Structured source
and output hashes, exact command and binary SHA256 are in `logs/assets_samples.jsonl`.

## Remaining work

All WEM files have been converted and validated, but only the representative sample
has a separately documented codec inspection. BNK hierarchy XML was produced for
all 265 files; static HIRC/event reachability and sourceID-to-WEM manifest links
are now generated below. DIDX/DATA extraction semantics, some unresolved external
media IDs, event names, and runtime sequence choice remain open. wwiser did not
find `tools/src/wwiser/wwnames.db3`, so event names remain unresolved. The batch
manifests record per-source and per-output hashes and validation results. See T08
for related asset smoke tests.


## BNK sample and batch

- Input: bin/sound/NX64/wwise/bank/Battle_cutin.bnk (1,793 bytes), signature Wwise BKHD.
- Input SHA256: 98ca1dc35a08084cb4d1eda0db7b442df6f7536bb41c8e410362eb410527987a.
- Output: decoded/1.0.2/romfs/bin/sound/NX64/wwise/bank/Battle_cutin.xml (142,220 bytes), preserving the source path and replacing only the extension.
- Output SHA256: 57a89211fe6c649401616aed1a31f527e33dca9eb4d342905b5a5876b3a205eb.
- XML validation: root root, 2 top-level elements. The original SHA256 matched before and after parsing.
- wwiser version 20260808, exact source commit 08e937b649bc7007c234bbd59e34a41d5eef3b38; Python 3.12.14. wwiser did not find tools/src/wwiser/wwnames.db3, so event IDs and structural fields are preserved without guessed names.
- A separate two-bank config smoke test emitted valid XML for Battle_cutin.bnk and BGM_Common.bnk; it confirmed #@new config blocks isolate their output names. The final `manifests/bnk.jsonl` has 265 rows: 245 newly decoded plus 20 previously verified, zero failed, zero pending. Output XML files preserve source-relative paths and replace only the extension.
- wwiser source checkout has no root license file; retain the checkout locally and do not redistribute source based on an assumed license.

WEM full-batch counts are from manifests/audio.jsonl: 1,114 DECODED plus 20 DECODED_EXISTING_VERIFIED, 0 failed, 0 pending. Every row includes source/output SHA256 and a WAV validation result. BNK counts are from manifests/bnk.jsonl and likewise carry source/output hashes and XML validation.

Reproduction:

    uv run lgpe decode-audio --limit 0 --execute --timeout 120
    uv run lgpe decode-banks --limit 20 --execute
    uv run lgpe decode-banks --limit 0 --execute

## Static event-to-WEM mapping — 2026-10-29

The CLI `uv run lgpe map-audio-events` parses the existing mirrored wwiser XML
for all 265 successful BNK manifest rows and checks each current BNK SHA-256 and
each XML SHA-256 against `manifests/bnk.jsonl`. It parses the 1,134 WEM entries
from `manifests/audio.jsonl`; matches preserve the source path and source/output
hash receipts from that manifest. The command does not rewrite BNK, WEM, XML, or
WAV data. Its deterministic JSONL output is the ignored file
`manifests/wwise_event_media.jsonl` (6,934,629 bytes on the verified run).

The pinned wwiser source provides the field-level basis:

- `tools/src/wwiser/wwiser/generator/render/bnode_hircs.py:128-171` reads
  `CAkEvent.ulActionID` and `CAkAction.idExt` (with legacy `ulTargetID` fallback).
- `bnode_hircs.py:198-208` reads the Play action's `bankID` (legacy `fileID`).
- `bnode_hircs.py:281-310`, `351-384`, and `463-520` expose switch-node,
  container-child, and music-playlist segment references; `531-570` exposes
  music-segment children and track sources.
- `tools/src/wwiser/wwiser/generator/render/bnode_source.py:95-109` documents
  that newer banks use `sourceID` as the `.wem` number. Every parsed bank here
  reports Wwise version **128**.

The mapper keeps numeric IDs, bank IDs, object classes, XML field offsets, and
source/output receipts. For Play actions, it resolves a target only when the
declared bank ID and HIRC object ID both identify exactly one object in the
loaded batch. References without bank context resolve only when the HIRC ID is
globally unique; duplicates remain ambiguous. WEM matching is an exact decimal
filename-stem match against the audio manifest. The v2 map also joins each
reachable media `sourceID` to a DIDX media ID only within the same parsed
`BankHeader` ID, and only exposes the extracted output when that BNK's SHA-256
matches the independently validated BNK source receipt. These are static
reachability and index links, not proof of runtime playback or audible output.

Actual run result:

| Measure | Count |
|---|---:|
| BNK/XML pairs parsed and hash-checked | 265 / 265 |
| Bank ID values unique in this batch | 265 |
| Bank version | 128 (all 265) |
| `CAkEvent` records | 2,476 |
| Event/action JSONL rows | 2,552 |
| Distinct event-to-WEM path pairs | 2,251 |
| Distinct WEM IDs referenced | 1,127 of 1,134 manifest WEMs |
| Receipt-backed WAV references | 2,438 |
| Event/action rows with a matched WEM manifest entry | 1,151 |
| Event/action rows with media IDs but no local WEM manifest name | 1,160 |

The remaining row states are retained, not silently discarded: 138 action target
IDs are absent from their declared bank; 27 target IDs are ambiguous across the
loaded banks when no declared bank context is available; 5 IDs are absent from
the global HIRC index; 5 targets are zero/missing; and 66 action rows have no
reachable media source. Seven WEM manifest IDs do not occur in these event
graphs. No conclusion is made that these are orphaned: they may be loaded by
other runtime paths. `wwnames.db3` is absent, so event names remain `null` with
`UNKNOWN_WWNAMES_DB_ABSENT` status.

Representative cross-reference from the generated JSONL:

- `bin/sound/NX64/wwise/bank/BGM_Common.bnk`, event ID `45057678`
  reaches `CAkMusicTrack` object `974364983`; its `AkMediaInformation.sourceID`
  is `1001133599` at XML offset `80625`.
- The exact manifest path is
  `bin/sound/NX64/wwise/bank/1001133599.wem`, source SHA-256
  `a73d56ecf5db7dd8d9a6ab93080ddd1a5746fac4d37e4b65f853d856fc552022`, with
  mirrored WAV path
  `decoded/1.0.2/romfs/bin/sound/NX64/wwise/bank/1001133599.wav` and SHA-256
  `a117c721759309a25dbe11e6576a6958cd767df06d743c3316dcea203f3bbb93`.

The original four unit tests cover cross-bank declared-ID resolution,
duplicate-ID ambiguity, unmatched WEM IDs with field offsets, and XML hash
mismatch rejection. The later v2 mapping adds positive/negative same-bank DIDX
joins, source-BNK hash checks, and prefetch-fragment state tests below. WEM/WAV
byte hashes in this map are receipt-backed by `manifests/audio.jsonl`; full
output verification evidence is recorded in T11. Runtime state/switch choice,
probability, and event names remain open.

## Embedded BNK media extraction and WAV decoding — 2026-10-29

The source-backed parser in `src/lgpe_research/bnk_media.py` currently accepts
only Wwise bank version 128. It reads sequential chunk headers, preserves each
`DIDX` record's zero-based index, media ID, offset, size, and original 12-byte
index record, then copies only the bounded slice of the matching `DATA` payload.
The extracted bytes must validate as RIFF/WAVE before they receive a `.wem`
output path. The exact source basis is the pinned wwiser checkout:

- `tools/src/wwiser/wwiser/parser/wparser.py:188-276` reads
  `AkBankSourceData` fields, including the memory media size.
- `wparser.py:3386+` retains v128 `DATA` as an opaque payload;
  `wparser.py:3788-3800` parses `DIDX` entries as ID, offset, and size.
- `tools/src/wwiser/wwiser/parser/wdefs.py:1079-1084` identifies v112+
  `StreamType` variants. This extractor uses the actual bank `DIDX/DATA`
  offsets, not inferred stream flags or event-graph reachability.
- `tools/src/wwiser/doc/WWISER.md:114-115` describes internal WEM storage in
  `DATA` and its `DIDX` index.

The bounded CLI is `uv run lgpe decode-bnk-media`; `--sources-file` limits bank
reads before parsing, and `--limit` round-robins selected members over the
selected banks. A first WSL run over five banks stopped in Linux state `D`
(`p9_client_rpc`) after 4:53 and about 35.5 MB read, with no output manifest or
partial output. It was terminated, and no per-file status was inferred from the
incomplete run. Windows-native PowerShell 7 reruns completed. The helper
`scripts/Decode-BnkMedia.ps1` defaults to the tracked 5-bank sample list and
uses `ProcessStartInfo.ArgumentList` to preserve paths containing spaces.

Actual sample run and full receipts:

| Source bank | DIDX index | Media ID | WEM bytes | WAV output | Audio metadata |
|---|---:|---:|---:|---:|---|
| `System_Common.bnk` | 0 | 1,116,326 | 59,504 | 149,564 bytes | mono, 48 kHz, 74,760 PCM16 frames |
| `Battle_System_Common.bnk` | 0 | 4,765,198 | 73,982 | 184,804 bytes | mono, 48 kHz, 92,380 PCM16 frames |
| `Field.bnk` | 0 | 87,339,219 | 37,406 | 92,488 bytes | mono, 48 kHz, 46,222 PCM16 frames |
| `Waza_ew0738.bnk` | 0 | 73,971,825 | 167,378 | 497,788 bytes | stereo, 48 kHz, 124,436 PCM16 frames |
| `ev0330_masaki.bnk` | 0 | 156,198,044 | 624,263 | 1,861,964 bytes | stereo, 48 kHz, 465,480 PCM16 frames |

All children use
`decoded/1.0.2/romfs/bin/sound/NX64/wwise/bank/<source>.bnk.contents/<mediaID>.wem`
and the sibling `<mediaID>.wav`; bank names and paths are preserved. The
selected five banks contain **369 indexed members**. Across two bounded runs,
**9 members have exact WEM extractions and validated WAV decodes; 360 remain
PENDING; FAILED 0; UNKNOWN 0; UNSUPPORTED 0**. The first run selected five
entries from `Battle_System_Common.bnk`; the round-robin source filter then
added one entry in each of the five banks. For the five table rows, the WEM
SHA-256 values are respectively:

- `cbdc66f1144d6a0d856d3b6e01d3b33ec06cc960e958ab118183050e2da4db0f`
- `9eabec1f8a0b0bb9d0e9c71bfbf12b2ca6b0ec84d62b9dc81b4bfceb4953a55d`
- `0c71a1613bc4e6f9231871f99a65ddbc496d3ed120774aa9424a8113194f39b5`
- `c048c068aa6fffd3f78bd3232ff35f1bcfdc45e7f0137374534804decd519d58`
- `9fcbd7a50fe67f3f7e99ee29245db1b9560b6b706266de5afb2e8f363df237b5`

The decoder is vgmstream r2168 (binary SHA-256
`10fb0691538d3133f0115a071f89775fc99f32210b7e5991cfc3c2869247e4b2`).
`scripts/Verify-Outputs.ps1 -SourcesFile
docs/research/source_lists/t09-bnk-media-smoke5.txt` verified **23/23**
receipt-backed outputs with `bad=0`, no errors, and exit code 0. The 23 rows
are the five BNK/XML pairs plus nine WEM and nine WAV outputs. Targeted
verification now counts only failure-ledger entries belonging to selected
sources, rather than unrelated model failures elsewhere in the project.

At this five-bank sample checkpoint, source-wide totals were **SCANNED 27,824;
DECODED 21,068; FAILED 1; UNKNOWN 6,755; PENDING 0; UNSUPPORTED 0**; BNK-internal
members are tracked separately from the 27,824 top-level RomFS/ExeFS files.
The full 265-bank internal-media pass was still pending then. Use `pwsh.exe -NoProfile -File
scripts/Decode-BnkMedia.ps1 -SourcesFile '' -Limit 20 -Execute` for an initial
all-bank tranche, then set `-Limit 0` for the complete compatible batch. The
command writes per-bank/member JSONL status and exact output receipts; it does
not edit source BNKs.

## Full-bank preflight and 20-member tranche — 2026-10-29

The Windows-native bounded run completed an actual read/hash/parse pass over
all **265** source BNKs. `manifests/bnk_media_banks.jsonl` records **257 banks
with indexed internal media and 8 with no DIDX/DATA**; together, the source
banks contain **1,109** bounded DIDX members. All 265 were version 128, bank
hashes matched the prior `bnk.jsonl` receipts, all DIDX records were 12 bytes,
all slices were in bounds, and no bank parser errors occurred.

The first all-bank tranche selected one member from each of 20 source banks.
Manifest totals after conversion are **23 DECODED or
DECODED_EXISTING_VERIFIED; 1,083 PENDING; 3 UNSUPPORTED; FAILED 0; UNKNOWN 0**.
`scripts/Verify-Outputs.ps1 -SourcesFile
docs/research/source_lists/t09-bnk-media-first20-banks.txt` checked all
**65 registered outputs** for these 20 banks (their BNK/XML outputs plus
internal-media products): 65 verified, `bad=0`, `errors=[]`, `failed=0`,
`unsupported=3`, exit code 0. The 77-test full unit suite passed after adding
the fragment and targeted-verification regressions.

At the 20-member tranche checkpoint, the three unsupported records were not
malformed complete WEM files. Each was
media ID `230260104`, DIDX index 0, 14,106 bytes, in
`BGM_Common.bnk`, `BGM_Event.bnk`, or `FieldFootsteps_Normal.bnk`. The bank XML
for each source reports `StreamType=1 [PrefetchStreaming]`, `sourceID=230260104`,
and `uInMemoryMediaSize=14106`; the corresponding DIDX `MediaHeader` reports
the same ID, offset 0, and size 14,106. Each exact bank slice has SHA-256
`9d31d46a89d447eaaf977a1f586e7d9644c9e7e1e48238990199aee731fa3ee9` and equals
the first 14,106 bytes of
`bin/sound/NX64/wwise/bank/230260104.wem` (388,742 bytes, SHA-256
`b0e136537c2bda562ad7b41ab707ce9133c5e59645249e987fba5fde66ec214d`). The
RIFF header describes the whole 388,742-byte WEM, so a bank slice is not a
standalone decode input. Each is preserved as
`<bank>.bnk.contents/230260104.prefetch.bin`, hash-bound to the BNK, index,
offset, and full external WEM. No `.wem` or `.wav` is emitted for these
fragments. The full loose WEM is already independently decoded in the external
WEM batch.

This tranche confirms the Wwise `PrefetchStreaming` case and exact prefix
relationship. It does not imply other partial RIFF slices are prefetch fragments:
the extractor only marks a fragment as `PREFETCH_FRAGMENT` when the exact
indexed bytes match the prefix of a local complete WEM; other unsupported bytes
remain generic `.unsupported.bin` with raw offsets and hashes. At that tranche
checkpoint, global output receipts were **74,821** and 1,083 members were
pending.

## Complete embedded-media batch — 2026-10-29

The all-member command completed through the Windows-native wrapper:

```powershell
pwsh.exe -NoProfile -File scripts/Decode-BnkMedia.ps1 -SourcesFile '' -Limit 0 -Execute
pwsh.exe -NoProfile -File scripts/Verify-Outputs.ps1 -SourcesFile docs/research/source_lists/t09-bnk-media-all265.txt
pwsh.exe -NoProfile -File scripts/Refresh-Coverage.ps1
```

The final `manifests/bnk_media_banks.jsonl` contains all **265** source banks:
**257 INDEXED, 8 NO_INTERNAL_MEDIA, 0 FAILED, 0 UNSUPPORTED**. Their DIDX tables
contain **1,109** bank/member rows. Final member state is:

| Member state | Count | Result |
|---|---:|---|
| `DECODED` / `DECODED_EXISTING_VERIFIED` | 1,103 | Exact indexed `.wem` bytes and vgmstream WAV |
| `UNSUPPORTED` | 6 | Exact prefetch fragments preserved as `.prefetch.bin` |
| `FAILED` | 0 | No conversion failures |
| `UNKNOWN` | 0 | No unclassified DIDX members |
| `PENDING` | 0 | All compatible entries processed |

The six unsupported records are two media IDs repeated across three banks:

| Media ID | DIDX slice | Complete loose WEM | Prefix SHA-256 | Full WEM SHA-256 |
|---:|---:|---:|---|---|
| `230260104` | 14,106 bytes | 388,742 bytes | `9d31d46a89d447eaaf977a1f586e7d9644c9e7e1e48238990199aee731fa3ee9` | `b0e136537c2bda562ad7b41ab707ce9133c5e59645249e987fba5fde66ec214d` |
| `955527254` | 27,430 bytes | 4,653,928 bytes | `7d1d8eff81470a7e8403456324cbcbb812901ba98d2343cf31dbb67709f90e09` | `287e9c847a23dbcfadaecdacfb0e973eed1773a208c007991f48f301a9d6b867` |

Both fragments have `StreamType=1 [PrefetchStreaming]` and matching
`uInMemoryMediaSize` in pinned wwiser XML for `BGM_Common.bnk`, `BGM_Event.bnk`,
and `FieldFootsteps_Normal.bnk`. Their DIDX offsets/sizes and MediaHeader IDs
match the XML; all six byte sequences exactly match the prefix of the
same-directory loose WEM. The pipeline preserves each under its source bank's
`.bnk.contents` folder and records the external WEM path/hash and prefix-match
result. The complete loose WEMs already have independent WAV outputs.

All **2,477** output receipts associated with these 265 BNK sources (265 XML,
2,206 WEM/WAV, and 6 prefetch binary outputs) passed hash, path, and source
verification: `registered=2477`, `verified=2477`, `bad=0`, `errors=[]`,
`unsupported=6`, exit code 0. The refreshed coverage report records **27,824
SCANNED; 21,068 DECODED; 1 FAILED; 6,755 UNKNOWN; 0 PENDING; 0 UNSUPPORTED**
top-level sources and **76,984 decoded output receipts**. The six internal
prefetch fragments are separate `bnk-media` UNSUPPORTED members; all 1,103
complete internal WEMs are decoded. The 78-test unit suite passes. No original
BNK or other game input was written.

## Static event graph joined to embedded DIDX media — 2026-10-29

The event mapper now reads the actual `manifests/bnk_media.jsonl` receipts and
emits `lgpe-wwise-event-media-v2`. For each reachable `AkMediaInformation`
record it retains `sourceBankId`, then requires the exact pair
`(BankHeader ID, sourceID) == (DIDX bank_id, DIDX media_id)`. An internal output
is attached only when that member's recorded BNK source SHA-256 equals the
SHA-256 computed during the mapper's independent source-bank validation. A
same numeric media ID in another bank does not match. Stale/unverifiable source
receipts, ambiguous DIDX pairs, missing DIDX entries, and prefetch fragments
have distinct states. The mapper never advertises a prefetch fragment's
placeholder WAV path as decoded audio.

Re-running `uv run lgpe map-audio-events` on the actual 265 BNK/XML files and
the 1,109-member internal-media manifest produced:

| Measure | Count |
|---|---:|
| BNK/XML pairs independently source/XML hash-checked | 265 / 265 |
| Internal-media manifest rows / source-hash mismatches | 1,109 / 0 |
| Reachable event media references joined to a same-bank DIDX member | 1,190 |
| Unique bank DIDX members referenced from event graphs | 1,109 / 1,109 |
| Distinct event records reaching a bank DIDX member | 1,161 |
| Joined references with verified internal WAV receipts | 1,170 |
| Joined references to prefetch fragments (`UNSUPPORTED` as standalone WEM) | 20 |

The reference count includes repeated event reachability, so 1,190 references
do not mean 1,190 unique DIDX members. The 20 fragment references map to the
six exact `.prefetch.bin` index records (two IDs repeated across three banks);
the rest link to validated WEM/WAV outputs. Existing external-WEM filename
links remain available separately in each media record. All 265 bank versions
remain v128, no bank parse failed, and the event map retains its existing 2,552
event/action rows and 2,251 distinct event-to-loose-WEM path pairs. The run
reported `bankMediaSourceHashUnverifiedRows=0`.

Eight focused tests now cover same-bank receipt joins, rejection of an equal ID
from a different bank, rejection when the BNK source hash differs, fragment
linking without claiming WAV decode, and the original HIRC/WEM behaviors.
The complete regression suite passes **82/82** tests.
Runtime choice, sequence probability, event names, and audible playback remain
outside this static map.

## LGPE BSEQ sequence structure — 2026-10-29

The exact local RomFS scan contains **381** `.bseq` files in two source trees:
353 under `bin/battle/waza/sequence/` and 28 under `bin/demo/sequence/`.
Every input passed an actual byte check for `SESD` magic and little-endian
version 3. The file count is from the real scan; the uploaded tree is not used
to infer parser fields.

After adding the observed `SESD` signature to the generic scanner, the targeted
`scripts/research/refresh_bseq_scan_signatures.py` pass refreshed all 381
`.bseq` rows in `manifests/files.csv` from their real 64-byte headers. Every row
now reports `SESD`, exact header bytes, and unchanged source size; the other
27,443 scan rows and their existing hashes were retained. The audit script
checks these catalog headers against the actual source bytes.

The parser is the public [pbseqtool source](https://github.com/lincoln-lm/pbseqtool),
checked out under ignored `tools/src/pbseqtool` at exact commit
`6f122d1b7945797cae472960b798bf28523f8acd`. Its LGPE command dictionary
SHA-256 is `b226d3fbfbf6bce22256f82e3a38a933faa48bb1bea5b73b13b493896b5746be`.
The upstream README says the tool supports LGPE but does not support sequences
that may be used for demos/cutscenes. It also explicitly permits use as a base;
the checkout has no formal `LICENSE` file. The adapter therefore imports the
ignored checkout in place, records that license status, and does not copy or
redistribute upstream source. Names and parameter values are parser-reference
fields; command behavior and gameplay semantics remain unverified.

The new `uv run lgpe decode-sequences` command writes one-to-one
`<source>.json` outputs at the mirrored relative path. Each JSON records tool
commit, command-dictionary hash, source size/hash, the complete original bytes
as `raw_hex`, parsed groups/commands, and two separate round-trip checks. The
batch serializes and reparses the sequence, requiring the structured JSON to
match. It reports whether the serializer also reproduced every input byte.
The exact input remains embedded when pbseqtool normalizes binary encoding.

Five actual samples covered small `ee`-stem and larger `ew`-stem files; no
sequence-name or command semantics are assigned from those stems:

| Source | Bytes | Source SHA-256 | Groups / commands | Binary round trip |
|---|---:|---|---:|---|
| `bin/battle/waza/sequence/ee000.bseq` | 124 | `1b38facf44af506167a588da86c5a6926704336178669248e022e250366cc88f` | 1 / 5 | Exact |
| `bin/battle/waza/sequence/ee080.bseq` | 36 | `e1a7f326b2638a305b3436c83debb87e321423ede46158fabd0690e9751fe1a8` | 1 / 1 | Exact |
| `bin/battle/waza/sequence/ew001.bseq` | 988 | `2f8bf2764e79374ea76f3b6aeb92f0f2ad29ef5afa2a623a6fa32be75183d414` | 2 / 18 | Normalized; same output size |
| `bin/battle/waza/sequence/ew063.bseq` | 5,420 | `30c342822c38cc0f5279587b8e2fe1f7d968eff9974c4af954174d0ab1e80419` | 9 / 87 | Normalized; same output size |
| `bin/battle/waza/sequence/ew085.bseq` | 3,912 | `1260f05a463a03d55fd12b2648b0e34a84a1b691ab4ffc7428590a0226707435` | 10 / 56 | Normalized; same output size |

The 5-source smoke batch and the sorted first-20 batch both completed with
zero failures; their targeted verifications passed 5/5 and 20/20. The full
381-source run produced **353 decoded JSONs** and initially exposed 28 parser
exceptions in the demo tree. The pinned README excludes demo/cutscene
sequences, so those 28 are now explicitly `UNSUPPORTED`; their exact parser
exceptions are preserved in `manifests/bseq.jsonl` and
`manifests/failures.jsonl`, and no JSON output is created for them. The error
set is 14 `NameError: name 'i' is not defined`, 8 `KeyError: '6D6F'`, 2 each
`KeyError: '7461'` and `KeyError: '6465'`, plus one each `KeyError: '2F72'`
and `KeyError: 'EB03'`. This describes upstream parser coverage/errors; it does
not claim those files are malformed.

The independent audit in `scripts/research/check_bseq_outputs.py` checked all
381 source paths against the tracked list, re-read every source to verify the
SESD/version gate and source hash, confirmed all 353 mirrored JSON hashes and
embedded `raw_hex` values, and checked every semantic serialize/reparse result.
Results: **353 decoded; 28 unsupported; 0 failed; 52 byte-exact round trips;
301 normalized byte round trips; 353/353 semantic round trips**. The output
manifest verifier checked **353 registered / 353 verified / 0 bad**, with
28 unsupported entries kept separate. At audit time decoded JSON totaled
8,640,781 bytes for 1,146,388 bytes of decoded sources; raw source hex accounts
for the expansion.

Reproduction on WSL uses the repository's external Linux venv because the
mapped X: project drive does not permit Python venv symlinks:

```bash
UV_PROJECT_ENVIRONMENT=/tmp/lgpe-research-wsl-venv uv sync
UV_PROJECT_ENVIRONMENT=/tmp/lgpe-research-wsl-venv uv run python scripts/research/refresh_bseq_scan_signatures.py --root ..
UV_PROJECT_ENVIRONMENT=/tmp/lgpe-research-wsl-venv uv run lgpe decode-sequences --root .. --limit 0 --sources-file docs/research/source_lists/t09-bseq-smoke5.txt --execute
UV_PROJECT_ENVIRONMENT=/tmp/lgpe-research-wsl-venv uv run lgpe decode-sequences --root .. --limit 0 --sources-file docs/research/source_lists/t09-bseq-381.txt --execute
UV_PROJECT_ENVIRONMENT=/tmp/lgpe-research-wsl-venv uv run lgpe verify --root .. --sources-file docs/research/source_lists/t09-bseq-381.txt
UV_PROJECT_ENVIRONMENT=/tmp/lgpe-research-wsl-venv uv run python scripts/research/check_bseq_outputs.py --root ..
```

The same commands work in PowerShell 7 after `uv sync`, using `--root ..` from
the project directory. Tracked lists are `t09-bseq-smoke5.txt`,
`t09-bseq-first20.txt`, `t09-bseq-unsupported28.txt`, and `t09-bseq-381.txt`.
Audio event ownership, sequence-to-Wwise playback links, sequence probability,
and in-game timing remain open.

## BSEQ parser-literal to Wwise event-ID cross-reference — 2026-10-30

Added `uv run lgpe map-sequence-audio` and the native PowerShell wrapper
`scripts/Map-Sequence-Audio.ps1`. The adapter joins the outputs from the local
BSEQ and BNK workflows without assigning gameplay meaning to the upstream
command dictionary. It verifies every BSEQ source SHA-256 and supported JSON
output SHA-256, checks the embedded `raw_hex` against the current source bytes,
then rehashes the actual BNK sources and mirrored wwiser XML outputs before
using the existing static event map. Each event-map row is checked against the
same current BNK and XML hashes. The code changes no source files or decoder
coverage.

The event hash is reproduced from pinned
`tools/src/wwiser/wwiser/wfnv.py` at commit
`08e937b649bc7007c234bbd59e34a41d5eef3b38`: lowercase UTF-8 bytes, FNV-1
32-bit, with the Wwise offset basis and prime. The corresponding description
is in that commit's `doc/WWISER.md` under “Wwise files and names”. This is
FNV-1, not FNV-1a. Unit tests distinguish the hash behavior and exercise exact
literal extraction and all match-status classes.

The successful native run verified **265/265 BNK/XML pairs**, **381/381 BSEQ
source rows**, **353/353 supported BSEQ JSON/raw-byte pairs**, and **2,552**
Wwise event/action rows. It wrote **949** parser-field occurrences to ignored
`manifests/bseq_wwise_events.jsonl` (4,645,758 bytes; SHA-256
`1d12a2fbe58b49cdb11dd6122161ee49134d4528a40950c98713103775b0098e`). All
**268/268** parser-field `BelugaSoundLoadBank` literals equal an exact local
BNK filename stem, spanning 233 distinct strings. The 949
`BelugaSoundPlaySe` parser-field occurrences contain 658 distinct event
strings and 658 distinct FNV-1 IDs:

| Static result | Occurrences |
|---|---:|
| One event-ID candidate in a BNK whose exact stem is referenced by the sequence | 768 |
| Event-ID candidates exist only in other local banks, outside that sequence's exact bank-name references | 181 |
| No Wwise event-ID candidate | 0 |

The 181 outside-bank occurrences comprise **172** sequences with no
`BelugaSoundLoadBank` parser field and **9** with an exact local bank-name
match whose bank lacks that event ID. They have **214** candidate-bank
incidences across the current static index: `Battle_System_Common.bnk` has
173 incidences spanning 33 event IDs and 70 sequence sources;
`System_Common.bnk` has 37 incidences spanning two IDs and 24 sequence
sources; the two `PokemonVoice_Aibou*` banks contribute two incidences each.
Thirty-three of the 181 occurrences have more than one global bank candidate.
These counts describe where matching IDs occur in the parsed BNK set; they do
not show that any of those banks is loaded by a sequence at runtime.

“Sequence bank reference” means only that the pinned BSEQ parser produced a
`BelugaSoundLoadBank` command with a string exactly equal to a local BNK stem.
It is not a claim that the game loads that bank. Likewise, the
`BelugaSoundPlaySe` name and `event` parameter are parser dictionary fields,
not verified runtime instructions. The result is a static string/ID join;
event invocation, command behavior, bank-loading order, runtime selection,
probability, and playback are unverified. All event display names remain
unknown because `wwnames.db3` is absent. Candidate records preserve the Wwise
event index, bank/source/XML hashes, parser-field indexes, and available static
media/WAV receipts.

Concrete row check: `bin/battle/waza/sequence/ew063.bseq` (source SHA-256
`30c342822c38cc0f5279587b8e2fe1f7d968eff9974c4af954174d0ab1e80419`) contains
the parser-field literal `Waza_ew0063` at group 0, command 7; that exact string
equals the stem of `bin/sound/NX64/wwise/bank/Waza_ew0063.bnk` (source SHA-256
`b97f127835cfea1f33735f429055fd3b4547ffd83c9c84648f892a623be10674`; XML
SHA-256 `c08ebbf8804939d8445e8f8583fa9a4112e3f53339ef466a3aba290a6fd3a796`).
The adjacent parser-field literal `Play_SE_w0132` at group 0, command 8 hashes
to decimal `532430182` (`0x1fbc3d66`) with the pinned FNV-1 method. The local
static Wwise event map has that ID at event index 13 in the exact bank; its
display name is null/unknown. The same event record links statically to bank
media ID `1042267675`, with an existing internal WEM/WAV receipt under
`Waza_ew0063.bnk.contents/`; this is not proof that the BSEQ command caused
that audio to play.

The first WSL attempt entered kernel I/O wait at `Path.resolve()` on the
mapped X: (9P) filesystem and was interrupted before writing the output. The
path check was changed to a lexical comparison after rejecting traversal and
non-`decoded/` manifest paths. The native PowerShell wrapper then completed
the same run successfully in 17.3 seconds. Reproduce from the project root:

```powershell
pwsh -NoProfile -File scripts/Map-Sequence-Audio.ps1
```

```bash
UV_PROJECT_ENVIRONMENT=/tmp/lgpe-research-wsl-venv uv run lgpe map-sequence-audio --root ..
```

The output summary is `manifests/bseq_wwise_events.summary.json`; it records
input counts, status counts, manifest byte length and SHA-256. The output map
is ignored local research data, not committed game content.

## Exhaustive run orchestration — 2026-10-30

For `lgpe run --limit 0 --execute`, the pipeline adds four ordered T09
post-processing stages after the external-WEM and BSEQ batches: (1) index and
extract internal BNK media with `run_bnk_media_batch`, (2) rebuild the static
Wwise event/action/media map, (3) build the supported-BSEQ-to-Wwise event-ID
map, and (4) map bounded raw audio literals in unsupported demo BSEQ files to
local HIRC type-4 objects. Each stage receives its own run-journal checkpoint.
The top-level failure summary counts internal media member/bank failures and
incomplete supported-sequence mapping rows. These stages are deliberately
skipped for bounded runs, which do not have complete BSEQ or BNK coverage.

The full-run integration test verifies the stage order, checkpoints, and
summary fields. After adding the fourth stage, the native Windows test suite
passed **163 tests, with one expected symlink-creation skip**. The demo-audio
stage was independently run over its 28 actual unsupported sources and its
native dry-run produced the same report hash. The exhaustive 78,104-receipt
replay predates the fourth stage; this new integration test exercises the
orchestration, but the exhaustive command has not been repeated since that
addition.

## Loose WEMs without event-graph references — 2026-10-30

The Wwise event mapper now emits `manifests/wwise_unreferenced_wem.jsonl`.
After parsing and hash-checking the successful BNK/XML set, it compares each
loose WEM absent from event-reachable media against every parsed HIRC object's
`sourceID`. It then independently rehashes that WEM and its WAV output receipt.
The scope is explicit: all **265/265** successful local v128 banks were parsed,
with zero bank failures. This is a sourceID census of that set, not proof that
the executable never accesses a WEM by another path.

All **7/7** loose WEMs without event-graph references also have no matching
HIRC `sourceID` in those banks (`NO_LOCAL_HIRC_SOURCEID_MATCH`); all seven
source and WAV SHA-256 receipts were checked. They are not missing decodes:

| WEM ID | Source bytes | Source SHA-256 | WAV SHA-256 |
|---:|---:|---|---|
| 179568488 | 57,980 | `86d8ea7263fba434baa9841b51579eccaea335c41afe9c3070d33e5cfa6ee876` | `372bfe1d8329534a3d20927f22159264ec8a45f47f91e7b9bc3bf21be68631ba` |
| 362856945 | 103,700 | `9c8f86afadfcf28a1bbda8d3b23adffce2abba8c9ff7c5947df779b3c50befed` | `17442788e2ad5cd6b13689dd3a8328cd76deed9385c05bd8681e34e1c1712b5e` |
| 453049171 | 57,218 | `e58df0695316f9a5113e17ff085e3eb85acda17d9180220616e8cc0d7e4333b1` | `8f56ace776c5a97748f79410c74bd11dc8ba55b198340555b366d11d9e54613e` |
| 518366114 | 79,316 | `96f14cbaefede1fbbeb058fb4eeed0a357a9f229f22c621d45fa544b3ab794db` | `4ac9b71258db0a5bba132dc4d324ecfbec0207c0dcce96d989a308a2fe5002a1` |
| 687848159 | 21,404 | `3849ab5167a0db4d06d2b7688826b1438c4f3ef2e3da4e09edebbc930c135bd1` | `711cf905eb669e79f6016bf41f847c8ba08ae9aac9df19607d17333b55567a6d` |
| 733490508 | 38,168 | `78db598f5202bfc065c9fd1dac251b3b1dff386316b18419298d749e9b20f4ae` | `1ab3a40398d384fda94eb23e98a27e6eed2f20a76a86681e6105ea9eb16daf8b` |
| 805116817 | 75,506 | `a101e64aa725bf516ac1849069f2f294906c46a6c77fb63ad47b0a19e7d90176` | `fafad2e4473781fcd2f0d8846ca47484cee45569c049ccf337bf724952d9fb8f` |

The first Windows-native pass surfaced a missing `Counter` import after writing
the validated output files and exited with `NameError`; after adding the
import, the same wrapper completed successfully. Final summary: **265 banks
parsed, 0 failed, 7 loose WEMs without event reachability, 0 HIRC sourceID
matches**, with all existing WEM/WAV hashes valid. The seven-row sidecar is
6,728 bytes with SHA-256
`ffc4b6a704e8c580014520ab502c2733a03b9292a8a3b08cf92073fd60a2ace7`. Repeat with
`pwsh -NoProfile -File scripts/Map-Audio-Events.ps1` or
`uv run lgpe map-audio-events` on a fast local filesystem. The existing full
run invokes this mapper after BNK media extraction, so the sidecar is refreshed
as part of exhaustive processing.

## Integrated exhaustive replay — 2026-10-29

The native Windows-uv command
`uv.exe run lgpe run --root "X:\ROMS\Nintendo Switch\Pokemon\Pokemon Lets Go Pikachu" --limit 0 --timeout 600 --execute`
completed at `2026-10-29T18:15:13Z` with exit code 0 as journal run ID
`3854a69f321f49ea9eaeff9e2a80633f`. It completed the inventory, archive,
learnset, game-data, BNK, texture, model, animation,
particle, collision, audio, AMX, BSEQ, and Wwise-map checkpoints. Final
source-output verification checked **78,104/78,104 receipts**, with `bad=0`
and no errors. The refreshed coverage is **27,824 SCANNED; 21,456 DECODED; 0
FAILED; 6,340 UNKNOWN; 0 PENDING; 28 UNSUPPORTED; 78,104 decoded outputs**.
This section records the verified T09 stages from that full-corpus replay.

The BNK-media checkpoint read all **265/265** v128 banks, indexed **1,109**
internal members, decoded and reverified **1,103**, and retained **6** exact
prefetch fragments as `UNSUPPORTED`; failed 0, pending 0, unknown 0. All
265/265 bank source/XML pairs were rehashed. The regenerated event-media map
has **2,552** event/action rows, **2,251** event-to-loose-WEM pairs, **1,190**
event-to-DIDX references across 1,109 unique members, **1,170** verified
internal WAV references, and **20** references to the six prefetch fragments.
There were no bank parse failures or source-hash-unverified media rows.

The regenerated BSEQ-to-Wwise map reverified all **353/353** supported BSEQ
JSON outputs against the current 1.0.2 source bytes, while retaining the 28
known unsupported demo/cutscene inputs. It contains **949** `PlaySe` parser
field rows and **268** exact `LoadBank` name-reference occurrences. Of those
949 rows, **768** have an event-ID candidate in a bank whose stem is present
in that same sequence, while **181** have candidates only in other banks.
This remains a static parser-field/FNV-ID join, not runtime behavior. All 265
local banks are v128 and parsed; all seven loose WEMs without event-graph
reachability still have zero local HIRC `sourceID` matches.

The current regenerated ignored manifests were byte-counted and SHA-256 checked
after the journal checkpoints:

| Manifest | Rows | Bytes | SHA-256 |
|---|---:|---:|---|
| `bnk_media.jsonl` | 1,109 | 1,798,116 | `ab208adee1e41bb10cbc83708b12c11f31759f55d0e0c18a7b7cb23c5276d6e6` |
| `wwise_event_media.jsonl` | 2,552 | 8,887,397 | `9a94c7fcb15b6ea31a1bd02ed18568486dfa0b605f9dc738a690a58ed332767e` |
| `bseq_wwise_events.jsonl` | 949 | 4,645,758 | `180085cd6fd4c3f0e42d57e0996ffde54595f7573a93ab710ff69695e5671df5` |
| `wwise_unreferenced_wem.jsonl` | 7 | 6,854 | `087d673a01d89d9285b25031d9870e7cfb9d2bad9b96275e6034178dbbcc9ad4` |

The `wwnames.db3` name database is still absent, so event display names remain
unknown. Sample registration covered **302** receipts (290 archive-member, 5
asset, 7 game-data); its 34 failed-or-unsupported sample statuses correspond
to the six prefetch fragments and 28 BSEQ demo/cutscene files. The final native
Windows-uv test run passed **140/140 tests**, with one skip because symlink
creation is unavailable on this host.

### Repeated native Windows full replay — 2026-10-30

`scripts/Start-Research.ps1 -Limit 0 -Timeout 600 -Execute` completed against
the actual extracted 1.0.2 source root as run ID
`bd3965f5d2a84bed9a87d6037be75d1f` at `2026-10-30T14:31:44+08:00`, exit 0.
The appended run journal records each domain checkpoint, final verification,
coverage, and completion. It scanned 27,824 paths, matched 27,819 snapshot
paths, identified the same five extensionless ExeFS additions, and reported no
scan access anomalies. It completed 1,017 archives / 59,121 members, 10,020
game-data outputs, 265 BNKs, 1,134 WEMs, 1,103 internal BNK media members, 353
supported BSEQs (28 remain explicitly UNSUPPORTED), and the texture/model/
animation/particle/collision/AMX stages listed in `STATUS.md`.

The end-of-run verifier rehashed **78,104/78,104** registered outputs with
`bad=0`, `errors=[]`; refreshed coverage is **SCANNED 27,824; DECODED 21,456;
FAILED 0; UNKNOWN 6,340; PENDING 0; UNSUPPORTED 28; 78,104 outputs**. The
1,103 decoded internal BNK media members and six unsupported prefetch fragments
remain represented separately from top-level RomFS source coverage. The
Windows-native regression suite ran **163 tests in 16.912s**, with 162 passed
and one expected symlink-permission skip. This repeat confirms the existing
counts and receipt hashes; it makes no claim about runtime playback or event
semantics.

### RomFS MS ADPCM WAVE batch — 2026-10-30

The actual 1.0.2 RomFS scan contains **318 `.wav` sources**. The new bounded
RIFF/WAVE inspector confirmed all 318 have format tag 2 (Microsoft ADPCM),
16,000 Hz, 4 bits/sample, and a valid nonzero `fact` frame count. It bounds
every chunk by the declared RIFF size and checks the ADPCM extension and
coefficient table before dispatching to vgmstream. Native PCM WAVE inputs are
recorded as `UNKNOWN` with an explicit already-PCM reason; no conversion is
claimed for them.

`run_wave_batch` now exports each converted file to the identical relative
path under `decoded/1.0.2/romfs/`, preserving the basename and `.wav`
extension while replacing the ADPCM stream with PCM16 data. Every output is
checked for PCM16 integrity, matching source channels and sample rate, and a
frame count equal to the source `fact` count. Each `waves.jsonl` row and output
receipt stores source/output hashes, validation fields, the vgmstream command,
release, and executable SHA-256. Output receipts are verified by the normal
source-list verifier; `waves.jsonl` also participates in source-wide coverage.

The staged native Windows-uv runs were:

| Command limit | Selected | DECODED | FAILED | PENDING | UNKNOWN |
|---:|---:|---:|---:|---:|---:|
| 5 | 5 | 5 | 0 | 313 | 0 |
| 20 | 20 | 20 | 0 | 298 | 0 |
| 0 (all) | 318 | 318 | 0 | 0 | 0 |

The all-source manifest contains **298 `DECODED` and 20
`DECODED_EXISTING_VERIFIED`** rows. Those 20 target files existed without
receipts before this batch. The first run correctly recorded five of them as
conflicts rather than overwriting them. The adapter was then tightened to
decode into a temporary file and adopt an unreceipted target only if the fresh
decode is byte-identical. All 20 passed that check; none was overwritten.
There are no remaining `wave` failure rows. The initial WSL invocation stalled
at mapped-drive `Path.resolve()` before processing a source, so the actual runs
used Windows-native uv and Python 3.12.13.

An independent audit rehashed all 318 sources against their manifest values,
validated all 318 outputs again as nonempty PCM16, and compared source channel,
sample-rate, and `fact` frame fields with each export. It found **0 source,
path, or PCM metadata mismatches**. Total PCM output size is **8,994,864
bytes**. Targeted `lgpe verify --root .. --sources-file
docs/research/source_lists/wave-sources.txt` verified **318/318 receipts**,
`bad=0`, with 0 selected failures or unsupported rows. The committed source
list contains the exact 318 RomFS-relative paths.

Representative exact hashes and independently validated output properties:

| Source | Source SHA-256 | PCM output SHA-256 | PCM properties |
|---|---|---|---|
| `bin/app/palma/verup/se_bl_hokaku_sys_040_masterball_adpcm.wav` | `19eb018d3a8e5aecce11b47990499d1e27fb2e51efc94a2f5a7a0358dce0e782` | `1a7629b5375e03a8e6c916f6f2ff3f741e6aee24a5b29a07f70a73a2220f2194` | mono, 16 kHz, 22,212 frames, 44,424 PCM bytes |
| `bin/app/palma/verup/se_bl_hokaku_sys_047_masterball_adpcm.wav` | `9396d54dc201fd0c45dac7ef3b3bec2890286f05cfd9dea2c80c5ef10d02f64e` | `27637ba0885ede7d6829d163b6794aa26fe0f476c0e5a7a99d73ca7f5b665cd9` | stereo, 16 kHz, 46,875 frames, 187,500 PCM bytes |
| `bin/app/palma/wave/pv0001_Common_adpcm.wav` | `b934cb33bd16f5793bc4834c8e97fc6133f0f738784200e73fb9af4400e3b62d` | `8c3367d86e1b9116f345ef251fff737fc5b63014c2a1ccabdfb4f87581c5c4ae` | mono, 16 kHz, 15,333 frames, 30,666 PCM bytes |

Reproduce from PowerShell 7 with the pinned local vgmstream r2168 adapter (the
source commit and license notices are recorded above):

```powershell
Set-Location 'X:\ROMS\Nintendo Switch\Pokemon\Pokemon Lets Go Pikachu\LGPE-Research'
$env:UV_PROJECT_ENVIRONMENT = 'D:\SDK\uv-envs\lgpe-research'
$uv = 'D:\SDK\uv-x86_64-pc-windows-msvc\uv.exe'
& $uv run --python 3.12.13 lgpe decode-wave --root .. --limit 5 --execute
& $uv run --python 3.12.13 lgpe decode-wave --root .. --limit 20 --execute
& $uv run --python 3.12.13 lgpe decode-wave --root .. --limit 0 --execute
& $uv run --python 3.12.13 lgpe verify --root .. --sources-file docs/research/source_lists/wave-sources.txt
& $uv run --python 3.12.13 lgpe coverage
```

The refreshed source-wide coverage is **SCANNED 27,824; DECODED 21,839;
FAILED 0; UNKNOWN 5,957; PENDING 0; UNSUPPORTED 28; 78,498 registered
outputs**. The T09 task remains `IN_PROGRESS` for event names and unresolved
bank/sequence/runtime behavior; this WAVE conversion does not address those
semantics.

Regression checks for this addition passed **14/14 focused wave, coverage, and
pipeline tests**. The full native Windows CPython 3.12.13 suite passed **193
tests, 1 expected symlink-permission skip, and 72 subtests** in 18.14 seconds.
The first WSL full-suite attempt had one unrelated Git `dubious ownership`
failure while reading the pinned pkNX checkout; the native Windows rerun
completed that same test successfully.

### Demo/cutscene BSEQ parser error-chain audit — 2026-10-30

The original `UNSUPPORTED` rows recorded only the outer exception string.
Reproducing `bin/demo/sequence/ev0050_get.bseq` showed that pinned
`pbseqtool` commit `6f122d1b7945797cae472960b798bf28523f8acd` catches a
`UnicodeDecodeError` while decoding a `String` parameter, then its own error
formatter raises `NameError: name 'i' is not defined` and hides the original
cause. A second sample, `ev0800_ghost.bseq`, reaches `Cmd.from_bytes`'s
`ref.lookup_params(cmd_id)` and raises `KeyError: '7461'` because that lookup
key is absent from the pinned LGPE command dictionary. These stack frames are
at `pbseqtool/sesd.py:476/939` and `sesd.py:467` → `cmdReference.py:161`.

The project adapter now renders the exception chain without modifying the
pinned upstream source. New regression tests cover hidden causes and cyclic
exception contexts. Reprocessing the bounded list
`docs/research/source_lists/t09-bseq-unsupported28.txt` selected **28/28**
files and produced **0 JSON outputs**, leaving all rows `UNSUPPORTED` and
`FAILED=0`. The detailed cause distribution is **14 UnicodeDecodeError** and
**14 KeyError**. The 14 KeyErrors contain lookup keys `7461` (2), `6465` (2),
`6D6F` (8), `2F72` (1), and `EB03` (1); these are recorded as raw lookup keys,
without assigning command meaning. All **28/28** source hashes still match
their manifest rows, and all 28 expected JSON targets remain absent.

Reproduce on Windows with:

```powershell
uv run lgpe decode-sequences --root .. --limit 0 --execute --sources-file docs/research/source_lists/t09-bseq-unsupported28.txt
uv run lgpe coverage
```

The updated ignored `manifests/bseq.jsonl` has **381** rows: 353
`DECODED_EXISTING_VERIFIED`, 28 `UNSUPPORTED`, 0 failed. Its SHA-256 is
`47f5dd63335fe4f4421438ef4822124a45f64848475b811fb97eb0b350269de8`.
Focused BSEQ decoder tests pass **5/5**; the complete native Windows CPython
3.12.13 suite passes **205 tests with one expected symlink-permission skip**.
Source-wide coverage is unchanged: **SCANNED 27,824; DECODED 21,839; FAILED
0; UNKNOWN 5,957; PENDING 0; UNSUPPORTED 28; 78,498 registered outputs**.
The demo/cutscene command set and playback behavior remain unsupported.


### Demo/cutscene BSEQ parser-cursor diagnostics — 2026-10-30

The adapter now records the pinned parser frame's byte cursor, 16-byte raw
command header, parsed option words, parameter name/type/declared length, and
SHA-256 of raw argument bytes when `pbseqtool` raises. Nearby printable ASCII
runs are retained only as byte evidence; they are not treated as decoded
strings or command semantics. The diagnostic follows `__cause__` and
unsuppressed `__context__` with cycle protection, and preserves the current
`UNSUPPORTED` status for the demo/cutscene tree. Source read/hash errors occur
outside that parser-error classification.

A second actual native-Windows run of
`docs/research/source_lists/t09-bseq-unsupported28.txt` selected **28**
`bin/demo/sequence/*.bseq` sources. Independent validation found **28/28**
manifest source hashes equal the bytes in the local 1.0.2 RomFS, **28/28**
expected JSON targets absent, and diagnostics present for **28/28**. Cause
counts remain **14 UnicodeDecodeError / 14 KeyError**. The UTF-8 failures are
at command IDs `2D00` (6) and `2E00` (8), each associated in the pinned
parser dictionary with `camFile`, type `String`, declared length 256; the
parameter byte hashes and parser offsets are retained per row. The KeyError
lookup keys remain uninterpreted raw IDs: `7461` (2), `6465` (2), `6D6F` (8),
`2F72` (1), and `EB03` (1). No format correction or command-name inference
was attempted.

The generated, locally ignored `manifests/bseq.jsonl` has **381** rows: **353
DECODED_EXISTING_VERIFIED, 28 UNSUPPORTED, 0 FAILED**. Its SHA-256 after the
rerun is
`66cb2cdbd35d678672d37b3501e28223576b7ea719cbaff62e27ab0b67df4d9c`. The
focused BSEQ suite passes **7/7**. The full native Windows CPython 3.12.13
suite ran **207 tests with one expected symlink-permission skip**. A fresh
`lgpe coverage` reports **SCANNED 27,824; DECODED 21,839; FAILED 0; UNKNOWN
5,957; PENDING 0; UNSUPPORTED 28; 78,498 registered outputs**. These BSEQ
diagnostics do not change source-wide coverage.

Reproduce with native Windows uv / PowerShell 7:

```powershell
$env:UV_PROJECT_ENVIRONMENT = 'D:\SDK\uv-envs\lgpe-research'
uv run --python 3.12.13 lgpe decode-sequences --root .. --limit 0 --execute --sources-file docs/research/source_lists/t09-bseq-unsupported28.txt
uv run --python 3.12.13 lgpe coverage
uv run --python 3.12.13 python -m unittest discover -s tests -v
```

### Sequence-derived Wwise event label candidates — 2026-10-31

A native Windows PowerShell rerun of `scripts/Map-Sequence-Audio.ps1` rehashed
the **265/265** local BNK/XML pairs and **353/353** supported BSEQ source/JSON
pairs before rebuilding the BSEQ-to-Wwise map. The pipeline now writes a
separate `manifests/wwise_sequence_event_label_candidates.jsonl` sidecar from
the just-verified map rows. It does not change `wwise_event_media.jsonl` or
assign the Wwise `eventName` field.

The sidecar contains **735** unique bank/event rows and **1,612** exact
sequence-literal-to-bank-event candidate links, covering **658** distinct
parser literals and event-ID values. Of those links, **768** point to a bank
whose stem appears in that sequence's parsed `BelugaSoundLoadBank` fields;
**844** point only outside those parser-referenced bank sources. This link
count has a different unit from the existing 949 parser rows (768 rows have a
candidate in a referenced bank; 181 rows have candidates only outside those
banks). All candidate pairs have one literal label, with **0** multi-literal
conflicts and **0** supported parser rows without an event-ID candidate.

Each candidate record retains the BNK source/XML paths and hashes, bank and
event IDs, event index, parser literal, pinned `pbseqtool` and `wwiser` commits,
command-dictionary hash, sequence source/output hashes, command index and
frame fields, and whether the bank source was named in that same sequence.
Every one of the **735/735** original Wwise `eventName` values remains `null`
with `UNKNOWN_WWNAMES_DB_ABSENT`; the report marks `eventNameWasUpdated` false.
The candidate labels therefore do not establish command semantics, runtime
bank loading, event invocation, selection, timing, or playback.

The input map has **949** rows, 4,645,758 bytes, SHA-256
`180085cd6fd4c3f0e42d57e0996ffde54595f7573a93ab710ff69695e5671df5`. The
candidate sidecar has **735** rows, 2,213,559 bytes, SHA-256
`8fd4ecc330b0fdadac8213b71560514ab2cccfd4b1eae97906ff05dc3abe03ea`; its
summary JSON is 1,421 bytes with SHA-256
`37781432ba020207218812f1c8338ac6735ee439fa286fafa15e42449bc54cd0`. Both reports use explicit UTF-8/LF writes for stable cross-platform output bytes.

Coverage remains **SCANNED 27,824; DECODED 21,839; FAILED 0; UNKNOWN 5,957;
PENDING 0; UNSUPPORTED 28; 78,498 outputs**. The BSEQ subset remains **381
SCANNED; 353 DECODED; 0 FAILED; 28 UNSUPPORTED**. No source or decoded output
status changed.

Reproduce with PowerShell 7 on the native Windows path:

```powershell
Set-Location 'X:\ROMS\Nintendo Switch\Pokemon\Pokemon Lets Go Pikachu\LGPE-Research'
$env:UV_PROJECT_ENVIRONMENT = 'D:\SDK\uv-envs\lgpe-research'
pwsh -NoProfile -File scripts/Map-Sequence-Audio.ps1
pwsh -NoProfile -File scripts/Refresh-Coverage.ps1
$env:PATH = 'D:\Tool\Git\cmd;' + $env:PATH
$env:PATHEXT = '.COM;.EXE;.BAT;.CMD;' + $env:PATHEXT
pwsh -NoProfile -File scripts/Test-Project.ps1
```

The equivalent WSL command using
`UV_PROJECT_ENVIRONMENT=/tmp/lgpe-research-resume-venv uv run lgpe
map-sequence-audio --root ..` stalled in `p9_client_rpc` on `/mnt/x` for 2:24;
the sidecar and input map timestamps did not change. That run was terminated
with exit 143 and is not counted as a result. The native Windows mapping run
completed with exit 0. The first native full-suite attempt lacked the local
Git path/PATHEXT and failed the existing pinned-checkout test; with the
process-local settings above, the full suite passed **237 tests, 236 passed,
1 expected symlink-permission skip**. The four focused candidate-label tests
also passed under the WSL temp uv environment.

### Unreferenced loose WEM ID cross-check — 2026-10-31

`uv run lgpe map-sequence-audio --root ..` now builds the ignored report
`manifests/wwise_unreferenced_wem_id_audit.json` after the existing sequence
map. The audit reads the actual 1.0.2 files, validates the source/output
receipts, and records each input-manifest hash. It parsed and hash-checked
**265/265 BNK sources**, matched every parsed DIDX entry against the indexed
media manifest (**1,109/1,109** rows; 257 banks with indexed media and 8 with
no internal media), and revalidated the **7/7** loose WEM and WAV receipts.
The earlier all-bank HIRC search is retained as a hash-linked input: all seven
rows report **0/265 HIRC `sourceID` matches** and zero bank failures.

The report also rehashed all **381/381** BSEQ source files and searched their
**1,411,352** raw bytes for each target ID as u32/u64 little- and big-endian,
decimal ASCII, 8-digit hexadecimal ASCII in both cases, and `0x`/`0X`-prefixed
hexadecimal ASCII in both cases. No target ID occurred in any of those 11
representations. All seven IDs therefore have **0 HIRC matches, 0 DIDX
matches, and 0 BSEQ byte occurrences** in the checked local corpus:
179568488, 362856945, 453049171, 518366114, 687848159, 733490508, and
805116817. Per-file BSEQ hashes, per-bank BNK/XML hashes, and the seven WEM/WAV
hash pairs are in the report.

The report is **219,059 bytes**, SHA-256
`6c09824e2227bd490a572002a03be5da02ca46fed703e044f8e2168b527b3a6f`. Its
source manifest hashes are: `bnk.jsonl`
`a06871b63b864cd5d64bbe199047cc31632680f1b7406c82401291bc8c476e12`,
`bnk_media_banks.jsonl`
`efc5ea51c5ab03ed5b54335693d6633841ee6bf2bda453c9051de211310ecaf8`,
`bnk_media.jsonl`
`ab208adee1e41bb10cbc83708b12c11f31759f55d0e0c18a7b7cb23c5276d6e6`,
`audio.jsonl`
`2758c72e6628623e2ebe655e31e09c7243fd9c36ee65a0956abf258b68693e99`,
`wwise_unreferenced_wem.jsonl`
`087d673a01d89d9285b25031d9870e7cfb9d2bad9b96275e6034178dbbcc9ad4`, and
`bseq.jsonl`
`66cb2cdbd35d678672d37b3501e28223576b7ea719cbaff62e27ab0b67df4d9c`.

The report is identifier-only evidence. It does not exclude other encodings,
indirect or dynamically generated IDs, or runtime loading paths, and does not
establish that a file is unused. No decoder status or original game file was
changed. BSEQ remains **381 SCANNED / 353 DECODED / 0 FAILED / 0 UNKNOWN / 28
UNSUPPORTED**; the 1,109 internal media rows remain **1,103
DECODED_EXISTING_VERIFIED / 6 UNSUPPORTED**. Global coverage remains
**27,824 SCANNED / 21,839 DECODED / 0 FAILED / 5,957 UNKNOWN / 0 PENDING / 28
UNSUPPORTED / 78,498 outputs**.

The three focused audit tests pass. The native PowerShell full suite ran **240
tests: 239 passed, one expected symlink-permission skip**. Reproduce with the
same PowerShell 7 setup above, or run `uv run lgpe map-sequence-audio --root
..` from the project directory. T09 remains `IN_PROGRESS`.

## Exact-build main to BSEQ resource request trace — 2026-10-31

This read-only Ghidra pass examined the actual LGPE Pikachu 1.0.2 ExeFS
`0/main` at `../1.0.2/2b7730a9e56498bbafac2002d4908c6b_NCA/0/main`, SHA-256
`1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8`, with
image base `0x7100000000`. The local install is Ghidra 12.2 PUBLIC under
`D:\Tool\ghidra\ghidra_12.2_PUBLIC`, Java 25.0.5, and its distribution
`LICENSE` identifies Apache-2.0. No Ghidra source checkout or source commit was
present; this records the exact local binary distribution used.

`InspectWwiseSequenceSymbols.java` iterated 10,469 defined string data entries
and found 79 strings matching the bounded BSEQ/Wwise marker list, with 99
references into 10 distinct functions. All 10 decompiled without errors; 17
references had no containing function in the saved database. The defined
string scan had zero hits for `BelugaSoundPlaySe`, `BelugaSoundLoadBank`,
`BelugaSoundAddEvent`, `SoundPostEvent`, `AK::SoundEngine`, or `SESD`. The 79
matches are predominantly literal BSEQ resource paths and are not a recovered
command-dispatch table.

Selected exact-build code evidence:

| Address (`main+offset`) | Observed static code relation |
|---|---|
| `main+0xa81470` | Formats `bin/battle/waza/sequence/ew%03d%s.bseq` or `ew%03d.bseq` from integer inputs, then passes the path to `main+0x1d88b0`. The meaning of those inputs is not assigned here. |
| `main+0xa812c0` | Reads a `fileName` property from an opaque object, formats `bin/battle/waza/sequence/%s.bseq`, checks a helper return value, and passes the selected path to `main+0xaa0c60`; the alternate path is `ee000.bseq`. |
| `main+0xa815e0` | Calls `main+0x27140` on a path object. On the `== 1` branch it passes that object to `main+0xaa0c60`; otherwise it constructs `ee000.bseq` and passes that path to the same callsite. It also writes state bytes at owner offsets `+0x7c` and `+0x779`. |
| `main+0xa81de0` | Receives a path and branches on whether it begins with the global `data/` prefix; it then creates/copies an opaque path object. This is path-object handling, not proof of a successful disk read. |
| `main+0xaa0c60` | Allocates two `0x2a0`-byte objects and passes the path argument and owner-relative data to `main+0x2103c0`; the function stores the resulting object pointers at owner offsets `+0x10` and `+0x18`. No BSEQ decode or Wwise event dispatch is visible in this function body. |
| `main+0x2103c0` | Initializes a request/callback object and calls `main+0xadc70` at `main+0x210494`. The selected BSEQ path object is passed as the resource argument; the fifth argument is the literal zero supplied by `main+0xaa0c60`. |
| `main+0xadc70` / `main+0xa63a0` | The shared helper calls the mutex-protected request/cache routine at `main+0xa63a0`, stores its returned request, and waits through `main+0x23880`. `main+0xa63a0` submits the request through `main+0x276e0` at `main+0xa6a8c`. This reaches the resource request/queue layer; it does not, by itself, identify the BSEQ request's final worker or prove a physical read. |
| `main+0xa81460` | Returns whether the integer at owner offset `+0x7c` equals zero; callers use it as a state-machine gate. The state field's broader meaning is unassigned. |

Other functions with BSEQ literals include `main+0xa81690`, `main+0xa882f0`,
`main+0xa886d0`, and `main+0xa8acd0`; their paths include fixed `em*.bseq`
and `ee*.bseq` resources. The latter function selects `ee610.bseq` or
`ee615.bseq` on one branch and otherwise delegates to the `%s.bseq` path
handler. These are code and path references from the exact local build, not
claims that those branches execute during gameplay.

The helper follow-up expanded from five to eleven selected functions, adding
the path-string joiner, opaque path-object constructor, request constructor,
shared resource helper, cache/request routine, and queue function. All 11 were
found and decompiled. Incoming-call references connect
`main+0xa815e0`, `main+0xa812c0`, and `main+0xa81690` to
`main+0xaa0c60`; the exact call from `main+0x2103c0` to `main+0xadc70` and
the subsequent direct calls to `main+0xa63a0` and `main+0x276e0` were also
recorded. The full helper trace and first string pass are retained as ignored
local logs; the Ghidra scripts and PowerShell wrappers are tracked. Reproduce
from the project root with:

```powershell
pwsh -NoProfile -File scripts/ghidra/Run-InspectWwiseSequenceSymbols.ps1
pwsh -NoProfile -File scripts/ghidra/Run-InspectSequenceRuntimeHelpers.ps1
```

Both wrappers run `-noanalysis -readOnly`, verify the exact source hash before
and after, and check Ghidra's summary marker. The source hash remained
unchanged. Script hashes are `a06b3d559c30a3da1bb1792568fd027350e246c58bb8fe3ffb5851e3d5eabc50`
(`InspectWwiseSequenceSymbols.java`),
`dc9ed390f405775368f92c90552571778c336a9781048de5b93d1ed0dea88ba9`
(`Run-InspectWwiseSequenceSymbols.ps1`),
`844043488284167c4004857625cb9021066e6b87601d076497311253f28f5f72`
(`InspectSequenceRuntimeHelpers.java`), and
`e72f1b812b111e00f80a91766447ccac1dacb9b2babaf7c34696162fe08e85a2`
(`Run-InspectSequenceRuntimeHelpers.ps1`). The two ignored Ghidra application
logs have SHA-256
`8f02a90ea184c5a00f92441a9e859f934653939893387e4dbbe02ae7e770fe52` and
`de0277b41e9f9835c4036a71ee0d59bc19219a7004e47de67555c0087c762aa3`.

This closes a static resource-path link from main into the same BSEQ file
family decoded above. It does **not** validate BSEQ opcode semantics, establish
that `BelugaSoundPlaySe` or `BelugaSoundLoadBank` are runtime commands, prove
the selected BSEQ request reaches a physical `nn::fs::OpenFile`/`ReadFile`
worker, prove event invocation or playback, recover sequence probability/
timing, or show runtime execution. The separately traced encounter caller's
OpenFile path is not transferred to the BSEQ request object. Those claims
remain `UNKNOWN`/`UNVERIFIED`. Current BSEQ
coverage remains **381 scanned / 353 decoded / 0 failed / 0 unknown / 28
unsupported**; internal BNK media remains **1,103
DECODED_EXISTING_VERIFIED / 6 UNSUPPORTED**. A fresh `uv run lgpe coverage`
reported **27,824 SCANNED; 21,839 DECODED; 0 FAILED; 5,957 UNKNOWN; 0 PENDING;
28 UNSUPPORTED; 78,498 outputs**.

The native Windows full test wrapper initially exposed a process-environment
issue: the test process inherited `PATHEXT=.CPL`, so Python could not resolve
the available `git.exe` while validating the pinned PokeLDN checkout. The
wrapper now locates the local Git executable and restores the standard native
suffixes for the child process. After that correction,
`scripts/Test-Project.ps1` completed **240 tests: 239 passed, one expected
symlink-permission skip**. This changed only the test wrapper environment; no
game source or decoded asset changed. T09 remains `IN_PROGRESS`.

### T09 BSEQ request vtable and conditional filesystem worker — 2026-10-31

A follow-up read-only Ghidra 12.2 pass on the same exact Pikachu 1.0.2
`0/main` (SHA-256
`1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8`, base
`0x7100000000`) extends the helper probe to **19 selected functions: 19
decompiled, 0 failed**. The script validates live memory values before
reporting the vtable: global cell `main+0x15fb380` contains `main+0x15287e8`,
whose address point is `main+0x15287f8`; its `+0x38` slot at
`main+0x1528830` points to `main+0x26070`, and `+0x40` at
`main+0x1528838` points to `main+0x26610`.

The BSEQ constructor path from `main+0xaa0c60` passes its selected path object
through `main+0x2103c0` into `main+0xadc70`. That helper forwards it to
`main+0xa63a0`; on the fresh-request path, `main+0x23680` copies the path
object's fields into the resource request beginning at offset `+0x60`. The
shared helper can reuse a request, so this copy is not assumed on a cache hit.
The same call chain forwards a literal zero through the fifth `main+0xadc70`
argument. On the common return path, `main+0x237c0` stores that value at
request `+0x148`, the optional object tested by the open/read helpers. Thus
the BSEQ request has a null cache-like object in this static constructor path;
this conclusion is tied to argument flow and observed branches, not inferred
from a filename.

`main+0x276e0` first tests whether the thread-local manager pointer at TLS
`+0x88` equals its manager argument. If equal, it unlocks the mutex and calls
request vtable `+0x38` immediately. That target, `main+0x26070`, calls
`main+0x238e0`, then request vtable `+0x40`, then `main+0x23970`. With the
BSEQ request's `+0x148` value null, `main+0x238e0` follows the path object
stored at request `+0x60` and calls `nn::fs::OpenFile`; it calls
`nn::fs::GetFileSize` after a successful open. `main+0x26610` allocates a
buffer and calls `main+0x23990`; because `+0x148` is null, that helper reaches
`nn::fs::ReadFile`. The final helper calls `nn::fs::CloseFile` when its
request flag permits. These are exact-build static conditional call edges;
they do not show that the TLS predicate selected the immediate branch, that
the queued branch was later serviced, or that open/read succeeded at runtime.

Reproduce with `pwsh -NoProfile -File
scripts/ghidra/Run-InspectSequenceRuntimeHelpers.ps1`. The wrapper uses
`-noanalysis -readOnly`, checks the original `main` SHA before and after, and
the successful run emitted `selected_functions=19`, `decompiled=19`, and
`function_failures=0`. Current script SHA-256 is
`4fd4a868039274e5e1cdf52f6f99ba74430ff1c2e66ae9e705a50303cbda1653`; wrapper
SHA-256 is `e72f1b812b111e00f80a91766447ccac1dacb9b2babaf7c34696162fe08e85a2`;
the ignored successful stdout and Ghidra script-log SHA-256 values are
`d1ea037c203697ca9d1a1505780144b9dae189b8a2551b6b80ff31ccd74019dc` and
`41528623c149acc5f582d8861cbb6057ef37a74e7ffb120634681b5002887237`.
The earlier statement in this note that the final worker was unverified is
superseded only for this **conditional static call chain**. Successful file
I/O, queue servicing, BSEQ parsing/command dispatch, Wwise invocation,
playback, timing, and runtime reachability remain `UNKNOWN`/`UNVERIFIED`.
Coverage remains **27,824 SCANNED; 21,839 DECODED; 0 FAILED; 5,957 UNKNOWN;
0 PENDING; 28 UNSUPPORTED; 78,498 registered outputs**. T09 remains
`IN_PROGRESS`.

### T09 BSEQ object vtable and path-selection callers — 2026-10-31

A further exact-build, read-only Ghidra pass expands the helper trace to **27
selected functions: 27 decompiled, 0 failed**. `main+0x2103c0` installs the
object vptr from global cell `main+0x15fe628`; the cell contains
`main+0x1541e30`, giving address point `main+0x1541e40`. The bounded executable
prefix maps slots 0 and 1 to `main+0x2109e0` and `main+0x210ae0`. Both bodies
reset/release the nested request state and call `main+0x23c70`; neither reads
the header values that the constructor copied from buffer offsets `+0x04` and
`+0x0c` into owner offsets `+0x18c` and `+0x184`. Slots 2 and 3 point to
`main+0x2fe0` and `main+0x3030`; slot 4 points to `main+0x3050`, which has no
FunctionManager entry in the saved Ghidra database. The slot scan stops at
slot 5's non-code value and does not classify those remaining methods.

The caller trace adds path-selection context without assigning gameplay
meaning. `main+0x1db010` reads a path at caller offset `+0x28`, normalizes it
through the exact-build path helpers, passes the resulting object to
`main+0x2103c0` with a literal zero final argument, and stores the constructed
object at caller-owner offset `+0x98`. `main+0xa812c0` reads the opaque key
`fileName`, formats `bin/battle/waza/sequence/%s.bseq`, and uses
`ee000.bseq` when its path check fails. `main+0xa8acd0` uses the low 16 bits
of its third argument; values `0` or `0x3c` select `ee610.bseq` or
`ee615.bseq` through a virtual predicate, while other values use the generic
`fileName` path. `main+0xa8ce20` has a switch at owner offset `+0x774`; case
2 selects `ee420.bseq` or `ee422.bseq` through another virtual predicate.
`main+0xa81690` initializes a bounded table of `em*.bseq` path records,
chooses an index from `main+0x9e3670` and a byte at an opaque object offset
`+0x2e1` via `main+0xb0c590`, maps results above `0x2f` to index 0, checks the
chosen path, then falls back to `ee000.bseq`.

This is a static resource-selection and lifetime trace, not BSEQ command
dispatch. No consumer of the constructor's `+0x184/+0x18c` fields or the
loaded BSEQ command stream was established in this pass; selector inputs and
virtual predicate semantics remain unassigned. Reproduce with
`pwsh -NoProfile -File
scripts/ghidra/Run-InspectSequenceRuntimeHelpers.ps1`; the exact local
`main` hash was rechecked before and after, and the run used
`-noanalysis -readOnly`. Current script SHA-256 is
`965f39182fb870456eccb5636ff09f81738a326deb9220b1251c2e7c2dfd9016`;
wrapper SHA-256 is `e72f1b812b111e00f80a91766447ccac1dacb9b2babaf7c34696162fe08e85a2`;
ignored stdout and Ghidra script-log SHA-256 values are
`63d47ee0241b3851d3ae46869e5f3a6ababbe93011cc5d2d39fb4b9b1e3b3eb6` and
`e9750e7b981ce292b7a433bbbef8c59f148163c93b415d701a07b31912845fae`.
BSEQ source coverage and global source coverage are unchanged: **381
SCANNED / 353 DECODED / 0 FAILED / 0 UNKNOWN / 28 UNSUPPORTED**; **27,824
SCANNED / 21,839 DECODED / 0 FAILED / 5,957 UNKNOWN / 0 PENDING / 28
UNSUPPORTED / 78,498 registered outputs**. T09 remains `IN_PROGRESS`.

### T09 BSEQ header and command-record consumer cross-reference — 2026-10-31

The previously unidentified consumer is now statically located in the exact
Pikachu 1.0.2 `0/main`. A full instruction-text sweep found 320 raw occurrences
of immediates `#0x184`/`#0x18c` in 142 functions; those numeric hits alone are
ambiguous. The confirmed sequence-object chain is grounded by the constructor,
its callers, and the two consumers: `main+0x2103c0` stores the resource buffer
pointer at object `+0x170`, initializes its command cursor to buffer `+0x10` at
object `+0x178`, copies header bytes `+0x04` and `+0x0c` into object `+0x18c`
and `+0x184`, and stores constructor arguments at `+0x190`/`+0x198`.
`main+0xaa0c60` supplies its owner object as the `+0x190` callback receiver and
the static `main+0xf97e30` address as the `+0x198` table argument.

`main+0x210510` is called at `main+0x80f5b4` from the active-object update
loop `main+0x80f4d0`. Its body reads the frame bound at object `+0x184` and
format version at `+0x18c`, advances through frame-indexed command records,
and invokes the owner object's virtual slot `+0x10` via object `+0x190`.
The version-dependent command-field reads align with the pinned parser's
version-3 `Cmd.from_bytes` layout: start/end frame at record `+0/+4`, group at
`+8`, option words at `+10/+12`, and command ID at `+14`. The alternate
target-frame path `main+0x81a790` calls `main+0x210880`; that body can reset
its cursor to buffer `+0x10`, uses the header frame bound/version, and dispatches
records through the same virtual slot. The exact callback implementation is
still dynamic at these callsites, so command effects are not assigned here.

This was cross-checked against actual local source bytes, the prior decoded
JSON, and the pinned upstream parser rather than a tree-name inference:

| Evidence | Value |
|---|---|
| RomFS source | `bin/battle/waza/sequence/ee000.bseq` |
| Source bytes / SHA-256 | `124` / `1b38facf44af506167a588da86c5a6926704336178669248e022e250366cc88f` |
| Header bytes | `5345534403000000000000001d000000` (`SESD`, version `3`, reserved `0`, frame value `29`) |
| Mirrored output | `decoded/1.0.2/romfs/bin/battle/waza/sequence/ee000.json`, 2,320 bytes |
| Output SHA-256 | `57d054f8269d6e519a4cc2bb913ac0a0f25a189c24283c4fef8ee2679fad1035` |
| Decoder validation | 1 group, 5 commands, exact byte round-trip, semantic round-trip equal |
| Cross-check | first `DummyLabel` record ends at frame `29`, matching the header value |

The manifest row is `DECODED_EXISTING_VERIFIED`; the WSL-side verifier normalizes
its Windows-generated backslash output path before checking the file. Its source
hash, output hash, and embedded `raw_hex` all match. The direct parser invocation
also completed `decode_bseq_bytes` using the pinned pbseqtool LGPE dictionary
at commit `6f122d1b7945797cae472960b798bf28523f8acd`; it independently reported
`byte_roundtrip_exact=true` and `semantic_roundtrip_equal=true`. The upstream
field basis is `tools/src/pbseqtool/sesd.py` (`SESD.from_bytes` header reads and
`Cmd.from_bytes` version-3 record layout). Parser-provided command labels and
gameplay semantics remain upstream reference data, not independently verified
game behavior.

The new SHA-guarded Ghidra offset sweep and the expanded helper pass both ran
with Ghidra 12.2 PUBLIC, `-noanalysis -readOnly`, image base `0x7100000000`,
and the same exact-build `main` SHA-256
`1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8` before
and after. The helper pass decompiled **31/31** selected functions with **0
failures**; the offset sweep emitted **320** raw hits across **142** function
bodies, then constructor and caller cross-references were used to reject
unrelated same-number offsets. Scripts and logs:

- `scripts/ghidra/InspectSequenceRuntimeHelpers.java` SHA-256
  `67cf7b109620d3d0b0eee88c23ef2555b4454fc464213c4d134f94feb623f269`;
  wrapper SHA-256 `e72f1b812b111e00f80a91766447ccac1dacb9b2babaf7c34696162fe08e85a2`.
- `scripts/ghidra/ScanSequenceHeaderFieldOffsetUses.java` SHA-256
  `1f0df4ffc7deb96168bb3986358c0df7aedee45e2a5770622890b9b73487a8ed`;
  wrapper SHA-256 `97a4b3eee9200ca0ce4278f88b72cec0f7d59fc0af81de6e2111340c9f0ad25f`.
- Reproduction: `pwsh -NoProfile -File scripts/ghidra/Run-ScanSequenceHeaderFieldOffsetUses.ps1`
  and `pwsh -NoProfile -File scripts/ghidra/Run-InspectSequenceRuntimeHelpers.ps1`.

This establishes static command-record parsing and virtual dispatch edges, not
the callback's runtime target, command gameplay effects, successful runtime
resource I/O, sequence selection at runtime, or Wwise playback. Counts remain
BSEQ **381 SCANNED / 353 DECODED / 0 FAILED / 0 UNKNOWN / 28 UNSUPPORTED** and
global **27,824 SCANNED / 21,839 DECODED / 0 FAILED / 5,957 UNKNOWN / 0 PENDING
/ 28 UNSUPPORTED / 78,498 registered outputs**. T09 and T10 remain
`IN_PROGRESS`; no original source or decoded output was modified.

After this script/doc update, `pwsh.exe -NoProfile -File
scripts/Test-Project.ps1` completed with exit code 0: **240 tests, 239 passed,
1 expected symlink-permission skip**. The containment test's printed
`ValueError: path outside allowed directory` is its expected rejection case;
it did not fail the suite.

## T09/T10 exact-build BSEQ delegate and command dispatch — 2026-10-31

A further Ghidra 12.2 trace resolves the callback object passed by the BSEQ
reader, using only the local Pikachu 1.0.2 `0/main` (SHA-256
`1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8`, image
base `0x7100000000`). Every address below is `main+offset` for this build.

The full controller pointer is not the sequence callback object. At
`main+0xa7899c`, the controller path calls `main+0xaa0b80` with the newly
constructed delegate storage and controller pointer. That initializer writes
the delegate vptr, captures the controller pointer in two fields, initializes
two null fields, installs a second vptr, and sets a 16-bit value at delegate
offset `+0x30`. At `main+0xa789b0`, the caller stores the delegate pointer at
controller offset `+0x3e0`; the replacement path releases the previous
pointer. The sequence-path callers load that field and pass it through
`main+0xaa0c60`; `main+0x2103c0` stores the resulting callback pointer at
sequence-object offset `+0x190`.

The callback vptr is read from global cell `main+0x1608de8`, whose value is
`main+0x15d5aa0`; the address point is `main+0x15d5ab0`. Its observed entries
are `+0x00 → main+0xaa2310`, `+0x08 → main+0xaa2370`, and
`+0x10 → main+0xaa0eb0`. The BSEQ reader's virtual call uses callback vptr
offset `+0x10`, so it enters `main+0xaa0eb0`. This target was initially
undefined in the saved Ghidra program; a dedicated pass created its function
boundary and confirmed the decompilation. `main+0xaa2310` and `main+0xaa2370`
are the other observed table entries and release/clear delegate fields.

The controller object has a separate address-point candidate at
`main+0x15d3268`, directly stored by `main+0xa77c20`. The candidate's observed
method references include `main+0xa8acd0` at slot 78 and `main+0xa8ce20` at
slot 152, but its preceding RTTI pointer is zero and its type name is
unresolved. This controller vptr candidate is not the delegate vptr at
`main+0x15d5ab0`; the BSEQ callback field points to the delegate stored at
controller `+0x3e0`.

The dispatcher `main+0xaa0eb0` reads the first 32-bit word through its command
record pointer as the lookup index and branches on bit 0 of its fourth
argument. The per-frame reader `main+0x210510` passes `0`, which reaches an
indirect handler table. The target-frame reader `main+0x210880` passes `1`,
which reaches the dispatcher's inline switch. The handler pointer cell at
`main+0x1608df8` resolves to table `main+0x15d4c70`. A bounded read-only probe
found **256 consecutive executable pointers** at indexes 0–255, reaching its
configured scan limit without a non-code terminator; the table's full length
is therefore not established.

The pinned external `pbseqtool` LGPE dictionary at commit
`6f122d1b7945797cae472960b798bf28523f8acd` contains **227 unique IDs**. Its
two-byte IDs, read by the exact-build consumer as little-endian 16-bit values,
map numerically to observed table indexes 0–226. The report retains every
observed slot and parser-reference label without promoting those labels to
verified gameplay semantics. On the actual local sample
`bin/battle/waza/sequence/ee000.bseq` (124 bytes, SHA-256
`1b38facf44af506167a588da86c5a6926704336178669248e022e250366cc88f`), the
pinned parser returned five commands. All five IDs joined their table slots,
and all five targets completed Ghidra decompilation:

| Parser reference label | Raw ID bytes | Table index | Exact-build target | Body observed |
|---|---:|---:|---|---|
| `DummyLabel` | `00 00` | 0 | `main+0xada060` | 4 bytes / 1 instruction (`ret`; exact bytes later verified as `c0 03 5f d6`) |
| `CameraReset` | `26 00` | 38 | `main+0xade320` | 84 bytes / 21 instructions |
| `GaugeDisp` | `7c 00` | 124 | `main+0xaeb5e0` | 208 bytes / 52 instructions |
| `GaugeDispAll` | `7d 00` | 125 | `main+0xaeb6b0` | 72 bytes / 18 instructions |
| `GaugeDamage` | `7e 00` | 126 | `main+0xaeb700` | 428 bytes / 107 instructions |

The one-instruction `DummyLabel` target decodes as `ret`; the later exact-byte
probe records its bytes and sole table-slot data reference. The other four
decoded handler bodies and their direct helper calls are preserved in the
Ghidra log; no gameplay outcome, timing, sound playback, or runtime
reachability is inferred.

The scripts and generated report are:

- `scripts/ghidra/InspectSequenceRuntimeHelpers.java` SHA-256
  `bf4815e53d5a8030454c8c0797a481ebf4f8733d21b8d7d6fc17d5f1bcf0fb1f`;
  its wrapper SHA-256 remains
  `e72f1b812b111e00f80a91766447ccac1dacb9b2babaf7c34696162fe08e85a2`.
- `scripts/ghidra/InspectSequenceCallbacks.java` SHA-256
  `a3989c17396979da5ee2132103dcc041ee5489322ff6bf87b747806a65972157`;
  wrapper SHA-256 `d3c39d7f608aef8887af4b479ea8d525b344eba8b3b3761bb38af4ac89e2a3e4`.
- `scripts/ghidra/InspectSequenceOwnerVtables.java` SHA-256
  `f9c1ad97b71e7337f81a9615c2a10505f16d9f441d80003ae39b058ded0c3341`;
  wrapper SHA-256 `dbc4b7c8fc72638a962b0c90028310ff07f1cee40aa816508c6a0dbeea293fe2`.
- `scripts/research/build_bseq_runtime_dispatch.py` SHA-256
  `842766a2ab1f98f8ef3920e3049c128bc500bad68cbadae5582063709d54f9e8`.
- `manifests/bseq-runtime-dispatch.json` SHA-256
  `331b189a10d047f9083d8211908a430b9fb6ee64bff3138c77024deb213e8d6e`;
  it records the exact main, source sample, parser commit/dictionary hash, all
  256 observed handler slots, 227 dictionary ID joins, five sample joins,
  script hashes, and limitations.
- Successful helper stdout/script-log SHA-256:
  `44ff1549615a6a5efa6f6b1abc2823a794d027ae4d03d19887c33f800fd5918f` /
  `efe14af0e87735286c5ca55f7f0172d783c1450162f4c01a76a1d901e64060a6`.
- Successful callback stdout/script-log SHA-256:
  `32d5fb31811eafb44c52eb664d875be76ed947c5bb5e9398e20da9e99cf47712` /
  `8c365071469b0642d6fcbdb73b9af201a037a372e06137b8a874f661ed1a1371`.
- Successful owner-vtable stdout/script-log SHA-256:
  `1cf3a1729e28fc122cc6b25faee7efb4059873b91c79a4b7bbf4d6ba7f0c5d51` /
  `6e49ea28292209daf552b4636e1fe7a7cf533deaeb9584d4972c4a2e5ab49ff1`.

Reproduction commands:

```powershell
pwsh.exe -NoProfile -File scripts/ghidra/Run-InspectSequenceRuntimeHelpers.ps1
pwsh.exe -NoProfile -File scripts/ghidra/Run-InspectSequenceCallbacks.ps1
pwsh.exe -NoProfile -File scripts/ghidra/Run-InspectSequenceOwnerVtables.ps1
python3 scripts/research/build_bseq_runtime_dispatch.py
```

The helper pass used Ghidra `-noanalysis -readOnly` and decompiled **40/40**
selected functions with **0 failures**. The callback pass used `disassemble`
and `createFunction` in the local Ghidra project database to add five missing
function boundaries; it decompiled **8/8** targets with **0 failures**. Both
wrappers SHA-256 checked the original `main` before and after. The game binary
and decoded asset outputs were not changed; the Ghidra analysis database was
changed by the callback pass.

Asset counts are unchanged: BSEQ **381 SCANNED / 353 DECODED / 0 FAILED / 0
UNKNOWN / 28 UNSUPPORTED**; global **27,824 SCANNED / 21,839 DECODED / 0
FAILED / 5,957 UNKNOWN / 0 PENDING / 28 UNSUPPORTED / 78,498 outputs**. The
previous “dynamic callback target” boundary is resolved for this constructed
delegate and the two statically observed dispatch modes. Runtime execution,
full dispatch-table length and command/gameplay semantics remain UNKNOWN;
T09/T10 remain `IN_PROGRESS`.

Focused manifest parser tests passed **4/4** with
`PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_bseq_runtime_dispatch.py' -v`.
The native Windows project suite then passed **244 tests: 243 passed, 1
expected symlink-permission skip**, using `pwsh.exe -NoProfile -File
scripts/Test-Project.ps1`.

## T10 BSEQ handler target byte verification — 2026-10-31

A follow-up corrected the earlier `br x16` disassembly note for the
`DummyLabel` slot. A new Ghidra 12.2 `-noanalysis -readOnly` probe verified the
exact Pikachu 1.0.2 `main` SHA-256 before and after. At `main+0xada060`,
Ghidra reads one 4-byte `ret` instruction with bytes `c0 03 5f d6`; the saved
reference database has one incoming DATA reference, from dispatch-table slot
0 at `main+0x15d4c70`. No indirect tail branch exists at this address. This
corrects the prior row and limit text. It assigns no gameplay meaning to the
pinned parser label.

The same read-only probe continued scanning pointer-shaped values after the
previous 256-slot limit. It inspected indexes **256–1351** (1,096 mapped
slots): **858** values pointed into executable memory, **238** did not, and
the configured eight-value non-executable run occurred at indexes 1344–1351.
This is an extended memory scan; adjacent pointer data can look executable,
so the dispatch table's complete length and command-ID bounds remain UNKNOWN.

The reproducible output is `manifests/bseq-dispatch-boundary.json` (SHA-256
`c71673787e5c1492a125bd39db6a371e98de2d37dd4f653bae50de6e600ef20f`). Its
normalized evidence log SHA-256 is
`7a96e7dc4b10e662420eb1797acc13c7aeafbec8f58b07bd64ad8e63c2870a21`; repeated
Ghidra runs produce the same normalized log and manifest hashes. The raw
stdout is retained for inspection, but its startup timing noise changes its
hash between runs. The probe script and wrapper hashes are
`78decb34f7606b6a151e868433aeaa6200f8f5c733c735a381cf5d5fe6016df2` and
`1c66f5f3413379769fa2aa5b12e17170ae2ee1d8e850db5a98add91c275c4d94`.
The report is regenerated with `uv run lgpe bseq-dispatch-boundary`; the
Ghidra trace runs with
`pwsh.exe -NoProfile -ExecutionPolicy Bypass -File scripts/ghidra/Run-InspectBseqDispatchBoundary.ps1`.
Five focused boundary-parser tests and four existing dispatch-parser tests
pass. Main/asset coverage is unchanged: BSEQ **381 SCANNED / 353 DECODED / 0
FAILED / 0 UNKNOWN / 28 UNSUPPORTED**; global **27,824 SCANNED / 21,839
DECODED / 0 FAILED / 5,957 UNKNOWN / 0 PENDING / 28 UNSUPPORTED / 78,498
outputs**. T09/T10 remain `IN_PROGRESS`.
