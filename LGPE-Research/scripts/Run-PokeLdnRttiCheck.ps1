[CmdletBinding()]
param(
  [string]$GhidraHome = 'D:\Tool\ghidra\ghidra_12.2_PUBLIC',
  [string]$ProjectName = 'LGPE102-main',
  [ValidateSet('nn::pia', 'nn::nex')]
  [string]$Prefix = 'nn::pia'
)

$ErrorActionPreference = 'Stop'
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$Headless = Join-Path $GhidraHome 'support/analyzeHeadless.bat'
$ProjectDir = Join-Path $Root 'work/ghidra-main/project'
$ScriptPath = Join-Path $Root 'scripts/ghidra'
$LogDir = Join-Path $Root 'logs'
if ($Prefix -eq 'nn::nex') {
  $Inventory = Join-Path $Root 'work/pokeldn/rtti-nex-ghidra.tsv'
  $LogStem = 'ghidra-pokeldn-nex-rtti'
} else {
  $Inventory = Join-Path $Root 'work/pokeldn/rtti-ghidra.tsv'
  $LogStem = 'ghidra-pokeldn-rtti'
}
$ScriptLog = Join-Path $LogDir "$LogStem-script.log"
$AppLog = Join-Path $LogDir "$LogStem.log"
$TempInventory = Join-Path $env:TEMP ("lgpe-rtti-{0}.tsv" -f [guid]::NewGuid().ToString('N'))

foreach ($RequiredPath in @($Headless, $ProjectDir, $ScriptPath, $Inventory)) {
  if (-not (Test-Path -LiteralPath $RequiredPath)) {
    throw "Required RTTI check input not found: $RequiredPath"
  }
}
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
Copy-Item -LiteralPath $Inventory -Destination $TempInventory

try {
  & $Headless $ProjectDir $ProjectName `
    -process main -noanalysis `
    -scriptPath $ScriptPath `
    -postScript VerifyPokeLdnRtti.java $TempInventory `
    -scriptlog $ScriptLog -log $AppLog
  if ($LASTEXITCODE -ne 0) {
    throw "Ghidra RTTI verification failed with exit code $LASTEXITCODE; see $AppLog"
  }
  Write-Host "Ghidra RTTI check succeeded. Summary: $ScriptLog"
} finally {
  Remove-Item -LiteralPath $TempInventory -Force -ErrorAction SilentlyContinue
}
