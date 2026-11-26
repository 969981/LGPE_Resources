param(
    [string]$ProjectRoot = (Join-Path $PSScriptRoot '..')
)

$ErrorActionPreference = 'Stop'
$ProjectRoot = (Resolve-Path -LiteralPath $ProjectRoot).Path

$UvCommand = Get-Command uv -ErrorAction SilentlyContinue
if ($UvCommand) {
    $Uv = $UvCommand.Source
} else {
    $Uv = 'D:\SDK\uv-x86_64-pc-windows-msvc\uv.exe'
    if (-not (Test-Path -LiteralPath $Uv -PathType Leaf)) {
        throw 'uv was not found on PATH or at the configured local SDK path.'
    }
}

$GitCommand = Get-Command git.exe -ErrorAction SilentlyContinue
if (-not $GitCommand) {
    $GitCandidates = [System.Collections.Generic.List[string]]::new()
    foreach ($Candidate in @(
        $env:GIT_EXE,
        'D:\Tool\Git\cmd\git.exe',
        'C:\Program Files\Git\cmd\git.exe',
        'C:\Program Files (x86)\Git\cmd\git.exe',
        (Join-Path $env:LOCALAPPDATA 'Programs\Git\cmd\git.exe')
    )) {
        if (-not [string]::IsNullOrWhiteSpace($Candidate) -and
            (Test-Path -LiteralPath $Candidate -PathType Leaf)) {
            $GitCandidates.Add($Candidate)
        }
    }
    if ($GitCandidates.Count -gt 0) {
        $GitDirectory = Split-Path -Parent $GitCandidates[0]
        $env:PATH = $GitDirectory + [IO.Path]::PathSeparator + $env:PATH
        $GitCommand = Get-Command git.exe -ErrorAction SilentlyContinue
    }
}
if (-not $GitCommand) {
    throw 'Git was not found on PATH or in the configured local Git locations.'
}
Write-Host "Using Git: $($GitCommand.Source)"

$NativeExtensions = @(
    $env:PATHEXT -split ';' |
        Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
)
foreach ($Extension in @('.COM', '.EXE', '.BAT', '.CMD')) {
    if ($NativeExtensions -notcontains $Extension) {
        $NativeExtensions += $Extension
    }
}
$env:PATHEXT = $NativeExtensions -join ';'

if ([string]::IsNullOrWhiteSpace($env:UV_PROJECT_ENVIRONMENT)) {
    $env:UV_PROJECT_ENVIRONMENT = Join-Path $env:TEMP 'lgpe-research-win-venv'
}

$Arguments = [System.Collections.Generic.List[string]]::new()
foreach ($Argument in @(
    'run', '--project', $ProjectRoot,
    'python', '-m', 'unittest', 'discover', '-s', 'tests'
)) {
    $Arguments.Add($Argument)
}

$StartInfo = [System.Diagnostics.ProcessStartInfo]::new()
$StartInfo.FileName = $Uv
$StartInfo.WorkingDirectory = $ProjectRoot
$StartInfo.UseShellExecute = $false
$StartInfo.RedirectStandardOutput = $true
$StartInfo.RedirectStandardError = $true
foreach ($Argument in $Arguments) {
    [void]$StartInfo.ArgumentList.Add($Argument)
}

$Process = [System.Diagnostics.Process]::Start($StartInfo)
$StdoutTask = $Process.StandardOutput.ReadToEndAsync()
$StderrTask = $Process.StandardError.ReadToEndAsync()
$Process.WaitForExit()
[Console]::Out.Write($StdoutTask.GetAwaiter().GetResult())
[Console]::Error.Write($StderrTask.GetAwaiter().GetResult())
exit $Process.ExitCode
