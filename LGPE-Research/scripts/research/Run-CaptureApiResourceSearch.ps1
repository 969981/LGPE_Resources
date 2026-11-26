param(
    [string]$ProjectRoot = (Join-Path $PSScriptRoot '..\..'),
    [string]$GameRoot,
    [string]$Output
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

if ([string]::IsNullOrWhiteSpace($env:UV_PROJECT_ENVIRONMENT)) {
    $env:UV_PROJECT_ENVIRONMENT = Join-Path $env:TEMP 'lgpe-research-win-venv'
}

$Arguments = [System.Collections.Generic.List[string]]::new()
foreach ($Argument in @('run', '--project', $ProjectRoot, 'lgpe', 'capture-api-resource-search')) {
    $Arguments.Add($Argument)
}
if (-not [string]::IsNullOrWhiteSpace($GameRoot)) {
    $Arguments.Add('--root')
    $Arguments.Add((Resolve-Path -LiteralPath $GameRoot).Path)
}
if (-not [string]::IsNullOrWhiteSpace($Output)) {
    $Arguments.Add('--output')
    $Arguments.Add($Output)
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
