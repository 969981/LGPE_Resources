# Windows / uv / WSL / Docker guide

## Windows PowerShell 7 (primary)

The parent directory of the repository must be the Pokémon Let's Go Pikachu game root. Always quote the X: paths and check `uv --version`, `dotnet --version` and `git --version` before installing duplicates.

```powershell
cd 'X:\ROMS\Nintendo Switch\Pokemon\Pokemon Lets Go Pikachu\LGPE-Research'
uv sync
uv run lgpe doctor
uv run lgpe tree-catalog
uv run lgpe scan
uv run lgpe plan
```

`uv sync` installs only the local project, not GUI converters; those must be installed or compiled separately, and are registered in `tools/TOOLS.md`. Use `--root 'D:\...\Pokemon Lets Go Pikachu'` if the game directory is somewhere else.

## WSL2 Ubuntu 24.04 (optional)

```powershell
wsl -- bash -lc 'wslpath "X:\ROMS\Nintendo Switch\Pokemon\Pokemon Lets Go Pikachu"'
```

If the drive is not mounted, check `ls /mnt/x` and Windows WSL automount settings; do not assume that `/mnt/x` exists. If it is available:

```bash
cd '/mnt/x/ROMS/Nintendo Switch/Pokemon/Pokemon Lets Go Pikachu/LGPE-Research'
uv sync
uv run lgpe doctor --root '/mnt/x/ROMS/Nintendo Switch/Pokemon/Pokemon Lets Go Pikachu'
```

Avoid running disk-heavy hash scans in both Windows and WSL simultaneously. Use Windows for pkNX/Toolbox GUI and Ghidra; use WSL only for tasks with real native tooling advantage.

## Docker (optional, not required)

For isolated, read-only scanning, the game dump can be mounted `:ro`. Mount a separate writable project directory; this example assumes Git Bash, Bash or a shell that supports `-v` quoting as written. Adjust Windows volume syntax to the Docker host before use.

```bash
docker run --rm -v '/absolute/game/root:/game:ro' -v '/absolute/LGPE-Research:/work' -w /work ghcr.io/astral-sh/uv:python3.12-bookworm uv run lgpe scan --root /game
```

Never start a full scan inside a container with an empty `/game` bind mount and mistake zero results for a completed job. Do not expose prod.keys or game dumps through container images, caches or GitHub Actions.

## Local environment evidence (2026-10-28)

- The current `X:` drive resolves in Windows to `\\192.168.1.5\j\ROMS\...`; Windows Python/uv can access it. WSL2 has no `/mnt/x`, and `wslpath` does not map this drive. A DrvFS mount attempt could not proceed because the WSL user has no passwordless sudo. Use the Windows toolchain for this mapped share unless its owner configures a WSL mount.
- PowerShell 7.6.9 is installed at `D:\Tool\PowerShell\7\pwsh.exe`. The WSL-launched PowerShell process did not inherit the Windows tool PATH, so this run invoked uv/Git by their exact executable paths. In a native Windows PowerShell session, `Get-Command` is the preferred lookup.
- Verified: CPython 3.12.14, uv 0.11.25, Git 2.45.2, .NET 10.0.403, Ghidra install folder `ghidra_12.2_PUBLIC`, Blender 5.1.2, and FFmpeg 8.0.1. `lgpe doctor` reports `vgmstream-cli` absent from PATH; T09 will verify whether a local binary exists elsewhere or install a pinned upstream build.
- `uv` reports that inherited `SSL_CERT_DIR=D:\SDK\anaconda3\Library\ssl\certs` is invalid and ignores it. `uv sync`, scan, plan, comparison, and tests all completed successfully despite that warning.
