# Initialize repository safely, outside the 1.0.2 game files.
$ErrorActionPreference='Stop'
$Project=(Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location $Project
if (-not (Test-Path '.git')) { git init }
Write-Host 'Checking ignores for source keys and game files...'
git check-ignore 'prod.keys' 'title.keys' 'some.nsp' 'some.gfpak' | Out-Host
git add README.md AGENTS.md CODEX_MASTER_PROMPT.md .gitignore .python-version pyproject.toml configs src scripts tests tools docs tasks
Write-Host 'Review proposed changes: git status --short'
git status --short
Write-Host 'No automatic commit. Inspect staged files before committing.'
