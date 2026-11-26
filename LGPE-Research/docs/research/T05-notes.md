# T05 — ARC identification and real extraction (2026-10-28)

`bin/app/battle/bin/battle_command_00.arc` was inspected as bytes and is **SARC**, signature `53415243`, little-endian BOM `FFFE`, version `0x0100`; this conclusion applies to this sample, not arbitrary `.arc` files. Header/SFAT/SFNT fields and all 41 stored filenames were validated against the pinned pkNX SARC source described in T04. Hash multiplier is 0x65 and every stored filename hash matches. All member ranges lie inside the source and are extracted under their original stored paths.

Actual result: 41 members, 1,472,090 output bytes, zero failed/empty products. Source SHA256 `7fdd7cf1378565f8b157f07250c5592fbc391063fe6f18ac495222943159534d` remains unchanged. For example, `anim/battle_button_grptxt_00_keep.bflan` is 192 bytes, SHA256 `430fbfcdf594f5e6168d2fdf7164bdf92e40055f3ab7602e7e7e94a91bf25fd8`. Embedded `timg/__Combined.bntx` is a texture archive for a later decoder. No nested SARC/GFLXPACK signature was observed among these output headers.

Implementation, exact tool revisions/licenses, commands, output aggregate hashes, tests and ignored machine manifests are recorded in [T04-notes.md](T04-notes.md). Unsupported/unnamed SARC members explicitly fail rather than receiving invented paths. More `.arc` samples and other families remain unsampled. No independent SARC extractor executable was run, so evidence is SOURCE_CODE + DECODED, not full cross-tool SARC validation.

## Additional GO Park SARC samples — 2026-10-29

The full archive manifest includes these two separate GO Park UI samples. Both
have the `SARC` signature and little-endian BOM `FFFE`; all stored internal
paths are preserved under `<source filename>.contents/`:

| Source | Source SHA-256 | Members | Output bytes | Example internal path |
|---|---|---:|---:|---|
| `bin/app/go_park_information/bin/go_park_list_00.arc` | `c9bea8745abf70f328976b374f503a790c0f1de1f24e67441168bfd493f87434` | 27 | 255,780 | `anim/go_park_list_00_in.bflan` |
| `bin/app/go_park_information/bin/go_park_poke_list_00.arc` | `082b3c52e176249157ae0a019dacfb9367e8ecbe5b0f992e4ffb3757c6173a67` | 19 | 733,606 | `go_park_poke_list_00.flyt` |

A read-only local rehash checked each source and all 46 extracted members
against `manifests/archives.jsonl`; source hashes, member sizes and member
hashes all matched with zero mismatches. The project receipt verifier gave
`selected_sources=2`, `registered=46`, `verified=46`, `bad=0`, `errors=[]` for
the same sample list. Its process exited `5` because the global failure ledger
also reports 79 unrelated historical FAILED/UNSUPPORTED rows; that field is
not part of the two-source verification result.

Reproduce the targeted receipt check from this checkout in PowerShell 7:

```powershell
@'
bin/app/go_park_information/bin/go_park_list_00.arc
bin/app/go_park_information/bin/go_park_poke_list_00.arc
'@ | Set-Content -Encoding utf8 work\t05-go-park-samples.txt
D:\SDK\uv-x86_64-pc-windows-msvc\uv.exe run lgpe verify --sources-file work\t05-go-park-samples.txt
```

The Linux `uv` runtime cannot create its venv on this X: 9P checkout; the
Windows `uv` command above uses the project's rebuilt, lock-synced venv. This
does not affect decoded products or the immutable game source.
