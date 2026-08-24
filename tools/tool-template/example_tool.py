from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def parse_flag_value(raw: str) -> Any:
    text = str(raw).strip()
    lowered = text.lower()
    if lowered in {"true", "yes"}:
        return True
    if lowered in {"false", "no"}:
        return False
    if lowered in {"null", "none"}:
        return None
    if text.startswith("{") or text.startswith("["):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return text
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def parse_invocation(argv: list[str] | None = None) -> tuple[str, dict[str, Any]]:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in {"-h", "--help", "help", "commands", "--list"}:
        return "commands", {}
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("command", nargs="?", default="ping")
    parser.add_argument("--json")
    parser.add_argument("--json-file")
    parsed, rest = parser.parse_known_args(argv)
    payload: dict[str, Any] = {}
    if parsed.json:
        payload.update(json.loads(parsed.json))
    if parsed.json_file:
        payload.update(json.loads(Path(parsed.json_file).read_text(encoding="utf-8")))
    key: str | None = None
    for token in rest:
        if token.startswith("--") and "=" in token:
            name, value = token[2:].split("=", 1)
            payload[name] = parse_flag_value(value)
            key = None
            continue
        if token.startswith("--"):
            key = token[2:]
            continue
        if key is None:
            raise SystemExit(f"Unexpected argument: {token}")
        payload[key] = parse_flag_value(token)
        key = None
    if key is not None:
        payload[key] = True
    return str(parsed.command), payload


def emit(payload: dict[str, Any], *, error: bool = False) -> None:
    stream = sys.stderr if error else sys.stdout
    json.dump(payload, stream, indent=2)
    stream.write("\n")


def ping(payload: dict[str, Any]) -> dict[str, Any]:
    return {"ok": True, "tool": "example-tool", "echo": payload}


def main(argv: list[str] | None = None) -> int:
    command, payload = parse_invocation(argv)
    commands = {"ping": ping, "commands": lambda _: {"commands": ["commands", "ping"]}}
    if command in {"-h", "--help", "help", "commands"}:
        emit(
            {
                "ok": True,
                "command": "commands",
                "data": commands["commands"]({}),
            }
        )
        return 0
    if command not in commands:
        known = sorted(commands)
        emit(
            {
                "ok": False,
                "command": command,
                "error": {
                    "code": "usage",
                    "message": (
                        f"Unknown command: {command}. Known: {', '.join(known)}. "
                        "Discover commands with `commands` or `--help`."
                    ),
                },
            },
            error=True,
        )
        return 1
    emit({"ok": True, "command": command, "data": commands[command](payload)})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
