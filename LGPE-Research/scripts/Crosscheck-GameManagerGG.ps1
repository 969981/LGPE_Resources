param(
    [string]$ProjectRoot = (Join-Path $PSScriptRoot '..'),
    [string]$GameRoot = ''
)

$ErrorActionPreference = 'Stop'
$ProjectRoot = (Resolve-Path -LiteralPath $ProjectRoot).Path
if ([string]::IsNullOrWhiteSpace($GameRoot)) {
    $GameRoot = Split-Path $ProjectRoot -Parent
}
if (-not (Test-Path -LiteralPath $GameRoot -PathType Container)) {
    throw "Game root does not exist: $GameRoot"
}
$GameRoot = (Resolve-Path -LiteralPath $GameRoot).Path

$DotNetCommand = Get-Command dotnet -ErrorAction SilentlyContinue
if ($DotNetCommand) {
    $DotNetPath = $DotNetCommand.Source
} elseif ($env:ProgramFiles) {
    $DotNetPath = Join-Path $env:ProgramFiles 'dotnet/dotnet.exe'
} else {
    $DotNetPath = $null
}
if ($DotNetPath -and (Test-Path -LiteralPath $DotNetPath -PathType Leaf)) {
    $DotNetDirectory = Split-Path -Parent $DotNetPath
    if ($env:PATH -notlike "*$DotNetDirectory*") {
        $env:PATH = $DotNetDirectory + [System.IO.Path]::PathSeparator + $env:PATH
    }
}
if (($env:PATHEXT -split ';') -notcontains '.EXE') {
    $env:PATHEXT = '.COM;.EXE;.BAT;.CMD;' + $env:PATHEXT
}

$UvCommand = Get-Command uv -ErrorAction SilentlyContinue
if ($UvCommand) {
    $Uv = $UvCommand.Source
} else {
    $Uv = 'D:\SDK\uv-x86_64-pc-windows-msvc\uv.exe'
    if (-not (Test-Path -LiteralPath $Uv -PathType Leaf)) {
        throw 'uv was not found on PATH or at the configured local SDK path.'
    }
}

function Invoke-External {
    param([string]$FileName, [string[]]$Arguments)
    $StartInfo = [System.Diagnostics.ProcessStartInfo]::new()
    $StartInfo.FileName = $FileName
    $StartInfo.WorkingDirectory = $ProjectRoot
    $StartInfo.UseShellExecute = $false
    $StartInfo.RedirectStandardOutput = $true
    $StartInfo.RedirectStandardError = $true
    $StartInfo.Environment['Path'] = $env:Path
    if ($env:DOTNET_ROOT) {
        $StartInfo.Environment['DOTNET_ROOT'] = $env:DOTNET_ROOT
    }
    foreach ($Argument in $Arguments) {
        [void]$StartInfo.ArgumentList.Add($Argument)
    }
    $Process = [System.Diagnostics.Process]::Start($StartInfo)
    $StdoutTask = $Process.StandardOutput.ReadToEndAsync()
    $StderrTask = $Process.StandardError.ReadToEndAsync()
    $Process.WaitForExit()
    return [pscustomobject]@{
        ExitCode = $Process.ExitCode
        Stdout = $StdoutTask.GetAwaiter().GetResult()
        Stderr = $StderrTask.GetAwaiter().GetResult()
    }
}

function Invoke-Uv {
    param([string[]]$Arguments)
    return Invoke-External -FileName $Uv -Arguments $Arguments
}

$WindowsPython = Join-Path $ProjectRoot '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $WindowsPython -PathType Leaf)) {
    $VenvPath = Join-Path $ProjectRoot '.venv'
    $VenvSetup = Invoke-Uv @('venv', '--force', '--python', '3.12', '--no-python-downloads', $VenvPath)
    [Console]::Out.Write($VenvSetup.Stdout)
    [Console]::Error.Write($VenvSetup.Stderr)
    if ($VenvSetup.ExitCode -ne 0) {
        exit $VenvSetup.ExitCode
    }
    $Sync = Invoke-Uv @('sync', '--project', $ProjectRoot)
    [Console]::Out.Write($Sync.Stdout)
    [Console]::Error.Write($Sync.Stderr)
    if ($Sync.ExitCode -ne 0) {
        exit $Sync.ExitCode
    }
}

$WorkerProject = Join-Path $ProjectRoot 'scripts/gamemanagergg-worker/gamemanagergg-worker.csproj'
if (-not $DotNetPath -or -not (Test-Path -LiteralPath $DotNetPath -PathType Leaf)) {
    throw '.NET 10 SDK was not found on PATH or under Program Files.'
}
$Build = Invoke-External -FileName $DotNetPath -Arguments @(
    'build', $WorkerProject, '--configuration', 'Release', '--nologo', '--verbosity', 'quiet'
)
[Console]::Out.Write($Build.Stdout)
[Console]::Error.Write($Build.Stderr)
if ($Build.ExitCode -ne 0) {
    exit $Build.ExitCode
}
$env:LGPE_GAMEMANAGERGG_PREBUILT = '1'

$Result = Invoke-Uv @(
    'run', '--project', $ProjectRoot, 'lgpe', 'crosscheck-gamemanagergg',
    '--root', $GameRoot
)
[Console]::Out.Write($Result.Stdout)
[Console]::Error.Write($Result.Stderr)
exit $Result.ExitCode
