# GFPAK: extraction engineering notes

Source evidence: `bin/archive/.../*.gfpak` visible in uploaded tree; official `pkNX` README says it can extract GFPAK, while Switch-Toolbox documents GFPAK editing. **No actual header bytes are available inside this ZIP.**

Priority test packs in ROMFS `1/`:

- `bin/archive/pokemon/pm0001_00.gfpak`
- `bin/archive/field/area01.gfpak`
- `bin/archive/bag.gfpak`
- `bin/archive/buddy_mood_pikachu.gfpak`

Investigate: signature/version, entry metadata, offsets and lengths, alignment, compression flags, file names/hash mapping, multi-part entries, nested resources, payload compression and the ability to recover original internal relative paths. Preserve bytes if not decodable. Do not bake in offset values from a different game or `GFPAK` variant.

**Adapter target:** a .NET 10 console command (reuse pkNX source with license compliance) `gfpak-cli list <file> --json <manifest>` and `gfpak-cli extract <file> --out <dir> --safe` with stable diagnostics and nonzero failure codes. Design only; this CLI is **not shipped** and Codex must implement it after source inspection.

After obtaining real exported directory, the included implemented command supports:

```powershell
uv run lgpe ingest-container --source 'bin/archive/pokemon/pm0001_00.gfpak' --export-dir 'D:\temp\pkNX_export\pm0001_00' --method 'pkNX GFPAK' --tool-version '<commit>'
```

Containment checks: prohibit `..`, rooted paths, symlink exits, duplicate Windows-normalized names; add max total bytes, per-entry bounds, decompression ratios, checksums, per-file errors and rollback-on-failure. Compare file count/content magic across pkNX vs Toolbox on the same 3 representative archives before extending to all 643 observed packages.
