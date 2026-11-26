$ErrorActionPreference = 'Stop'
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$GhidraHome = 'D:\Tool\ghidra\ghidra_12.2_PUBLIC'
$JavaHome = 'D:\SDK\Java\OpenJDK25U-jdk_x64_windows_hotspot_25.0.5_8\jdk-25.0.5+8'
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
    '-postScript', 'InspectBseqDispatchBoundary.java',
    '-scriptlog', 'logs\ghidra-bseq-dispatch-boundary-v1-script.log',
    '-log', 'logs\ghidra-bseq-dispatch-boundary-v1-app.log'
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
    (Join-Path $ProjectRoot 'logs\ghidra-bseq-dispatch-boundary-v1.stdout.log'),
    $Combined,
    [Text.UTF8Encoding]::new($false)
)
$After = (Get-FileHash -LiteralPath $Main.Path -Algorithm SHA256).Hash.ToLowerInvariant()
if ($After -ne $Before) { throw 'The original 1.0.2 main changed during read-only analysis.' }
if ($Process.ExitCode -ne 0) { exit $Process.ExitCode }
if ($Combined -match 'ERROR REPORT SCRIPT ERROR|SCRIPT ERROR') {
    throw 'Ghidra reported a script failure.'
}
if ($Combined -notmatch 'InspectBseqDispatchBoundary\.java> SUMMARY.*read_only_source=true.*read_only_project=true') {
    throw 'Ghidra did not emit the verified read-only exact-build summary marker.'
}
if ($Combined -notmatch 'TARGET_INSTRUCTION.*mnemonic=ret.*bytes_le=c0 03 5f d6') {
    throw 'Ghidra did not verify the RET instruction bytes at the recorded DummyLabel handler.'
}
$EvidenceLines = [System.Collections.Generic.List[string]]::new()
foreach ($Line in ($Stdout -split '\r?\n')) {
    $Marker = 'InspectBseqDispatchBoundary.java> '
    $MarkerAt = $Line.IndexOf($Marker, [StringComparison]::Ordinal)
    if ($MarkerAt -lt 0) { continue }
    $Payload = $Line.Substring($MarkerAt + $Marker.Length) -replace '\s+\(GhidraScript\)\s*$', ''
    if ($Payload -match '^(BUILD|TARGET_INSTRUCTION|TARGET_INCOMING_REF|TARGET_INCOMING_SUMMARY|EXTRA_DISPATCH_SLOT|EXTRA_DISPATCH_SUMMARY|SUMMARY)\t') {
        $EvidenceLines.Add($Payload)
    }
}
$SlotLineCount = @($EvidenceLines | Where-Object { $_ -match '^EXTRA_DISPATCH_SLOT\t' }).Count
$SummaryPattern = '^EXTRA_DISPATCH_SUMMARY\t.*\tinspected=' + $SlotLineCount + '\t'
if (-not ($EvidenceLines | Where-Object { $_ -match '^BUILD\t' }) -or
    -not ($EvidenceLines | Where-Object { $_ -match '^SUMMARY\t' }) -or
    -not ($EvidenceLines | Where-Object { $_ -match $SummaryPattern })) {
    throw 'Ghidra normalized evidence log is missing required records or has an incomplete slot scan.'
}
$Evidence = ($EvidenceLines -join "`n") + "`n"
[IO.File]::WriteAllText(
    (Join-Path $ProjectRoot 'logs\ghidra-bseq-dispatch-boundary-v1-evidence.tsv'),
    $Evidence,
    [Text.UTF8Encoding]::new($false)
)
Write-Host "Verified: BSEQ target bytes and dispatch-table continuation scanned; source SHA-256 unchanged ($After)."
$Stdout -split '\r?\n' |
    Where-Object { $_ -match 'InspectBseqDispatchBoundary\.java> (TARGET_INSTRUCTION|EXTRA_DISPATCH_SUMMARY|SUMMARY)' } |
    Select-Object -Last 3 |
    ForEach-Object { Write-Host $_ }
