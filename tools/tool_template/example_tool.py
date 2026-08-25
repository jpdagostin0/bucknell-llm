from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "cli_args"))
import cli_args


def parse_flag_value(raw: str) -> Any:
    return cli_args.parse_flag_value(raw)


def parse_invocation(argv: list[str] | None = None) -> tuple[str, dict[str, Any]]:
    return cli_args.parse_invocation(argv, default_command="ping")


def emit(payload: dict[str, Any], *, error: bool = False) -> None:
    stream = sys.stderr if error else sys.stdout
    json.dump(payload, stream, indent=2)
    stream.write("\n")


def ping(payload: dict[str, Any]) -> dict[str, Any]:
    return {"ok": True, "tool": "example_tool", "echo": payload}


def main(argv: list[str] | None = None) -> int:
    try:
        command, payload = parse_invocation(argv)
    except cli_args.CliError as error:
        emit(
            {
                "ok": False,
                "command": None,
                "error": {"code": error.code, "message": error.message},
            },
            error=True,
        )
        return 1
    commands = {"ping": ping, "commands": lambda _: {"commands": ["commands", "ping"]}}
    if command in {"-h", "--help", "help", "commands"}:
        emit(
            {
                "ok": True,
                "command": "commands",
                "data": {
                    "program": "example_tool",
                    "commands": ["commands", "ping"],
                    "invoke": [
                        "python tools/run_tool/run_tool.py example_tool commands",
                        "python tools/run_tool/run_tool.py example_tool ping",
                        "Always use flags. Never write scratch files.",
                    ],
                },
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
                        "Example: python tools/run_tool/run_tool.py example_tool ping"
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
