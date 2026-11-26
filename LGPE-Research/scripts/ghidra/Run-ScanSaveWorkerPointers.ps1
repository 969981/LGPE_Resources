param(
    [string]$GhidraHome = 'D:\Tool\ghidra\ghidra_12.2_PUBLIC',
    [string]$JavaHome = 'D:\SDK\Java\OpenJDK25U-jdk_x64_windows_hotspot_25.0.5_8\jdk-25.0.5+8'
)

$ErrorActionPreference = 'Stop'
$ExpectedMainSha256 = '1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8'
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
    '-postScript', 'ScanSaveWorkerPointers.java',
    '-scriptlog', 'logs\ghidra-save-worker-pointers-v1-script.log',
    '-log', 'logs\ghidra-save-worker-pointers-v1-app.log'
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
if ($RunOutput -match 'ERROR REPORT SCRIPT ERROR|SCRIPT ERROR') {
    [Console]::Error.WriteLine('Ghidra reported a script failure.')
    exit 1
}
if ($RunOutput -notmatch 'Processing read-only project file: /main') {
    [Console]::Error.WriteLine('Ghidra did not confirm opening /main read-only.')
    exit 1
}
foreach ($Target in @(
    "7100024d70`tSAVE_WORKER", "7100027200`tSAVE_ID_HELPER",
    "7100027440`tQUEUE_HELPER", "71000275f0`tSTATUS_HELPER"
)) {
    if (-not $RunOutput.Contains("TARGET`t$Target")) {
        [Console]::Error.WriteLine("The trace omitted target $Target")
        exit 1
    }
}
$ExpectedSummaryPattern = 'SUMMARY.*main_sha256=' + [regex]::Escape($ExpectedMainSha256)
if ($RunOutput -notmatch $ExpectedSummaryPattern -or
    $RunOutput -notmatch 'sourceHashUnchanged=true.*readOnly=true') {
    [Console]::Error.WriteLine('The trace did not confirm exact-build identity and source integrity.')
    exit 1
}
$HasQwordSummary = $RunOutput -match 'QWORD_SCAN_SUMMARY.*matches='
$HasImageOffsetSummary = $RunOutput -match 'IMAGE_OFFSET_SCAN_SUMMARY.*matches='
$HasAddressSummary = $RunOutput -match 'ADDRESS_MATERIALIZATION_SUMMARY.*instruction_count='
if (-not $HasQwordSummary -or -not $HasImageOffsetSummary -or -not $HasAddressSummary) {
    [Console]::Error.WriteLine('The trace did not report all pointer/address scan summaries.')
    exit 1
}
[Console]::Out.WriteLine('Verified: exact 1.0.2 main, read-only worker-pointer census, and source integrity.')
exit 0
