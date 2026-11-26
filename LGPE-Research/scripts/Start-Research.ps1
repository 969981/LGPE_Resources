param(
    [int]$Limit = 20,
    [int]$Timeout = 240,
    [switch]$Execute,
    [switch]$FullSha256,
    [string]$Blender,
    [string]$Ffmpeg,
    [string]$Vgmstream
)
$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $false

function Invoke-ResearchProcess {
    param(
        [Parameter(Mandatory)][string]$FilePath,
        [Parameter(Mandatory)][string[]]$ProcessArgs,
        [Parameter(Mandatory)][string]$WorkingDirectory
    )

    $StartInfo = [System.Diagnostics.ProcessStartInfo]::new()
    $StartInfo.FileName = $FilePath
    $StartInfo.WorkingDirectory = $WorkingDirectory
    foreach ($Argument in $ProcessArgs) {
        [void]$StartInfo.ArgumentList.Add($Argument)
    }

    $Process = [System.Diagnostics.Process]::new()
    $Process.StartInfo = $StartInfo
    if (-not $Process.Start()) { throw "Could not start $FilePath." }
    $Process.WaitForExit()
    return $Process.ExitCode
}

$Project = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$GameRoot = Split-Path $Project -Parent
if ([string]::IsNullOrWhiteSpace($env:UV_PROJECT_ENVIRONMENT)) {
    $env:UV_PROJECT_ENVIRONMENT = Join-Path $env:TEMP 'lgpe-research-win-venv'
}

# Keep Git discoverable by Python subprocesses such as shutil.which("git").
$GitCommand = Get-Command git.exe -ErrorAction SilentlyContinue
if (-not $GitCommand) {
    $GitCandidates = @(
        $env:GIT_EXE,
        'D:\Tool\Git\cmd\git.exe',
        'C:\Program Files\Git\cmd\git.exe',
        'C:\Program Files (x86)\Git\cmd\git.exe',
        (Join-Path $env:LOCALAPPDATA 'Programs\Git\cmd\git.exe')
    )
    $GitPath = $GitCandidates |
        Where-Object { -not [string]::IsNullOrWhiteSpace($_) -and (Test-Path -LiteralPath $_ -PathType Leaf) } |
        Select-Object -First 1
    if ($GitPath) {
        $env:PATH = (Split-Path -Parent $GitPath) + [IO.Path]::PathSeparator + $env:PATH
        $GitCommand = Get-Command git.exe -ErrorAction SilentlyContinue
    }
}
if (-not $GitCommand) { throw 'Git was not found on PATH or in the configured local Git locations.' }
$GitDirectory = Split-Path -Parent $GitCommand.Source
if (($env:PATH -split [IO.Path]::PathSeparator) -notcontains $GitDirectory) {
    $env:PATH = $GitDirectory + [IO.Path]::PathSeparator + $env:PATH
}
$NativeExtensions = @(
    $env:PATHEXT -split ';' |
        Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
)
foreach ($Extension in @('.COM', '.EXE', '.BAT', '.CMD')) {
    if ($NativeExtensions -notcontains $Extension) { $NativeExtensions += $Extension }
}
$env:PATHEXT = $NativeExtensions -join ';'

$UvCommand = Get-Command uv -ErrorAction SilentlyContinue
if ($UvCommand) {
    $Uv = $UvCommand.Source
} else {
    $UvFallback = 'D:\SDK\uv-x86_64-pc-windows-msvc\uv.exe'
    if (-not (Test-Path $UvFallback)) { throw 'uv was not found on PATH or at the known local SDK path.' }
    $Uv = $UvFallback
}
Set-Location $Project
Write-Host "Using Windows uv environment: $env:UV_PROJECT_ENVIRONMENT"
Write-Host "Using Git: $($GitCommand.Source)"
$SyncExitCode = Invoke-ResearchProcess -FilePath $Uv -ProcessArgs @('sync') -WorkingDirectory $Project
if ($SyncExitCode -ne 0) { throw "uv sync failed with exit code $SyncExitCode." }
$RunArgs = @('run', 'lgpe', 'run', '--root', $GameRoot, '--limit', "$Limit", '--timeout', "$Timeout")
if ($Execute) { $RunArgs += '--execute' }
if ($FullSha256) { $RunArgs += '--full-sha256' }
if ($Blender) { $RunArgs += @('--blender', $Blender) }
if ($Ffmpeg) { $RunArgs += @('--ffmpeg', $Ffmpeg) }
if ($Vgmstream) { $RunArgs += @('--vgmstream', $Vgmstream) }
$RunExitCode = Invoke-ResearchProcess -FilePath $Uv -ProcessArgs $RunArgs -WorkingDirectory $Project
$TestExitCode = Invoke-ResearchProcess -FilePath $Uv -ProcessArgs @('run', 'python', '-m', 'unittest', 'discover', '-s', 'tests', '-v') -WorkingDirectory $Project
if ($RunExitCode -ne 0) { throw "LGPE research run exited $RunExitCode; unit tests exited $TestExitCode. Inspect manifests and logs." }
if ($TestExitCode -ne 0) { throw 'Unit tests failed.' }
Write-Host 'Completed. Inspect manifests/, decoded/, docs/research/STATUS.md, and tasks/INDEX.md.'
