# Tool register / verify upstream versions when installing

No redistributable proprietary binaries, title keys, ROMs, or screenshots are packed here. The `scripts/Fetch-Tool-Sources.ps1` helper clones **public code** into `tools/src/` and writes `tools/source-revisions.tsv` with actual commits; check each tool's `README`, `LICENSE` and run flags at that revision.

| Name | primary use | source | preferred execution |
|---|---|---|---|
| pkNX | LGPE structured game data, GFPAK extraction | https://github.com/kwsch/pkNX | Windows GUI initially; build .NET 10 headless reusable adapter in later tasks |
| CompuPhase Pawn | AMX header reference; dialect compatibility check | https://github.com/compuphase/pawn | Pinned source comparison only; the observed LGPE `defsize` and `hea` values do not satisfy this revision's standard runtime checks |
| Switch-Toolbox | GFPAK, BNTX, models, PTCL etc. | https://github.com/KillzXGaming/Switch-Toolbox | GUI reference / batch importer only after verified |
| pokedat | `.dat + .tbl` text incl. LGPE | https://github.com/Digote/pokedat | `python main.py read <input> <output> --version=LGPE --format=json` as upstream states; inspect exact output layout |
| read_swsh | comparison text decoder LGPE | https://github.com/CMahk/read_swsh | Python experimental cross validation |
| io_scene_gfbanm | Blender skeletal animation import/export | https://github.com/Shararamosh/io_scene_gfbanm | Blender 3.1+ addon version-dependent |
| Pokemon Switch Blender Importer | model import/export for Let's Go | https://github.com/ChicoEevee/Pokemon-Switch-Model-Importer-Blender | Blender addon; review Blender compatibility |
| vgmstream | Wwise WEM/BNK decoder | https://github.com/vgmstream/vgmstream | `vgmstream-cli -i -o <out.wav> <in.wem>` |
| wwiser | Wwise bank metadata/events | https://github.com/bnnm/wwiser | Python/CLI; format-specific research |
| pbseqtool | LGPE `SESD` BSEQ structure to JSON | https://github.com/lincoln-lm/pbseqtool | Pinned at `6f122d1b7945797cae472960b798bf28523f8acd`; `uv run lgpe decode-sequences --execute`; source README grants reuse as a base but no formal LICENSE exists, so source is used from the ignored local checkout and is not redistributed |
| Ghidra Switch Loader | ExeFS NSO/NRO analysis | https://github.com/Adubbz/Ghidra-Switch-Loader | Check extension vs local Ghidra version and Java build requirements |
| Ghidra | binary and source-level analysis | https://github.com/NationalSecurityAgency/ghidra | Existing Windows installation, PyGhidra scripts later |
| PokeLDN | LGPE networking/ExeFS investigation reference and RTTI name helper | https://github.com/Decryptu/pokeldn | Public source is pinned to commit `0afe6f61f25464767e55b909eef6b260a372bb34` (AGPL-3.0); its local helper decompresses an already extracted `0/main` and enumerates RTTI/vtable pointers. Confirm results against this project's exact-build Ghidra database; never fetch ROMs or keys. |

## Explicitly verified documentation

- pkNX's official README states support for LGPE and drag/drop extraction of `gfpak`; `.NET 10` in the current branch.
- Switch-Toolbox's official README enumerates `GFPAK`, `BNTX`, and `PTCL` and its LGPE wiki describes `.gfbmdl` in `.gfpak`.
- pokedat's README explicitly lists `LGPE` and `.dat`+`.tbl` text.
- vgmstream's docs demonstrate `vgmstream-cli` WAV decoding and say it cannot encode/repack original Wwise formats.

## Download/build guardrails

Prefer `git clone` / official project releases after inspecting digital signatures/SHAs. Do not build everything before confirming format needs. First work on read-only source; a GUI “Open” capability does not guarantee a batch or lossless export feature. For each tool maintain in `docs/research/TOOL_REVISIONS.md`:

`name | Git URL | commit | license | OS | runtime | exact invocation | test sample SHA256 | success/failure`.

If Ghidra Switch Loader does not build against the user's Ghidra/JDK version, document version compatibility rather than forcing an upgrade of the existing installation.
