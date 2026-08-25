from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


HELP_TOKENS = {"-h", "--help", "help", "commands", "--list"}
SECRET_NAMES = {".env.yml", ".env"}
SECRET_DIR_MARKERS = {("tools", "moodle_dl", "state"), ("tools", "google_auth", "state")}


class ToolError(Exception):
    def __init__(self, message: str, code: str = "usage") -> None:
        super().__init__(message)
        self.message = message
        self.code = code


def vault_root() -> Path:
    return Path(__file__).resolve().parents[2]


def emit(payload: dict[str, Any], *, error: bool = False) -> None:
    stream = sys.stderr if error else sys.stdout
    json.dump(payload, stream, indent=2, default=str)
    stream.write("\n")


def parse_int(value: Any, name: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as error:
        raise ToolError(f"{name} must be an integer", "usage") from error


def parse_invocation(argv: list[str] | None = None) -> tuple[str, dict[str, Any]]:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in HELP_TOKENS:
        return "commands", {}
    rest = argv
    if argv[0] in {"read", "run"}:
        rest = argv[1:]
    payload: dict[str, Any] = {}
    positionals: list[str] = []
    key: str | None = None
    for token in rest:
        if token in HELP_TOKENS:
            return "commands", {}
        if token.startswith("--") and "=" in token:
            name, value = token[2:].split("=", 1)
            payload[name] = value
            key = None
            continue
        if token.startswith("--"):
            if key is not None:
                payload[key] = True
            key = token[2:]
            continue
        if key is not None:
            payload[key] = token
            key = None
            continue
        positionals.append(token)
    if key is not None:
        payload[key] = True
    if positionals:
        payload.setdefault("path", positionals[0])
        if len(positionals) > 1:
            payload.setdefault("start", positionals[1])
        if len(positionals) > 2:
            payload.setdefault("end", positionals[2])
        if len(positionals) > 3:
            raise ToolError("Unexpected extra argument. Usage: <path> [start] [end]", "usage")
    return "read", payload


def resolve_path(raw: str) -> Path:
    text = str(raw).strip().strip("\"'")
    if not text:
        raise ToolError("path is required", "usage")
    candidates = []
    given = Path(text)
    candidates.append(given)
    if not given.is_absolute():
        candidates.append(Path.cwd() / given)
        candidates.append(vault_root() / given)
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    raise ToolError(f"File not found: {text}", "not_found")


def assert_not_secret(path: Path) -> None:
    if path.name.lower() in SECRET_NAMES:
        raise ToolError(f"Refusing to read secret file: {path.name}", "usage")
    parts = {part.lower() for part in path.parts}
    if "state" in parts and ("moodle_dl" in parts or "google_auth" in parts):
        raise ToolError("Refusing to read tool state or secret files.", "usage")


def select_range(
    total: int,
    start: Any = None,
    end: Any = None,
    limit: Any = None,
) -> tuple[int, int]:
    begin = 1 if start in (None, "", True) else parse_int(start, "start")
    if begin < 1:
        begin = total + begin + 1
    if begin < 1:
        begin = 1
    if end not in (None, "", True):
        finish = parse_int(end, "end")
    elif limit not in (None, "", True):
        finish = begin + parse_int(limit, "limit") - 1
    else:
        finish = total
    if finish < 1:
        finish = total + finish + 1
    if total == 0:
        return 1, 0
    finish = min(finish, total)
    if begin > total:
        return begin, begin - 1
    return begin, finish


def read_file_lines(payload: dict[str, Any]) -> dict[str, Any]:
    raw_path = payload.get("path") or payload.get("file") or payload.get("filename")
    if not raw_path or raw_path is True:
        raise ToolError("path is required", "usage")
    path = resolve_path(str(raw_path))
    assert_not_secret(path)
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    total = len(lines)
    start, end = select_range(
        total,
        payload.get("start") or payload.get("offset"),
        payload.get("end"),
        payload.get("limit") or payload.get("max") or payload.get("count"),
    )
    selected = lines[start - 1 : end] if end >= start else []
    numbered = [f"{index}| {line}" for index, line in enumerate(selected, start=start)]
    try:
        rel = str(path.relative_to(vault_root())).replace("\\", "/")
    except ValueError:
        rel = str(path)
    return {
        "path": rel,
        "start": start,
        "end": end if selected else 0,
        "total": total,
        "text": "\n".join(selected),
        "lines": numbered,
    }


def catalog() -> dict[str, Any]:
    return {
        "program": "read_file_lines",
        "commands": ["commands", "read"],
        "invoke": [
            "python tools/run_tool/run_tool.py read_file_lines commands",
            "python tools/run_tool/run_tool.py read_file_lines courses/MATH-212-Differential-Equations-Fall-2026/MATH-212.md 1 35",
            "Always use flags. Never write scratch files.",
        ],
        "rule": "Lines are 1-based. Omit end to read through EOF. Do not read .env.yml.",
    }


def main(argv: list[str] | None = None) -> int:
    command = None
    try:
        command, payload = parse_invocation(argv)
        if command in HELP_TOKENS:
            emit({"ok": True, "command": "commands", "data": catalog()})
            return 0
        data = read_file_lines(payload)
        emit({"ok": True, "command": "read", "data": data})
        return 0
    except ToolError as error:
        emit(
            {
                "ok": False,
                "command": command,
                "error": {"code": error.code, "message": error.message},
            },
            error=True,
        )
        return 1
    except Exception as error:
        emit(
            {
                "ok": False,
                "command": command,
                "error": {"code": "tool", "message": str(error)},
            },
            error=True,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
