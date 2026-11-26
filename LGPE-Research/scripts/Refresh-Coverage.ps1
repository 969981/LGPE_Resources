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

$StartInfo = [System.Diagnostics.ProcessStartInfo]::new()
$StartInfo.FileName = $Uv
$StartInfo.WorkingDirectory = $ProjectRoot
$StartInfo.UseShellExecute = $false
$StartInfo.RedirectStandardOutput = $true
$StartInfo.RedirectStandardError = $true
foreach ($Argument in @('run', '--project', $ProjectRoot, 'lgpe', 'coverage')) {
    [void]$StartInfo.ArgumentList.Add($Argument)
}

$Process = [System.Diagnostics.Process]::Start($StartInfo)
$StdoutTask = $Process.StandardOutput.ReadToEndAsync()
$StderrTask = $Process.StandardError.ReadToEndAsync()
$Process.WaitForExit()
[Console]::Out.Write($StdoutTask.GetAwaiter().GetResult())
[Console]::Error.Write($StderrTask.GetAwaiter().GetResult())
exit $Process.ExitCode
