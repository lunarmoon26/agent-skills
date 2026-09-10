#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11,<3.15"
# dependencies = [
#   "Pillow==12.3.0",
# ]
# ///
"""JSON-in/JSON-out bridge for the photo-processing CLI."""

from __future__ import annotations

import io
import json
import sys
from contextlib import redirect_stdout

import photo

COMMANDS = {
    "flood-fill",
    "inspect",
    "key-color",
    "key-luminance",
    "mask",
    "resize",
    "sprite-grid",
    "trim",
}


def read_request() -> tuple[str, list[str]]:
    request = json.load(sys.stdin)
    if not isinstance(request, dict) or set(request) != {"command", "arguments"}:
        raise ValueError("input must contain exactly command and arguments")
    command = request["command"]
    arguments = request["arguments"]
    if command not in COMMANDS:
        raise ValueError(f"unsupported photo command: {command!r}")
    if not isinstance(arguments, list) or not all(isinstance(argument, str) for argument in arguments):
        raise ValueError("arguments must be an array of strings")
    return command, arguments


def main() -> None:
    command, arguments = read_request()
    original_argv = sys.argv
    captured = io.StringIO()
    try:
        sys.argv = [str(photo.__file__), command, *arguments]
        with redirect_stdout(captured):
            photo.main()
    finally:
        sys.argv = original_argv

    messages = captured.getvalue().splitlines()
    records: list[object] = []
    for message in messages:
        try:
            records.append(json.loads(message))
        except json.JSONDecodeError:
            continue
    print(json.dumps({"ok": True, "command": command, "messages": messages, "records": records}))


if __name__ == "__main__":
    try:
        main()
    except (json.JSONDecodeError, OSError, TypeError, ValueError) as error:
        print(f"photo_process: {error}", file=sys.stderr)
        raise SystemExit(2) from error
