# T08 BFFNT NX decode

Date: 2026-11-01

## Verified local sample

`bin/font/num_00.bffnt` is the only `.bffnt` source in the LGPE 1.0.2 RomFS
catalog. It is 140,340 bytes with SHA-256
`5a4228c020523d3f260be26ccae284dfff7a7af30b835ed73388e937d5bcc9bc`.

The headless adapter follows the pinned Switch-Toolbox BXFNT source in
`tools/src/Switch-Toolbox/File_Format_Library/FileFormats/Font/BXFNT` (commit
`3fcb87f1fea25ad56db139b0d9577db591f54118`, GPL-3.0). It accepts only the
observed little-endian NX `FFNT` version `0x04010000`. It validates the 20-byte
header, declared file size, six consecutive sections, FINF references, linked
CWDH/CMAP offsets, TGLP sheet bounds, and exact source length. It exports the
section offsets and hashes, the FINF fields from the source reader, 218 CWDH
width entries, and three CMAP maps: two Direct maps and one 27-entry Scan map.
No additional field semantics are inferred.

The pinned `FFNT.Read` contains an inconsistent common-header `FileSize`
read (`UInt16`) while the same class's `FFNT.Write` emits a 32-bit file size
followed by a 16-bit block count. The adapter uses the writer's field widths;
on this sample the 32-bit size equals the actual 140,340-byte file and the
16-bit block count equals the six parsed section headers.

The TGLP sheet begins at source offset `0x1000`. The exact embedded BNTX is
135,272 bytes with SHA-256
`75dd4246c77841a0a2c98ad34c223998acad7df9736cc0ffa1e62860d15febd0`; it is
preserved at
`decoded/1.0.2/romfs/bin/font/num_00.bffnt.contents/Sheet_0.bntx`. The pinned
BNTX-Extractor source (commit `2c08e8e55fcc666ba6568a102f36dabd6c584e25`)
identifies one 512×512 `BC4_UNORM` texture. Installed FFmpeg converted the
extractor's DDS to a validated RGBA PNG at
`decoded/1.0.2/romfs/bin/font/num_00.bffnt.contents/Sheet_0.png` (2,863 bytes,
SHA-256 `6752264d3bf6db8bfbfd801306f7328f7c6807dee23bc0757890ccca5222f593`).

The one-to-one structure output is
`decoded/1.0.2/romfs/bin/font/num_00.json` (39,870 bytes, SHA-256
`55df1acc1f720b585cad3fbfccf8af2a13ccab2dcf77f71996d7b0ebe75ef98f`). The
three outputs have source/hash receipts; the content subdirectory retains the
full original `.bffnt` filename before `.contents` and preserves `Sheet_0`.

## Reproduction and results

```powershell
uv run lgpe decode-bffnt --limit 0 --execute --sources-file work/bffnt-verify-sources.txt
uv run lgpe verify --sources-file work/bffnt-verify-sources.txt
uv run lgpe coverage
```

Native Windows execution reported **1 decoded, 0 failed, 0 unknown, 0
unsupported**. Targeted verification registered and verified **3/3 outputs**
with `bad=0`. The source hash remained unchanged. Current source-wide coverage
is **27,824 SCANNED; 21,843 DECODED; 0 FAILED; 5,953 UNKNOWN; 0 PENDING; 28
UNSUPPORTED; 78,504 outputs**.

Only this NX version, one sheet, and the observed section set are supported.
Other platforms or versions, multi-sheet layouts, unhandled sections, and
per-glyph rendering remain UNKNOWN/UNSUPPORTED.
