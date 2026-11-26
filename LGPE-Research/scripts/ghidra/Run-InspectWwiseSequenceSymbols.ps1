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
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "Required local Ghidra/Java/main file missing: $Path"
    }
}
$Before = (Get-FileHash -LiteralPath $Main.Path -Algorithm SHA256).Hash.ToLowerInvariant()
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
    '-postScript', 'InspectWwiseSequenceSymbols.java',
    '-scriptlog', 'logs\ghidra-wwise-sequence-symbols-v1-script.log',
    '-log', 'logs\ghidra-wwise-sequence-symbols-v1-app.log'
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
[Console]::Out.Write($Stdout)
[Console]::Error.Write($Stderr)
$Combined = $Stdout + [Environment]::NewLine + $Stderr
[IO.File]::WriteAllText(
    (Join-Path $ProjectRoot 'logs\ghidra-wwise-sequence-symbols-v1.stdout.log'),
    $Combined,
    [Text.UTF8Encoding]::new($false)
)
$After = (Get-FileHash -LiteralPath $Main.Path -Algorithm SHA256).Hash.ToLowerInvariant()
if ($After -ne $Before) { throw 'The original 1.0.2 main changed during read-only analysis.' }
if ($Process.ExitCode -ne 0) { exit $Process.ExitCode }
if ($Combined -match 'ERROR REPORT SCRIPT ERROR|SCRIPT ERROR|DECOMPILE_FAILED') {
    throw 'Ghidra reported a script or decompiler failure.'
}
if ($Combined -notmatch 'InspectWwiseSequenceSymbols\.java> SUMMARY.*semantics=UNKNOWN.*read_only=true') {
    throw 'Ghidra did not emit the verified read-only exact-build summary marker.'
}
Write-Host "Verified: read-only exact-build trace completed; source SHA-256 unchanged ($After)."
