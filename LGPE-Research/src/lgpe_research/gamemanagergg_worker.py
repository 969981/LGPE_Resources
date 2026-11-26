"""Run pinned pkNX GameManagerGG as a read-only structured-data cross-check."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from .core import PROJECT, source_dirs

PKNX_COMMIT = "d191cd0e5c05f2af81d9a41c1f1d82e6621b351a"


def _find_dotnet() -> tuple[str, bool]:
    """Find dotnet; the boolean indicates Windows dotnet.exe invoked from WSL."""
    dotnet = shutil.which("dotnet")
    if dotnet:
        return dotnet, False
    dotnet_exe = shutil.which("dotnet.exe")
    if dotnet_exe:
        return dotnet_exe, True

    if os.name == "nt":
        where = shutil.which("where.exe") or str(Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32/where.exe")
        found = subprocess.run(
            [where, "dotnet"], capture_output=True, text=True, encoding="utf-8", errors="replace", check=False
        )
        candidates = [line.strip() for line in found.stdout.splitlines() if line.strip().lower().endswith("dotnet.exe")]
        for variable in ("DOTNET_ROOT", "DOTNET_ROOT_X64", "ProgramW6432", "ProgramFiles"):
            base = os.environ.get(variable)
            if base:
                candidates.append(str(Path(base) / "dotnet/dotnet.exe"))
        for candidate in candidates:
            if Path(candidate).is_file():
                return candidate, False

    cmd = shutil.which("cmd.exe")
    wslpath = shutil.which("wslpath")
    if cmd and wslpath:
        found = subprocess.run(
            [cmd, "/d", "/c", "where", "dotnet"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
            check=False,
        )
        candidates = [line.strip() for line in found.stdout.splitlines() if line.strip().lower().endswith("dotnet.exe")]
        for candidate in candidates:
            converted = subprocess.run(
                [wslpath, "-u", candidate], capture_output=True, text=True, encoding="utf-8", check=True
            ).stdout.strip()
            if Path(converted).is_file():
                return converted, True
    raise FileNotFoundError(".NET 10 SDK/runtime not found (checked dotnet, dotnet.exe, and Windows PATH).")


def _arg_path(path: Path, windows_dotnet: bool) -> str:
    resolved = str(path.resolve())
    if not windows_dotnet or os.name == "nt":
        return resolved
    wslpath = shutil.which("wslpath")
    if not wslpath:
        raise FileNotFoundError("wslpath is required to pass workspace paths to Windows dotnet.exe.")
    result = subprocess.run(
        [wslpath, "-w", resolved], capture_output=True, text=True, encoding="utf-8", check=True
    )
    return result.stdout.strip()


def _pknx_revision(project: Path) -> str:
    repo = project / "tools/src/pkNX"
    result = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    commit = result.stdout.strip()
    if commit != PKNX_COMMIT:
        raise ValueError(f"Expected pinned pkNX commit {PKNX_COMMIT}, found {commit}.")
    dirty = subprocess.run(
        ["git", "-C", str(repo), "status", "--porcelain", "--untracked-files=no"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    ).stdout.strip()
    if dirty:
        raise ValueError("Pinned pkNX source has tracked local modifications; refusing a parity run.")
    return commit


def run_gamemanagergg_worker(root: Path, project: Path = PROJECT) -> dict:
    """Build and run the pinned C# worker; it hashes mapped inputs before and after parsing."""
    dirs = source_dirs(root)
    romfs, exefs = dirs["romfs"].resolve(), dirs["exefs"].resolve()
    if not romfs.is_dir() or not exefs.is_dir():
        raise FileNotFoundError(f"Expected local ExeFS and RomFS: {exefs}; {romfs}")
    project = project.resolve()
    commit = _pknx_revision(project)
    run_id = "run-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output = project / "work/gamemanagergg" / run_id
    worker_project = project / "scripts/gamemanagergg-worker/gamemanagergg-worker.csproj"
    if not worker_project.is_file():
        raise FileNotFoundError(worker_project)

    dotnet, windows_dotnet = _find_dotnet()
    prebuilt = os.environ.get("LGPE_GAMEMANAGERGG_PREBUILT") == "1"
    if prebuilt:
        worker_dll = worker_project.parent / "bin/Release/net10.0/gamemanagergg-worker.dll"
        if not worker_dll.is_file():
            return {"status": "FAILED", "exitCode": 4, "outputDirectory": str(output),
                    "error": "prebuilt worker DLL is missing; run scripts/Crosscheck-GameManagerGG.ps1 or unset LGPE_GAMEMANAGERGG_PREBUILT"}
        path_args = [_arg_path(path, windows_dotnet) for path in (worker_dll, romfs, exefs, output, project)]
        command = [dotnet, path_args[0], path_args[1], path_args[2], path_args[3], path_args[4], commit]
    else:
        path_args = [_arg_path(path, windows_dotnet) for path in (worker_project, romfs, exefs, output, project)]
        command = [dotnet, "run", "--project", path_args[0], "--configuration", "Release", "--",
                   path_args[1], path_args[2], path_args[3], path_args[4], commit]
    environment = os.environ.copy()
    if os.name == "nt":
        sdk_dir = os.path.dirname(dotnet)
        path_key = next((key for key in environment if key.casefold() == "path"), "PATH")
        environment[path_key] = sdk_dir + os.pathsep + environment.get(path_key, "")
        pathext_key = next((key for key in environment if key.casefold() == "pathext"), "PATHEXT")
        extensions = [value for value in environment.get(pathext_key, "").split(os.pathsep) if value]
        if ".EXE" not in {value.upper() for value in extensions}:
            environment[pathext_key] = ".COM;.EXE;.BAT;.CMD;" + environment.get(pathext_key, "")
        runtime_lookup = subprocess.run(
            ["dotnet", "--list-runtimes"], capture_output=True, text=True,
            encoding="utf-8", errors="replace", env=environment, check=False,
        )
        if runtime_lookup.returncode:
            return {
                "status": "FAILED",
                "exitCode": 4,
                "outputDirectory": str(output),
                "error": "dotnet.exe was found, but the build target's command name is not resolvable from the worker environment",
                "dotnetPath": dotnet,
                "sdkDirectory": sdk_dir,
                "pathKey": path_key,
                "pathPrefix": environment.get(path_key, "").split(os.pathsep)[:4],
                "runtimeLookupStderr": runtime_lookup.stderr[-1000:],
            }
    process = None
    launch_error = None
    try:
        process = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=1800,
            check=False,
            env=environment,
        )
    except (OSError, subprocess.SubprocessError) as error:
        launch_error = f"{type(error).__name__}: {error}"

    if launch_error:
        return {"status": "FAILED", "exitCode": 4, "outputDirectory": str(output), "error": launch_error}
    assert process is not None
    receipt_path = output / "receipt.json"
    receipt = None
    if receipt_path.is_file():
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if receipt is not None and not receipt.get("sourceUnchanged", False):
        return {"status": "SOURCE_CHANGED", "exitCode": 5, "outputDirectory": str(output),
                "changedPaths": receipt.get("changedPaths", []),
                "inputFiles": receipt.get("inputFileCount", 0)}
    if process.returncode:
        return {
            "status": "FAILED",
            "exitCode": 4,
            "outputDirectory": str(output),
            "workerExitCode": process.returncode,
            "stdoutTail": process.stdout[-3000:],
            "stderrTail": process.stderr[-3000:],
        }
    if receipt is None:
        return {"status": "FAILED", "exitCode": 4, "outputDirectory": str(output),
                "error": "worker succeeded without writing receipt.json"}
    return {
        "status": "CROSSCHECKED",
        "exitCode": 0,
        "outputDirectory": str(output),
        "pknxCommit": commit,
        "sourceUnchanged": receipt["sourceUnchanged"],
        "inputFiles": receipt["inputFileCount"],
        "outputCounts": receipt["outputCounts"],
        "roundTrip": receipt["roundTrip"],
    }
