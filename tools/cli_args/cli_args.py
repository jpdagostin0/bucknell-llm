from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

HELP_TOKENS = {"-h", "--help", "help", "commands", "--list"}
ARGUMENT_HELP = {
    "flags": "Always use --name value. Repeat a flag for a list: --class MATH-212 --class MATH-245.",
    "json": "Never use --json when flags work. Nested objects only when a CLI requires them.",
}
ARGUMENT_RULE = (
    "Always use --flag value. Repeat a flag for a list. "
    "Never write payload.json when flags are enough. "
    "Always call python tools/run_tool/run_tool.py with forward slashes. "
    "Never use pyodide. Read JSON from stdout. Never write scratch files."
)


class CliError(Exception):
    def __init__(self, message: str, code: str = "usage") -> None:
        super().__init__(message)
        self.message = message
        self.code = code


def is_sandbox_or_scratchpad_path(raw: str) -> bool:
    text = str(raw).replace("\\", "/").lower()
    if ".lmstudio/scratchpads" in text:
        return True
    posix = text if text.startswith("/") else ""
    if posix == "/inputs" or posix.startswith("/inputs/"):
        return True
    if posix == "/outputs" or posix.startswith("/outputs/"):
        return True
    return False


def require_host_path(
    raw: str,
    *,
    kind: str = "path",
    error_class: type[Exception] | None = None,
) -> Path:
    if is_sandbox_or_scratchpad_path(raw):
        raise _error(
            error_class,
            f"{kind} {raw!r} is not on the host filesystem. "
            "Do not use .lmstudio/scratchpads, /inputs, or /outputs. "
            "Use a vault-relative path such as payload.json, or skip the file and pass --flag values.",
            "usage",
        )
    return Path(raw)


def parse_flag_value(raw: str) -> Any:
    text = raw.strip()
    lowered = text.lower()
    if lowered in {"true", "yes"}:
        return True
    if lowered in {"false", "no"}:
        return False
    if lowered in {"null", "none"}:
        return None
    if re.fullmatch(r"-?\d+", text):
        return int(text)
    if re.fullmatch(r"-?\d+\.\d+", text):
        return float(text)
    if text[:1] in "{[":
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return text
    return text


def assign_flag(payload: dict[str, Any], seen: set[str], key: str, value: Any) -> None:
    if key in seen:
        existing = payload.get(key)
        extra = value if isinstance(value, list) else [value]
        if isinstance(existing, list):
            existing.extend(extra)
        else:
            payload[key] = [existing, *extra]
        return
    seen.add(key)
    payload[key] = value


def _error(
    error_class: type[Exception] | None,
    message: str,
    code: str = "usage",
) -> Exception:
    cls = error_class or CliError
    try:
        return cls(message, code)  # type: ignore[call-arg]
    except TypeError:
        error = cls(message)
        error.code = code  # type: ignore[attr-defined]
        error.message = message  # type: ignore[attr-defined]
        return error


def _load_json_object(raw: str, *, source: str, error_class: type[Exception] | None) -> dict[str, Any]:
    try:
        loaded = json.loads(raw)
    except json.JSONDecodeError as error:
        raise _error(error_class, f"{source} is not valid JSON: {error}", "usage") from error
    if not isinstance(loaded, dict):
        raise _error(error_class, f"{source} must contain a JSON object", "usage")
    return loaded


def _load_json_file(
    raw: str,
    *,
    error_class: type[Exception] | None,
) -> dict[str, Any]:
    path = require_host_path(raw, kind="--json-file", error_class=error_class)
    if not path.is_file():
        raise _error(
            error_class,
            f"--json-file not found: {path}. Use a vault-relative host path such as payload.json, "
            "or pass --flag values instead.",
            "usage",
        )
    return _load_json_object(
        path.read_text(encoding="utf-8"),
        source="--json-file",
        error_class=error_class,
    )


def parse_invocation(
    argv: list[str] | None = None,
    default_command: str | None = None,
    error_class: type[Exception] | None = None,
    allow_json: bool = True,
) -> tuple[str, dict[str, Any]]:
    using_sys = argv is None
    argv = list(sys.argv[1:] if using_sys else argv)
    if argv and argv[0] in HELP_TOKENS:
        command = "commands"
        rest = argv[1:]
    elif not argv or argv[0].startswith("-"):
        command = default_command or "commands"
        rest = argv
    else:
        command = argv[0]
        rest = argv[1:]
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--json")
    parser.add_argument("--json-file")
    args, unknown = parser.parse_known_args(rest)
    if not allow_json and (args.json or args.json_file):
        raise _error(
            error_class,
            'Never pass --json or --json-file here. Use flags. '
            'Example: python tools/run_tool/run_tool.py fast_dashboard --class "MATH 212"',
            "usage",
        )
    payload: dict[str, Any] = {}
    if args.json_file:
        payload.update(_load_json_file(args.json_file, error_class=error_class))
    if args.json:
        payload.update(
            _load_json_object(args.json, source="--json", error_class=error_class)
        )
    elif (
        using_sys
        and not args.json_file
        and not sys.stdin.isatty()
        and not unknown
    ):
        raw = sys.stdin.read().strip()
        if raw:
            payload.update(
                _load_json_object(raw, source="stdin", error_class=error_class)
            )
    seen: set[str] = set()
    key: str | None = None
    for token in unknown:
        if token in {"-h", "--help"}:
            return "commands", {}
        if token.startswith("--") and "=" in token:
            name, value = token[2:].split("=", 1)
            assign_flag(payload, seen, name, parse_flag_value(value))
            key = None
            continue
        if token.startswith("--"):
            if key is not None:
                assign_flag(payload, seen, key, True)
            key = token[2:]
            continue
        if key is None:
            raise _error(error_class, f"Unexpected argument: {token}", "usage")
        assign_flag(payload, seen, key, parse_flag_value(token))
        key = None
    if key is not None:
        assign_flag(payload, seen, key, True)
    return command, payload
