from __future__ import annotations

import fnmatch
import json
import os
import re
import sys
from pathlib import Path, PurePosixPath
from typing import Any, Iterator


HELP_TOKENS = {"-h", "--help", "help", "commands", "--list"}
COMMANDS = {"search", "find", "grep", "run"}
SECRET_NAMES = {".env.yml", ".env"}
SKIP_DIR_NAMES = {
    ".git",
    ".obsidian",
    ".venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "chrome-profile",
}
SKIP_DIR_MARKERS = {("tools", "moodle_dl", "state"), ("tools", "google_auth", "state")}
TEXT_SUFFIXES = {
    ".md",
    ".markdown",
    ".py",
    ".ps1",
    ".js",
    ".ts",
    ".json",
    ".yml",
    ".yaml",
    ".txt",
    ".csv",
    ".html",
    ".css",
    ".sh",
    ".toml",
    ".xml",
    ".svg",
    ".ini",
    ".cfg",
    ".rst",
}
DEFAULT_MATCH_LIMIT = 200
DEFAULT_FILE_LIMIT = 500


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


def parse_int(value: Any, name: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as error:
        raise ToolError(f"{name} must be an integer", "usage") from error


def parse_invocation(argv: list[str] | None = None) -> tuple[str, dict[str, Any]]:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in HELP_TOKENS:
        return "commands", {}
    payload: dict[str, Any] = {}
    positionals: list[str] = []
    key: str | None = None
    index = 0
    while index < len(argv):
        token = argv[index]
        if token in HELP_TOKENS:
            return "commands", {}
        if token in {"--json", "--json-file"}:
            if index + 1 >= len(argv):
                raise ToolError(f"{token} requires a value", "usage")
            raw = argv[index + 1]
            loaded = (
                json.loads(raw)
                if token == "--json"
                else json.loads(Path(raw).read_text(encoding="utf-8"))
            )
            if not isinstance(loaded, dict):
                raise ToolError(f"{token} must contain a JSON object", "usage")
            payload.update(loaded)
            index += 2
            continue
        if token.startswith("--json=") or token.startswith("--json-file="):
            name, value = token[2:].split("=", 1)
            loaded = (
                json.loads(value)
                if name == "json"
                else json.loads(Path(value).read_text(encoding="utf-8"))
            )
            if not isinstance(loaded, dict):
                raise ToolError(f"--{name} must contain a JSON object", "usage")
            payload.update(loaded)
            index += 1
            continue
        if token.startswith("--") and "=" in token:
            name, value = token[2:].split("=", 1)
            payload[name] = parse_flag_value(value)
            key = None
            index += 1
            continue
        if token.startswith("--") or token in {"-i", "-A", "-B", "-C"}:
            if key is not None:
                payload[key] = True
            key = token[2:] if token.startswith("--") else token[1:]
            index += 1
            continue
        if key is not None:
            payload[key] = parse_flag_value(token)
            key = None
            index += 1
            continue
        positionals.append(token)
        index += 1
    if key is not None:
        payload[key] = True
    command = "search"
    if positionals and positionals[0] in COMMANDS:
        command = positionals.pop(0)
        if command == "run":
            command = "search"
    if positionals:
        payload.setdefault("path", positionals[0])
        if len(positionals) > 1:
            payload.setdefault("pattern", positionals[1])
        if len(positionals) > 2:
            raise ToolError(
                "Unexpected extra argument. Usage: [search|find|grep] [path] [pattern]",
                "usage",
            )
    return command, payload


def resolve_root(raw: Any) -> Path:
    if raw in (None, "", True):
        return vault_root()
    text = str(raw).strip().strip("\"'")
    if not text:
        return vault_root()
    candidates = [Path(text)]
    given = candidates[0]
    if not given.is_absolute():
        candidates.append(Path.cwd() / given)
        candidates.append(vault_root() / given)
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    raise ToolError(f"Path not found: {text}", "not_found")


def rel_posix(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root)).replace("\\", "/")
    except ValueError:
        try:
            return str(path.relative_to(vault_root())).replace("\\", "/")
        except ValueError:
            return str(path).replace("\\", "/")


def vault_parts(path: Path) -> tuple[str, ...]:
    try:
        return path.relative_to(vault_root()).parts
    except ValueError:
        return path.parts


def is_secret(path: Path) -> bool:
    if path.name.lower() in SECRET_NAMES:
        return True
    parts = tuple(part.lower() for part in vault_parts(path))
    lowered = set(parts)
    if "state" in lowered and ("moodle_dl" in lowered or "google_auth" in lowered):
        return True
    return any(
        parts[index : index + len(marker)] == marker
        for marker in SKIP_DIR_MARKERS
        for index in range(len(parts))
    )


def skip_dir(path: Path) -> bool:
    if path.name in SKIP_DIR_NAMES:
        return True
    return is_secret(path)


def glob_matches(rel: str, glob: str) -> bool:
    rel = rel.replace("\\", "/")
    pattern = glob.replace("\\", "/")
    posix = PurePosixPath(rel)
    candidates = [pattern]
    if "/" not in pattern.rstrip("/"):
        candidates.append("**/" + pattern)
    for candidate in candidates:
        try:
            if posix.match(candidate):
                return True
        except (ValueError, re.error):
            pass
        if fnmatch.fnmatch(rel, candidate) or fnmatch.fnmatch(posix.name, candidate):
            return True
        if candidate.startswith("**/") and (
            fnmatch.fnmatch(rel, candidate[3:])
            or posix.name == PurePosixPath(candidate).name
        ):
            return True
    return False


def truthy(value: Any) -> bool:
    return value not in (None, "", False)


def as_list(value: Any) -> list[str]:
    if value in (None, "", False, True):
        return []
    if isinstance(value, list):
        return [str(item) for item in value if item not in (None, "")]
    return [str(value)]


def compile_pattern(raw: Any, ignore_case: bool) -> re.Pattern[str] | None:
    if raw in (None, "", True, False):
        return None
    flags = re.IGNORECASE if ignore_case else 0
    try:
        return re.compile(str(raw), flags)
    except re.error as error:
        raise ToolError(f"Invalid pattern: {error}", "usage") from error


def is_probably_binary(path: Path) -> bool:
    try:
        sample = path.read_bytes()[:8192]
    except OSError:
        return True
    return b"\x00" in sample


def iter_files(root: Path) -> Iterator[Path]:
    if root.is_file():
        yield root
        return
    for current, dirnames, filenames in os.walk(root):
        current_path = Path(current)
        dirnames[:] = [name for name in dirnames if not skip_dir(current_path / name)]
        for name in filenames:
            path = current_path / name
            if is_secret(path):
                continue
            yield path


def file_allowed(
    path: Path,
    *,
    search_root: Path,
    globs: list[str],
    names: list[str],
    types: list[str],
    require_text_suffix: bool,
) -> bool:
    rel = rel_posix(path, search_root)
    if names and not any(fnmatch.fnmatch(path.name, pattern) for pattern in names):
        return False
    if globs and not any(glob_matches(rel, pattern) for pattern in globs):
        return False
    if types:
        suffixes = {item if item.startswith(".") else f".{item}" for item in types}
        if path.suffix.lower() not in {item.lower() for item in suffixes}:
            return False
    elif require_text_suffix and path.suffix.lower() not in TEXT_SUFFIXES:
        return False
    return True


def output_mode(command: str, payload: dict[str, Any], has_pattern: bool) -> str:
    raw = payload.get("output") or payload.get("output_mode") or payload.get("output-mode")
    if truthy(
        payload.get("files-with-matches")
        or payload.get("files_with_matches")
        or payload.get("files")
    ):
        return "files"
    if payload.get("count") is True or raw in {"count", "counts"}:
        return "count"
    if raw in {"files", "files_with_matches", "files-with-matches"}:
        return "files"
    if raw in {"content", "matches"}:
        return "content"
    if command == "find" or not has_pattern:
        return "files"
    return "content"


def context_sizes(payload: dict[str, Any]) -> tuple[int, int]:
    around = payload.get("context") or payload.get("C") or 0
    before = payload.get("before") or payload.get("B") or around
    after = payload.get("after") or payload.get("A") or around
    if before is True:
        before = around
    if after is True:
        after = around
    return max(0, parse_int(before or 0, "before")), max(0, parse_int(after or 0, "after"))


def search_content(command: str, payload: dict[str, Any]) -> dict[str, Any]:
    search_root = resolve_root(payload.get("path") or payload.get("root") or payload.get("dir"))
    if is_secret(search_root):
        raise ToolError("Refusing to search secret files or tool state.", "usage")
    globs = as_list(payload.get("glob") or payload.get("include"))
    names = as_list(payload.get("name"))
    types = as_list(payload.get("type") or payload.get("extension"))
    ignore_case = truthy(
        payload.get("ignore-case")
        or payload.get("ignore_case")
        or payload.get("i")
        or payload.get("insensitive")
    )
    pattern = compile_pattern(
        payload.get("pattern") or payload.get("query") or payload.get("regexp"),
        ignore_case,
    )
    if command == "grep" and pattern is None:
        raise ToolError("grep requires --pattern", "usage")
    if (
        pattern is None
        and not globs
        and not names
        and not types
        and not search_root.is_file()
    ):
        raise ToolError("Provide --pattern, --glob, --name, or --type", "usage")
    mode = output_mode(command, payload, pattern is not None)
    before_n, after_n = context_sizes(payload)
    raw_limit = (
        payload.get("head_limit")
        or payload.get("head-limit")
        or payload.get("limit")
        or payload.get("max")
    )
    default_limit = DEFAULT_FILE_LIMIT if mode == "files" else DEFAULT_MATCH_LIMIT
    limit = default_limit if raw_limit in (None, "", True) else parse_int(raw_limit, "limit")
    if limit < 1:
        raise ToolError("limit must be at least 1", "usage")
    require_text_suffix = pattern is not None and not globs and not names and not types
    matches: list[dict[str, Any]] = []
    files: list[str] = []
    counts: list[dict[str, Any]] = []
    truncated = False
    seen_files = 0
    for path in iter_files(search_root):
        if not file_allowed(
            path,
            search_root=search_root,
            globs=globs,
            names=names,
            types=types,
            require_text_suffix=require_text_suffix,
        ):
            continue
        rel = rel_posix(path, search_root if search_root.is_dir() else search_root.parent)
        if search_root.is_file():
            rel = rel_posix(path, vault_root())
        if pattern is None:
            seen_files += 1
            if seen_files > limit:
                truncated = True
                break
            files.append(rel)
            continue
        if is_probably_binary(path):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        lines = text.splitlines()
        file_hits: list[dict[str, Any]] = []
        for line_number, line in enumerate(lines, start=1):
            found = pattern.search(line)
            if not found:
                continue
            file_hits.append(
                {
                    "path": rel,
                    "line": line_number,
                    "column": found.start() + 1,
                    "text": line,
                    "before": lines[max(0, line_number - 1 - before_n) : line_number - 1],
                    "after": lines[line_number : line_number + after_n],
                }
            )
        if not file_hits:
            continue
        files.append(rel)
        counts.append({"path": rel, "count": len(file_hits)})
        if mode == "content":
            remaining = limit - len(matches)
            if remaining <= 0:
                truncated = True
                break
            if len(file_hits) > remaining:
                matches.extend(file_hits[:remaining])
                truncated = True
                break
            matches.extend(file_hits)
        elif len(files) >= limit:
            truncated = True
            break
    data: dict[str, Any] = {
        "mode": "find" if pattern is None else "grep",
        "output": mode,
        "path": rel_posix(search_root, vault_root()) if search_root != vault_root() else ".",
        "pattern": None if pattern is None else pattern.pattern,
        "glob": globs,
        "name": names,
        "type": types,
        "ignore_case": ignore_case,
        "file_count": len(files),
        "match_count": (
            sum(item["count"] for item in counts) if pattern is not None else len(files)
        ),
        "truncated": truncated,
        "files": files,
    }
    if pattern is not None and mode == "content":
        data["matches"] = matches
        data["match_count"] = len(matches)
    if pattern is not None and mode == "count":
        data["counts"] = counts
    return data


def catalog() -> dict[str, Any]:
    return {
        "program": "search_content",
        "commands": ["commands", "search", "find", "grep"],
        "invoke": [
            "python tools/run_tool/run_tool.py search_content commands",
            'python tools/run_tool/run_tool.py search_content --glob "**/Week-01.md"',
            "Always use flags. Never write scratch files.",
        ],
        "rule": (
            "Combined find + grep. Omit --pattern to list files. "
            "Never search .env.yml or tool state directories."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    command = None
    try:
        command, payload = parse_invocation(argv)
        if command in HELP_TOKENS:
            emit({"ok": True, "command": "commands", "data": catalog()})
            return 0
        data = search_content(command, payload)
        emit({"ok": True, "command": command, "data": data})
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
