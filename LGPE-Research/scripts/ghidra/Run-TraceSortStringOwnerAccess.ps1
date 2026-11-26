param(
    [string]$GhidraHome = 'D:\Tool\ghidra\ghidra_12.2_PUBLIC',
    [string]$JavaHome = 'D:\SDK\Java\OpenJDK25U-jdk_x64_windows_hotspot_25.0.5_8\jdk-25.0.5+8'
)

$ErrorActionPreference = 'Stop'
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$Java = Join-Path $JavaHome 'bin/java.exe'
$UtilityJar = Join-Path $GhidraHome 'Ghidra/Framework/Utility/lib/Utility.jar'
foreach ($Path in @($Java, $UtilityJar)) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "Required local Ghidra/Java file missing: $Path"
    }
}

$Arguments = @(
    '-Djava.system.class.loader=ghidra.GhidraClassLoader',
    '-Dfile.encoding=UTF8', '-Duser.country=US', '-Duser.language=en',
    '-Dsun.java2d.opengl=false', '-Djdk.tls.client.protocols=TLSv1.2,TLSv1.3',
    '-Djava.awt.headless=true', '-Xshare:off', '-XX:+UseCompactObjectHeaders',
    '--enable-native-access=ALL-UNNAMED', '--sun-misc-unsafe-memory-access=allow',
    '-Dsun.java2d.d3d=false', '-Dlog4j.skipJansi=true', '-Xmx2G',
    '-XX:ParallelGCThreads=2', '-XX:CICompilerCount=2',
    '-cp', ('"{0}"' -f $UtilityJar),
    'ghidra.Ghidra', 'ghidra.app.util.headless.AnalyzeHeadless',
    'work\ghidra-main\project', 'LGPE102-main', '-process', 'main',
    '-noanalysis', '-readOnly', '-scriptPath', 'scripts\ghidra',
    '-postScript', 'TraceSortStringOwnerAccess.java',
    '-scriptlog', 'logs\ghidra-sortstring-owner-access-v1-script.log',
    '-log', 'logs\ghidra-sortstring-owner-access-v1-app.log'
)
$StartInfo = [System.Diagnostics.ProcessStartInfo]::new()
$StartInfo.FileName = $Java
$StartInfo.WorkingDirectory = $ProjectRoot
$StartInfo.Arguments = $Arguments -join ' '
$StartInfo.UseShellExecute = $false
$StartInfo.RedirectStandardOutput = $true
$StartInfo.RedirectStandardError = $true

$Process = [System.Diagnostics.Process]::Start($StartInfo)
$StdoutTask = $Process.StandardOutput.ReadToEndAsync()
$StderrTask = $Process.StandardError.ReadToEndAsync()
$Process.WaitForExit()
$Stdout = $StdoutTask.GetAwaiter().GetResult()
$Stderr = $StderrTask.GetAwaiter().GetResult()
[Console]::Out.Write($Stdout)
[Console]::Error.Write($Stderr)
if ($Process.ExitCode -ne 0) { exit $Process.ExitCode }

$RunOutput = $Stdout + [Environment]::NewLine + $Stderr
if ($RunOutput -match 'ERROR REPORT SCRIPT ERROR|DECOMPILE_FAILED') {
    [Console]::Error.WriteLine('Ghidra reported a script or decompiler failure.')
    exit 1
}
if ($Stdout -notmatch 'TraceSortStringOwnerAccess\.java> SUMMARY') {
    [Console]::Error.WriteLine('Ghidra did not emit the expected exact-build summary marker.')
    exit 1
}
if ($RunOutput -notmatch 'Processing read-only project file: /main') {
    [Console]::Error.WriteLine('Ghidra did not confirm that the main database was opened read-only.')
    exit 1
}
[Console]::Out.WriteLine('Verified: exact-build main was processed read-only; script changes cannot be saved.')
exit 0
