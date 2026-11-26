# T07 follow-up: grammar DAT and `asset.tbl` probe — 2026-10-29

## Scope and source versions

This pass examined the nine actual files under `bin/message/grammar/` and the
unpaired `bin/message/asset.tbl` from the extracted LGPE 1.0.2 RomFS. Inputs
were read only. No JSON was emitted and no manifest or source file was
changed.

Local source checkouts used for format-boundary review:

| Project | Commit | Local license |
|---|---|---|
| pkNX | `d191cd0e5c05f2af81d9a41c1f1d82e6621b351a` | GPL-3.0 |
| pokedat | `bd423b2cad9aa852fddb796bbba3c5e7b381289b` | GPL-3.0 |
| read_swsh | `1a54a75a5ce4c740f9a0da688ec26e3327bdfda2` | GPL-3.0 |

A repository search for `grammar` and `asset.tbl` across these checkouts found
no source or documentation matches. The local game-data batch code pairs a
message DAT only with a same-directory, same-stem `.tbl`. pokedat's
`TblHandler._get_tbl_path` likewise derives a sibling TBL from the DAT path;
it has no global-table association rule. Its `TextFile` reader requires one
section, a zero initial key, a valid section offset, and a section length
matching the file. The project's `gamedata_decode.message` has the same
LGPE-message envelope gate before it reads AHTB labels.

## Actual sample bytes and decode attempts

The source paths below are relative to
`../1.0.2/2b7730a9e56498bbafac2002d4908c6b_NCA/1/`. The first 16 bytes are
shown as hex. For files at least 20 bytes long, the listed error was returned
by the project's LGPE-message decoder when `asset.tbl` was tried as a
read-only candidate label table. The 2-byte files fail the message-header
minimum-length check.

| Grammar DAT | Bytes | SHA-256 | First 16 bytes | Result with `asset.tbl` candidate |
|---|---:|---|---|---|
| `English.dat` | 86 | `76341d90414dcdb5a330fb205e66fb0eaff84c66bc4944f67f8d0f6f003f2061` | `040622002c0036004600000000000000` | `ValueError: invalid LGPE text header` |
| `French.dat` | 538 | `fb83a92ef3ba82400c78f126ac6b1e614dcff8dc77a9948f33f27fe3e82bfdfe` | `0c0caa00ca00ea000801260154018201` | `ValueError: invalid LGPE text header` |
| `Italian.dat` | 1,602 | `ba0750015be1e667ee7f0948915e01fa87a2a8b36719ed4833de0909bc60a83a` | `101e020238026e02ea026603be031604` | `ValueError: invalid LGPE text header` |
| `German.dat` | 334 | `9cb8aeccd90b41f7deb62a6c47510c3b7d36176f0392bb2ff93231d5ebde5ddd` | `08095a0078009600ae00c600e4000201` | `ValueError: invalid LGPE text header` |
| `JPN.dat` | 2 | `96a296d224f285c67bee93c30f8a309157f0daa35dc5b87e410b78630a09cfc7` | `0000` | `ValueError: truncated message header` |
| `Korean.dat` | 2 | `96a296d224f285c67bee93c30f8a309157f0daa35dc5b87e410b78630a09cfc7` | `0000` | `ValueError: truncated message header` |
| `Simp_Chinese.dat` | 2 | `96a296d224f285c67bee93c30f8a309157f0daa35dc5b87e410b78630a09cfc7` | `0000` | `ValueError: truncated message header` |
| `Spanish.dat` | 804 | `d27412d77e7526ca9841b1e9c042d68b0cb9b7b0a345a117c07cc531ca68f8b1` | `0c12f20016013a0166019201ca010202` | `ValueError: invalid LGPE text header` |
| `Trad_Chinese.dat` | 2 | `96a296d224f285c67bee93c30f8a309157f0daa35dc5b87e410b78630a09cfc7` | `0000` | `ValueError: truncated message header` |

The shared `asset.tbl` is 336,463 bytes, SHA-256
`961b9cc7de222c0fa7b57746ac1cf8da35f20c3aee0547646947504fcc34fb0b`, with
the AHTB magic and 8,290 parsed label entries: 840 `common`, 4,540 `script`,
and 2,910 `debug` path IDs. Its IDs include paths such as
`English/common/app_common.dat` and `Trad_Chinese/script/town002.dat`;
inspection of all labels found zero `grammar` path components. This does not
establish the file's full runtime role, but provides no path or label evidence
that it is the missing grammar companion.

The upstream pokedat CLI was run on three actual samples, writing only to a
scratch path:

```bash
python3 tools/src/pokedat/main.py read ../1.0.2/2b7730a9e56498bbafac2002d4908c6b_NCA/1/bin/message/grammar/English.dat /tmp/pokedat-grammar-probe --version=LGPE --format=json
python3 tools/src/pokedat/main.py read ../1.0.2/2b7730a9e56498bbafac2002d4908c6b_NCA/1/bin/message/grammar/French.dat /tmp/pokedat-grammar-probe --version=LGPE --format=json
python3 tools/src/pokedat/main.py read ../1.0.2/2b7730a9e56498bbafac2002d4908c6b_NCA/1/bin/message/grammar/JPN.dat /tmp/pokedat-grammar-probe --version=LGPE --format=json
```

Each logged `Error extracting strings`; `/tmp/pokedat-grammar-probe` was not
created. As a positive control, the same local decoder accepted the real
paired `bin/message/English/common/go_park.dat` and `.tbl`, returning 92 lines
and one unpaired label. This shows the probe still accepts a known-valid LGPE
text pair.

## Classification

The nine grammar DAT files do not pass the verified LGPE message envelope and
the public local readers provide no grammar-specific format or companion
mapping. `asset.tbl` has AHTB labels for message resource paths, but none name
the grammar directory; using it as a global substitute fails on the grammar
samples before labels are consumed. No field or language semantics are
asserted. Keep the nine grammar DAT rows and `bin/message/asset.tbl` as
`UNKNOWN`; do not create mirrored JSON outputs from these experiments. The
T07 game-data manifest remains 9,993 decoded / 13 unknown / 0 failed / 0
pending.
