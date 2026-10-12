#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11,<3.15"
# dependencies = []
# ///
"""One-shot JSON bridge to an independently installed PhotoCraft CLI."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys

COMMANDS = {"info", "commands", "convert", "run", "batch"}
TIMEOUT_SECONDS = 590


def execute(request: object) -> dict[str, object]:
    if not isinstance(request, dict) or set(request) != {"command", "arguments"}:
        raise ValueError("input must contain exactly command and arguments")
    command = request["command"]
    arguments = request["arguments"]
    if not isinstance(command, str) or command not in COMMANDS:
        raise ValueError(f"unsupported PhotoCraft command: {command!r}")
    if not isinstance(arguments, list) or not all(isinstance(arg, str) for arg in arguments):
        raise ValueError("arguments must be an array of strings")
    executable = shutil.which("photocraft-cli")
    if executable is None:
        raise FileNotFoundError("photocraft-cli is not on PATH; install PhotoCraft CLI separately")
    result = subprocess.run(
        [executable, command, *arguments],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=TIMEOUT_SECONDS,
        check=False,
    )
    if result.returncode != 0:
        raise ValueError(
            f"photocraft-cli exited {result.returncode}: {result.stderr.strip() or result.stdout.strip()}"
        )
    records: list[object] = []
    # `info`/`commands` can print multi-line JSON; `run`/`batch` print JSON lines.
    try:
        records.append(json.loads(result.stdout))
    except json.JSONDecodeError:
        for line in result.stdout.splitlines():
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return {
        "ok": True,
        "command": command,
        "messages": result.stdout.splitlines(),
        "records": records,
        "warnings": result.stderr.splitlines(),
    }


if __name__ == "__main__":
    try:
        print(json.dumps(execute(json.load(sys.stdin))))
    except (OSError, TypeError, ValueError, subprocess.TimeoutExpired) as error:
        print(f"photocraft: {error}", file=sys.stderr)
        raise SystemExit(2) from error
