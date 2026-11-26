param(
    [string]$GhidraHome = 'D:\Tool\ghidra\ghidra_12.2_PUBLIC',
    [string]$JavaHome = 'D:\SDK\Java\OpenJDK25U-jdk_x64_windows_hotspot_25.0.5_8\jdk-25.0.5+8'
)

$ErrorActionPreference = 'Stop'
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$Java = Join-Path $JavaHome 'bin/java.exe'
$UtilityJar = Join-Path $GhidraHome 'Ghidra/Framework/Utility/lib/Utility.jar'
$Main = Resolve-Path (Join-Path $ProjectRoot '..\1.0.2\2b7730a9e56498bbafac2002d4908c6b_NCA\0\main')
$ExpectedHash = '1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8'
foreach ($Path in @($Java, $UtilityJar, $Main.Path)) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { throw "Required file missing: $Path" }
}
$Before = (Get-FileHash -LiteralPath $Main.Path -Algorithm SHA256).Hash.ToLowerInvariant()
if ($Before -ne $ExpectedHash) { throw "Exact-build main hash mismatch: $Before" }

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
    '-postScript', 'InspectGfbcolTokenHandler.java',
    '-scriptlog', 'logs\ghidra-gfbcol-token-handler-v2-script.log',
    '-log', 'logs\ghidra-gfbcol-token-handler-v2-app.log'
)
$ScriptLogPath = Join-Path $ProjectRoot 'logs\ghidra-gfbcol-token-handler-v2-script.log'
Remove-Item -LiteralPath $ScriptLogPath -Force -ErrorAction SilentlyContinue
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
$Combined = $Stdout + [Environment]::NewLine + $Stderr
[IO.File]::WriteAllText(
    (Join-Path $ProjectRoot 'logs\ghidra-gfbcol-token-handler-v2.stdout.log'),
    $Combined,
    [Text.UTF8Encoding]::new($false)
)
$After = (Get-FileHash -LiteralPath $Main.Path -Algorithm SHA256).Hash.ToLowerInvariant()
if ($After -ne $Before) { throw 'The original 1.0.2 main changed during read-only analysis.' }
if ($Process.ExitCode -ne 0) { exit $Process.ExitCode }
if ($Combined -match 'ERROR REPORT SCRIPT ERROR|SCRIPT ERROR|DECOMPILE_FAILED') {
    throw 'Ghidra reported a script or decompiler failure.'
}
if ($Combined -notmatch 'InspectGfbcolTokenHandler\.java> SUMMARY.*context_instructions=[1-9][0-9]*.*sourceHashUnchanged=true.*readOnly=true.*semantics=UNKNOWN') {
    throw 'Ghidra did not emit a verified read-only exact-build summary.'
}
foreach ($Offset in @('24f48c', '24f4e4', '24f534', '24f584', '24f5d4', '24f624')) {
    if ($Combined -notmatch "EXPECTED_CALLSITE\s+main\+0x$Offset\s+ghidra_reference=true") {
        throw "Expected raw-confirmed call reference missing at main+0x$Offset."
    }
    if ($Combined -notmatch "CALL_CONTEXT\s+callsite=main\+0x$Offset\s+address=main\+0x$Offset\s+owner=NONE") {
        throw "Expected ownerless direct callsite context missing at main+0x$Offset."
    }
}
if ($Combined -notmatch 'DECOMPILED_BEGIN\s+main\+0xb660\s+chars=[1-9]') {
    throw 'Ghidra did not decompile the expected helper.'
}
Write-Host "Verified: read-only exact-build trace recorded; source SHA-256 unchanged ($After)."
