$code = 'from pathlib import Path,PureWindowsPath; import sys; from lgpe_research.core import PROJECT; from lgpe_research.batch import _ContainedPathResolver; p=PROJECT; r=_ContainedPathResolver(p / "decoded"); e=r.root / "1.0.2" / "romfs" / "bin" / "message" / "asset.json"; print(sys.platform, repr(str(p)), repr(str(r.root)), repr(str(e)), repr(PureWindowsPath(str(e)).drive), repr(PureWindowsPath(str(e)).anchor), repr(PureWindowsPath(str(p)).drive))'
$si = [System.Diagnostics.ProcessStartInfo]::new()
$si.FileName = Join-Path $env:TEMP 'lgpe-research-win-venv\Scripts\python.exe'
$si.WorkingDirectory = 'X:\ROMS\Nintendo Switch\Pokemon\Pokemon Lets Go Pikachu\LGPE-Research'
$si.UseShellExecute = $false
$si.RedirectStandardOutput = $true
$si.RedirectStandardError = $true
[void]$si.ArgumentList.Add('-c')
[void]$si.ArgumentList.Add($code)
$p = [System.Diagnostics.Process]::Start($si)
$o = $p.StandardOutput.ReadToEndAsync()
$e = $p.StandardError.ReadToEndAsync()
$p.WaitForExit()
[Console]::Out.Write($o.GetAwaiter().GetResult())
[Console]::Error.Write($e.GetAwaiter().GetResult())
exit $p.ExitCode
