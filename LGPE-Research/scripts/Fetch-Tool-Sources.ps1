# Public source repos only. NEVER download or bundle prod.keys/title.keys/ROMs.
param([switch]$UpdateExisting)
$ErrorActionPreference='Stop'
$Git = Get-Command git -ErrorAction SilentlyContinue
if (-not $Git) { throw 'Git is unavailable on Windows PATH; use the WSL entry point scripts/Fetch-Tool-Sources.sh.' }
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$Dest = Join-Path $Root 'tools/src'
New-Item -ItemType Directory -Force -Path $Dest | Out-Null
$Repos = [ordered]@{
  'pkNX'='https://github.com/kwsch/pkNX.git'
  'Pawn'='https://github.com/compuphase/pawn.git'
  'Switch-Toolbox'='https://github.com/KillzXGaming/Switch-Toolbox.git'
  'pokedat'='https://github.com/Digote/pokedat.git'
  'read_swsh'='https://github.com/CMahk/read_swsh.git'
  'io_scene_gfbanm'='https://github.com/Shararamosh/io_scene_gfbanm.git'
  'Pokemon-Switch-Model-Importer-Blender'='https://github.com/ChicoEevee/Pokemon-Switch-Model-Importer-Blender.git'
  'vgmstream'='https://github.com/vgmstream/vgmstream.git'
  'wwiser'='https://github.com/bnnm/wwiser.git'
  'Ghidra-Switch-Loader'='https://github.com/Adubbz/Ghidra-Switch-Loader.git'
  'BNTX-Extractor'='https://github.com/aboood40091/BNTX-Extractor.git'
  'pokeldn'='https://github.com/Decryptu/pokeldn.git'
  'pbseqtool'='https://github.com/lincoln-lm/pbseqtool.git'
}
$PinnedCommits = @{
  'pokeldn'='0afe6f61f25464767e55b909eef6b260a372bb34'
  'pbseqtool'='6f122d1b7945797cae472960b798bf28523f8acd'
}
foreach ($Name in $Repos.Keys) {
  $Path = Join-Path $Dest $Name
  if (-not (Test-Path (Join-Path $Path '.git'))) {
    git clone --depth 1 $Repos[$Name] $Path
    if ($LASTEXITCODE -ne 0) { Write-Warning "Failed cloning $Name"; continue }
  } elseif ($UpdateExisting -and -not $PinnedCommits.ContainsKey($Name)) {
    git -C $Path pull --ff-only
    if ($LASTEXITCODE -ne 0) { Write-Warning "Failed updating $Name" }
  }
}
foreach ($Name in $PinnedCommits.Keys) {
  $Path = Join-Path $Dest $Name
  if (Test-Path (Join-Path $Path '.git')) {
    $CurrentCommit = (git -C $Path rev-parse HEAD).Trim()
    if ($CurrentCommit -ne $PinnedCommits[$Name]) {
      git -C $Path fetch --depth 1 origin $PinnedCommits[$Name]
      if ($LASTEXITCODE -ne 0) { throw "Failed fetching pinned commit for $Name" }
      git -C $Path checkout --detach $PinnedCommits[$Name]
      if ($LASTEXITCODE -ne 0) { throw "Failed checking out pinned commit for $Name" }
    }
  }
}
$Provenance = Join-Path $Root 'tools/source-revisions.tsv'
$ProvenanceLines = [System.Collections.Generic.List[string]]::new()
$ProvenanceLines.Add("name`tcommit`tremote")
foreach ($Name in $Repos.Keys) {
  $Path = Join-Path $Dest $Name
  if (Test-Path (Join-Path $Path '.git')) {
    $Hash = git -C $Path rev-parse HEAD
    $ProvenanceLines.Add("$Name`t$Hash`t$($Repos[$Name])")
  }
}
[System.IO.File]::WriteAllText(
  $Provenance,
  (($ProvenanceLines -join "`n") + "`n"),
  [System.Text.UTF8Encoding]::new($false)
)
Write-Host "Pinned source revision list: $Provenance"
