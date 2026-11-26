param()

$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$journal = Join-Path $projectRoot 'manifests\runs.jsonl'
$raw = [System.IO.File]::ReadAllBytes($journal)
$beforeHash = [Convert]::ToHexString(
    [System.Security.Cryptography.SHA256]::HashData($raw)
).ToLowerInvariant()
$utf8 = [System.Text.UTF8Encoding]::new($false, $true)
$text = $utf8.GetString($raw)
$lines = [System.Collections.Generic.List[string]]::new()
foreach ($line in $text.Split([char[]]@([char]10), [System.StringSplitOptions]::None)) {
    $lines.Add($line)
}
if ($lines.Count -gt 0 -and $lines[$lines.Count - 1] -eq '') {
    $lines.RemoveAt($lines.Count - 1)
}

$invalid = [System.Collections.Generic.List[int]]::new()
$events = [System.Collections.Generic.List[object]]::new()
for ($i = 0; $i -lt $lines.Count; $i++) {
    $body = $lines[$i].TrimEnd([char]13)
    if ([string]::IsNullOrWhiteSpace($body)) { continue }
    try {
        $events.Add((ConvertFrom-Json -InputObject $body -AsHashtable -ErrorAction Stop))
    }
    catch {
        $invalid.Add($i)
    }
}

if ($invalid.Count -ne 1) {
    throw "Expected exactly one malformed line, found $($invalid.Count); journal left untouched."
}
$index = $invalid[0]
$fragment = $lines[$index].TrimEnd([char]13)
if ($fragment -notmatch '^id": "([0-9a-f]{32})", "sequence": 0, "status": "RUNNING", "timestamp_utc": "([^"]+)"\}$') {
    throw 'Malformed line did not match the known truncated-prefix shape; journal left untouched.'
}
$runId = $Matches[1]
$timestamp = $Matches[2]
$completion = @($events | Where-Object {
    $_.run_id -eq $runId -and $_.sequence -eq 1
})
if ($completion.Count -ne 1 -or $completion[0].command -ne 'verify' -or
    $completion[0].status -ne 'COMPLETED') {
    throw 'No unique matching verify completion exists; journal left untouched.'
}

$fragmentHash = [Convert]::ToHexString(
    [System.Security.Cryptography.SHA256]::HashData($utf8.GetBytes($fragment))
).ToLowerInvariant()
$backupDir = Join-Path $projectRoot 'work\journal-repair-2026-10-30'
[System.IO.Directory]::CreateDirectory($backupDir) | Out-Null
$backup = Join-Path $backupDir 'runs.jsonl.original'
if ([System.IO.File]::Exists($backup)) {
    throw "Exact backup already exists at $backup; journal left untouched."
}
[System.IO.File]::WriteAllBytes($backup, $raw)
$backupHash = [Convert]::ToHexString(
    [System.Security.Cryptography.SHA256]::HashData([System.IO.File]::ReadAllBytes($backup))
).ToLowerInvariant()
if ($backupHash -ne $beforeHash) {
    throw 'Exact backup hash mismatch; journal left untouched.'
}

$replacement = [ordered]@{
    run_id = $runId
    sequence = 0
    timestamp_utc = $timestamp
    command = 'verify'
    status = 'RECOVERED'
    detail = [ordered]@{
        recovery_kind = 'TRUNCATED_JSONL_PREFIX'
        original_line_sha256_utf8_without_terminator = $fragmentHash
        original_fragment = $fragment
        recovered_from_matching_sequence_1 = 'verify / COMPLETED'
        original_detail_arguments = 'UNAVAILABLE_IN_TRUNCATED_PREFIX'
        original_status = 'RUNNING'
    }
}
$lines[$index] = ConvertTo-Json -InputObject $replacement -Compress -Depth 8
$newText = [string]::Join("`n", $lines) + "`n"
$temp = "$journal.repair-tmp"
[System.IO.File]::WriteAllText($temp, $newText, $utf8)
[System.IO.File]::Move($temp, $journal, $true)

try {
    $validCount = 0
    foreach ($line in [System.IO.File]::ReadAllLines($journal, $utf8)) {
        if ([string]::IsNullOrWhiteSpace($line)) { continue }
        $null = ConvertFrom-Json -InputObject $line -AsHashtable -ErrorAction Stop
        $validCount++
    }
}
catch {
    [System.IO.File]::WriteAllBytes($journal, $raw)
    throw "Repaired journal validation failed; exact original restored. $($_.Exception.Message)"
}

$afterHash = [Convert]::ToHexString(
    [System.Security.Cryptography.SHA256]::HashData([System.IO.File]::ReadAllBytes($journal))
).ToLowerInvariant()
$repair = [ordered]@{
    journal = 'manifests/runs.jsonl'
    original_sha256 = $beforeHash
    original_backup = 'work/journal-repair-2026-10-30/runs.jsonl.original'
    backup_sha256 = $backupHash
    repaired_sha256 = $afterHash
    line_number = $index + 1
    malformed_fragment_sha256_utf8_without_terminator = $fragmentHash
    recovered_run_id = $runId
    inferred_command = 'verify (from matching sequence 1 COMPLETED event)'
    unavailable = 'original detail.arguments prefix was truncated'
    valid_jsonl_records = $validCount
}
$repairPath = Join-Path $backupDir 'repair.json'
[System.IO.File]::WriteAllText(
    $repairPath,
    (ConvertTo-Json -InputObject $repair -Depth 5),
    $utf8
)

Write-Output "original_sha256=$beforeHash"
Write-Output "backup_sha256=$backupHash"
Write-Output "repaired_sha256=$afterHash"
Write-Output "recovered_line=$($index + 1) run_id=$runId fragment_sha256=$fragmentHash"
Write-Output "valid_jsonl_records=$validCount"
