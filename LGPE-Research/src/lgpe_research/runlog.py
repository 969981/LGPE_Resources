"""Durable append-only lifecycle events for CLI runs."""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _json_value(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


class RunJournal:
    """Append fsynced run events so interrupted work remains discoverable."""

    def __init__(self, project: Path, command: str, arguments: dict[str, Any]):
        self.path = project / "manifests" / "runs.jsonl"
        self.run_id = uuid.uuid4().hex
        self.command = command
        self.arguments = _json_value(arguments)
        self.sequence = 0
        self._append("RUNNING", {"arguments": self.arguments})

    def _append(self, status: str, detail: dict[str, Any] | None = None) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        event = {
            "run_id": self.run_id,
            "sequence": self.sequence,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "command": self.command,
            "status": status,
            "detail": _json_value(detail or {}),
        }
        payload = json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n"
        with self.path.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        self.sequence += 1

    def checkpoint(self, name: str, result: Any) -> None:
        self._append("CHECKPOINT", {"name": name, "result": _json_value(result)})

    def finish(self, exit_code: int, error: str | None = None) -> None:
        status = "COMPLETED" if exit_code == 0 else "FAILED"
        detail: dict[str, Any] = {"exit_code": exit_code}
        if error:
            detail["error"] = error
        self._append(status, detail)
