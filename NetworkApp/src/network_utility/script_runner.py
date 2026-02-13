from __future__ import annotations

import os
import subprocess
import sys


def build_command(path: str) -> list[str] | None:
    ext = os.path.splitext(path)[1].lower()
    if ext == ".py":
        return [sys.executable, path]
    if ext in {".bat", ".cmd"}:
        if os.name != "nt":
            return None
        return ["cmd", "/c", path]
    if ext in {".bash", ".sh"}:
        return ["bash", path]
    return None


def run_script(path: str) -> tuple[int | None, str, str, str | None]:
    command = build_command(path)
    if command is None:
        ext = os.path.splitext(path)[1].lower()
        if ext in {".bat", ".cmd"} and os.name != "nt":
            return None, "", "", ".bat/.cmd scripts can only run on Windows"
        return None, "", "", f"Unsupported extension: {ext}"

    try:
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        return result.returncode, result.stdout, result.stderr, None
    except FileNotFoundError as exc:
        return None, "", "", f"Missing runtime for script: {exc}"
    except Exception as exc:  # noqa: BLE001
        return None, "", "", f"Failed running script: {exc}"
