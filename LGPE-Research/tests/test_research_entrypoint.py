import unittest
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]


class ResearchEntrypointTests(unittest.TestCase):
    def test_windows_entrypoint_isolates_uv_and_git_environment_before_sync(self):
        script = (PROJECT / "scripts" / "Start-Research.ps1").read_text(encoding="utf-8")

        environment_setup = script.index("$env:UV_PROJECT_ENVIRONMENT = Join-Path $env:TEMP")
        git_setup = script.index("$GitCommand = Get-Command git.exe")
        pathext_setup = script.index("$env:PATHEXT = $NativeExtensions -join ';'")
        first_uv_sync = script.index("-ProcessArgs @('sync')")

        self.assertLess(environment_setup, first_uv_sync)
        self.assertLess(git_setup, first_uv_sync)
        self.assertLess(pathext_setup, first_uv_sync)
        self.assertIn("D:\\Tool\\Git\\cmd\\git.exe", script)
        self.assertIn("Join-Path $env:LOCALAPPDATA 'Programs\\Git\\cmd\\git.exe'", script)


if __name__ == "__main__":
    unittest.main()
