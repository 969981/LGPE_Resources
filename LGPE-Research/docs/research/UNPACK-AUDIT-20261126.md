# LGPE 1.0.2 — repository unpack audit (2026-11-26)

Base commit: `74bcb0f16db16ecb0498d23fd28d9346cff3193e`.

## Actual remote verification

The repository API was used to read the original SARC bytes and each corresponding output at the same pinned commit. An independent SARC reader checked the header, BOM, SFAT/SFNT, names and bounds, sliced member payloads and compared them byte-for-byte against the tracked output. No game asset was modified or added.

| ROMFS source | Git blob SHA-1 | Bytes | Matched |
|---|---|---:|---:|
| bin/app/gameover/gameover_black_00.arc | c652ad372efa767c553ce3f891e38524d4e112e9 | 29116 | 9/9 |
| bin/app/cursor/bin/cursor.arc | ce42a071ada20b43ea743108eb1b1986a2babc61 | 33140 | 8/8 |

Both have an 8296-byte `timg/__Combined.bntx` and BFLYT/BFLAN members. The original member paths and payloads match. The BNTX blobs differ, so the equal file lengths do not establish identical texture data. The third planned SARC sample was not checked because the connector call limit was reached.

The independent repository tree query (not truncated) enumerated 374 ARC in bin/app and 643 GFPAK in bin/archive, agreeing with the historical 1017 archive count. No full extraction replay was performed.

### Font

`bin/font/num_00.bffnt`: 140340 bytes; declared size agrees. FINF/TGLP/CWDH/CMAP/CMAP/CMAP are bounded. The embedded sheet at offset 4096, length 135272, is byte-identical to the existing Sheet_0.bntx. Sheet_0.png has PNG signature and IHDR 512x512, 2863 bytes. PNG pixels were NOT independently re-decoded.

The recorded failure is a conflicting `num_00.json`, not proof of an invalid FFNT. Existing JSON contains transient commands; the current decoder includes a narrowly scoped legacy-report migration. Retry on a local checkout and verify receipts before changing coverage; do not delete or overwrite conflicts.

## Coverage discrepancy

- [README](../../README.md): 21843 decoded, 0 failed, 5953 unknown, 28 unsupported, 78504 outputs.
- [coverage.summary.json](../../manifests/coverage.summary.json): 21842 decoded, 1 failed, 5953 unknown, 28 unsupported, 78514 outputs.
- The tracked failures manifest identifies the BFFNT conflict. Counts are not reconciled here.
- The current ExeFS directory contains `eevee_main` in addition to the previously documented six files. Its version/hash must be classified separately before using Pikachu-specific address evidence.
- The split directory contains two compressed receipt manifests, JDK files and Ghidra project data. These are not game archive formats; restore receipt manifests separately with a local 7-Zip installation and validate existing destinations first.

## Reproduction on a local checkout

Run from LGPE-Research after restoring receipt manifests as needed:

```powershell
uv sync
uv run python -m unittest discover -s tests -v
uv run lgpe scan --root ..
uv run lgpe decode-archives --limit 0 --execute
uv run python scripts/audit_ui_sarc.py
uv run lgpe decode-bffnt --limit 0 --execute
uv run lgpe verify
uv run lgpe coverage
```

The new UI audit script is read-only for extracted assets by default. To restore missing SARC outputs, add `--restore-missing`; existing conflicts are refused by the existing archive reader. It writes a separate JSONL report in work/ and inventories embedded BNTX members by magic, not just extension. It does not register production receipts or decode nested textures to PNG. Script execution and regression tests were not possible in the remote connector environment.

## Next steps

1. Restore and verify receipt manifests locally; repeat scan and reconcile BFFNT status.
2. Audit all 374 SARC, then index all nested BNTX and BFLYT/BFLAN binding evidence.
3. Treat 1344 historically decoded loose BNTX as a separate population from nested texture containers. Build texture-member provenance before semantic image mapping.
4. Resolve 3171 unknown BIN, 698 GFBCOL, shader/camera/animation configs and 28 unsupported demo BSEQ by format and actual reader evidence.

Blocker: current compute container cannot resolve github.com for git clone, has no mounted game dump, and connector reads individual files rather than running repository commands. Historical results are not current-run results.
