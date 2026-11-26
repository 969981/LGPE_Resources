$ErrorActionPreference = 'Stop'
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$GhidraHome = 'D:\Tool\ghidra\ghidra_12.2_PUBLIC'
$JavaHome = 'D:\SDK\Java\OpenJDK25U-jdk_x64_windows_hotspot_25.0.5_8\jdk-25.0.5+8'
$Java = Join-Path $JavaHome 'bin/java.exe'
$UtilityJar = Join-Path $GhidraHome 'Ghidra/Framework/Utility/lib/Utility.jar'
$Main = (Resolve-Path (Join-Path $ProjectRoot '..\1.0.2\2b7730a9e56498bbafac2002d4908c6b_NCA\0\main')).Path
$ExpectedHash = '1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8'
foreach ($Path in @($Java, $UtilityJar, $Main)) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "Required local Ghidra/Java/main file missing: $Path"
    }
}

$Before = (Get-FileHash -LiteralPath $Main -Algorithm SHA256).Hash.ToLowerInvariant()
if ($Before -ne $ExpectedHash) { throw "Exact-build main hash mismatch: $Before" }

$Arguments = [System.Collections.Generic.List[string]]::new()
foreach ($Argument in @(
    '-Djava.system.class.loader=ghidra.GhidraClassLoader',
    '-Dfile.encoding=UTF8', '-Duser.country=US', '-Duser.language=en',
    '-Dsun.java2d.opengl=false', '-Djdk.tls.client.protocols=TLSv1.2,TLSv1.3',
    '-Djava.awt.headless=true', '-Xshare:off', '-XX:+UseCompactObjectHeaders',
    '--enable-native-access=ALL-UNNAMED', '--sun-misc-unsafe-memory-access=allow',
    '-Dsun.java2d.d3d=false', '-Dlog4j.skipJansi=true', '-Xmx2G',
    '-XX:ParallelGCThreads=2', '-XX:CICompilerCount=2',
    '-cp', $UtilityJar,
    'ghidra.Ghidra', 'ghidra.app.util.headless.AnalyzeHeadless',
    'work\ghidra-main\project', 'LGPE102-main', '-process', 'main',
    '-noanalysis', '-readOnly', '-scriptPath', 'scripts\ghidra',
    '-postScript', 'InspectScriptRegistryOperandScan.java',
    '-scriptlog', 'logs\ghidra-script-registry-operands-v1-script.log',
    '-log', 'logs\ghidra-script-registry-operands-v1-app.log'
)) { $Arguments.Add($Argument) }

$StartInfo = [System.Diagnostics.ProcessStartInfo]::new()
$StartInfo.FileName = $Java
$StartInfo.WorkingDirectory = $ProjectRoot
$StartInfo.UseShellExecute = $false
$StartInfo.RedirectStandardOutput = $true
$StartInfo.RedirectStandardError = $true
foreach ($Argument in $Arguments) { [void]$StartInfo.ArgumentList.Add($Argument) }
$Process = [System.Diagnostics.Process]::Start($StartInfo)
$StdoutTask = $Process.StandardOutput.ReadToEndAsync()
$StderrTask = $Process.StandardError.ReadToEndAsync()
$Process.WaitForExit()
$Stdout = $StdoutTask.GetAwaiter().GetResult()
$Stderr = $StderrTask.GetAwaiter().GetResult()
$Combined = $Stdout + [Environment]::NewLine + $Stderr
[IO.File]::WriteAllText(
    (Join-Path $ProjectRoot 'logs\ghidra-script-registry-operands-v1.stdout.log'),
    $Combined,
    [Text.UTF8Encoding]::new($false)
)

$After = (Get-FileHash -LiteralPath $Main -Algorithm SHA256).Hash.ToLowerInvariant()
if ($After -ne $Before) { throw 'The original 1.0.2 main changed during analysis.' }
if ($Process.ExitCode -ne 0) { exit $Process.ExitCode }
if ($Combined -match 'ERROR REPORT SCRIPT ERROR|SCRIPT ERROR|DECOMPILE_FAILED') {
    throw 'Ghidra reported an operand-scan script or decompiler failure.'
}
if ($Combined -notmatch 'InspectScriptRegistryOperandScan\.java> SUMMARY.*readOnlySource=true.*readOnlyProject=true') {
    throw 'Ghidra did not emit the verified read-only exact-build summary.'
}
if ($Combined -notmatch 'Processing read-only project file: /main') {
    throw 'Ghidra did not confirm read-only processing of /main.'
}
if ($Combined -notmatch 'Discarding changes to the following read-only file: /main') {
    throw 'Ghidra did not confirm discarding temporary function-boundary changes.'
}
Write-Host "Verified: script registry operand scan completed; main SHA-256 unchanged ($After)."
$Stdout -split '\r?\n' |
    Where-Object { $_ -match 'InspectScriptRegistryOperandScan\.java> SUMMARY' } |
    Select-Object -Last 1 |
    ForEach-Object { Write-Host $_ }

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
$UvInfo = [System.Diagnostics.ProcessStartInfo]::new()
$UvInfo.FileName = $Uv
$UvInfo.WorkingDirectory = $ProjectRoot
$UvInfo.UseShellExecute = $false
$UvInfo.RedirectStandardOutput = $true
$UvInfo.RedirectStandardError = $true
foreach ($Argument in @(
    'run', '--project', $ProjectRoot, 'lgpe', 'script-registry-operand-scan'
)) { [void]$UvInfo.ArgumentList.Add($Argument) }
$UvProcess = [System.Diagnostics.Process]::Start($UvInfo)
$UvStdoutTask = $UvProcess.StandardOutput.ReadToEndAsync()
$UvStderrTask = $UvProcess.StandardError.ReadToEndAsync()
$UvProcess.WaitForExit()
$UvStdout = $UvStdoutTask.GetAwaiter().GetResult()
$UvStderr = $UvStderrTask.GetAwaiter().GetResult()
[Console]::Out.Write($UvStdout)
[Console]::Error.Write($UvStderr)
if ($UvProcess.ExitCode -ne 0) { throw "Operand-scan manifest builder exited $($UvProcess.ExitCode)." }
