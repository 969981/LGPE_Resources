param(
    [string]$ProjectRoot = (Join-Path $PSScriptRoot '..'),
    [string]$GameRoot = '',
    [string]$UvPath = ''
)

$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $false
$ProjectRoot = (Resolve-Path -LiteralPath $ProjectRoot).Path
if ([string]::IsNullOrWhiteSpace($GameRoot)) {
    $GameRoot = Split-Path $ProjectRoot -Parent
}
$GameRoot = (Resolve-Path -LiteralPath $GameRoot).Path

if ([string]::IsNullOrWhiteSpace($UvPath)) {
    $UvCommand = Get-Command uv -ErrorAction SilentlyContinue
    if ($UvCommand) {
        $UvPath = $UvCommand.Source
    } else {
        $UvPath = 'D:\SDK\uv-x86_64-pc-windows-msvc\uv.exe'
    }
}
if (-not (Test-Path -LiteralPath $UvPath -PathType Leaf)) {
    throw "uv executable not found: $UvPath"
}

$Arguments = @('run', '--project', $ProjectRoot, 'lgpe', 'map-audio-events', '--root', $GameRoot)
$StartInfo = [System.Diagnostics.ProcessStartInfo]::new()
$StartInfo.FileName = $UvPath
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
