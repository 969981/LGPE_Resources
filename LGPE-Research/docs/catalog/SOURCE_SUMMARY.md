# Snapshot-derived baseline (not a byte-level scan)

Source: `docs/source_snapshot/pikachu.1.0.2.txt`, UTF-16, exported by PowerShell's `tree /f`. This listing contains **27,824 apparent files** (of which 27,819 have suffixes suitable for the CSV inventory), and excludes directory rows.

## Key observed top-level source structure

```text
1.0.2/
└─2b7730a9e56498bbafac2002d4908c6b_NCA/
  ├─0/                                  # contains main, main.npdm, rtld, sdk, subsdk0, subsdk1
  └─1/
    └─bin/
       ├─app/...
       ├─archive/pokemon/*.gfpak
       ├─archive/field/*.gfpak
       ├─battle/ai_script/*.amx
       ├─field/param/encount/encount_data_{p,e}.bin
       ├─message/<Language>/.../*.dat / *.tbl
       └─pokelib/personal/personal_total.bin
```

`uv run lgpe tree-catalog` regenerates the full source listing as `docs/catalog/snapshot_file_inventory.csv` and counts as `docs/catalog/snapshot_summary.json`. Actual files must be scanned with `uv run lgpe scan`; only that produces actual size and magic evidence.

## Initial top suffix counts

| ext | count | ext | count |
|---|---:|---|---:|
| `.bin` | 6,736 | `.dat` | 6,532 |
| `.tbl` | 5,395 | `.bntx` | 1,344 |
| `.ptcl` | 1,160 | `.wem` | 1,134 |
| `.gfbcol` | 698 | `.gfpak` | 643 |
| `.gfbanm` | 455 | `.arc` | 374 |
| `.gfbmdl` | 321 | `.bnk` | 265 |

These counts should not be treated as successful decompression counts.

## Actual filesystem comparison (2026-10-28)

`uv run lgpe scan` found 27,824 files in the extracted partitions. All 27,819 snapshot inventory paths matched. The five additional scan paths are the extensionless ExeFS files `main`, `rtld`, `sdk`, `subsdk0`, and `subsdk1`; no snapshot path was missing. Detailed machine output is `scan_snapshot_diff.json`.
