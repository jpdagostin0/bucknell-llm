from __future__ import annotations

import datetime as dt
import difflib
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "cli_args"))
import cli_args

HELP_TOKENS = cli_args.HELP_TOKENS
CLI_SHELL_RULE = cli_args.ARGUMENT_RULE
EMULATED_PYTHON_MESSAGE = (
    "This CLI cannot run in an in-memory Python sandbox. "
    "Always use a real python.exe: python tools/run_tool/run_tool.py <tool> ..."
)

FORBIDDEN_FIELDS = ("status", "due", "priority", "estimate")
SECRET_NAME_PARTS = ("cookie", "token", "password", "secret", "credential")
SECRET_FILENAMES = {
    "config.json",
    "config.json.bak",
    "moodle-dl.db",
    "moodle.db",
}
BINARY_RETAIN_EXTENSIONS = {".pdf", ".doc", ".docx", ".ppt", ".pptx", ".epub"}
EPHEMERAL_EXTENSIONS = {
    ".css",
    ".db",
    ".htm",
    ".html",
    ".js",
    ".json",
    ".log",
    ".mp3",
    ".mp4",
    ".tmp",
    ".webm",
    ".xml",
}
TERM_START = dt.date(2026, 8, 24)
WEEKDAY_LETTERS = {"M": 0, "T": 1, "W": 2, "R": 3, "F": 4, "S": 5, "U": 6}
MONTHS = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "sept": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}
KIND_TO_LINEAR = {
    "homework": "pset",
    "assignment": "pset",
    "worksheet": "pset",
    "pset": "pset",
    "reading": "reading",
    "quiz": "quiz",
    "exam": "exam",
    "lab": "lab",
    "lecture": "study",
    "study": "study",
    "admin": "admin",
    "course project": "course project",
}
KIND_PATTERNS = (
    ("syllabus", re.compile(r"syllabus", re.I)),
    ("homework", re.compile(r"\b(?:homework|h[wu]\b|pset|problem\s*set)|(?:^|[\s/_])H(?:W)?-?\d+", re.I)),
    ("worksheet", re.compile(r"worksheet|(?:^|[\s/_])W(?:S)?-?\d+", re.I)),
    ("reading", re.compile(r"(?:reading[-\s]?guide|content[-\s]?guide|reading)|(?:^|[\s/_])R(?:G)?-?\d+", re.I)),
    ("quiz", re.compile(r"\bquiz\b", re.I)),
    ("exam", re.compile(r"\b(?:exam|midterm|final)\b", re.I)),
    ("lab", re.compile(r"\blab\b", re.I)),
    ("lecture", re.compile(r"\b(?:lecture|slides?)\b", re.I)),
    ("textbook", re.compile(r"(?:textbook|edition)\b", re.I)),
)
DEADLINE_HINT = re.compile(
    r"\b(?:homework|assignment|quiz|exam|lab|due|deadline|pset)\b",
    re.I,
)
PAGE_CITATION = re.compile(
    r"\b(?:pp?\.?|pages?)\s+(\d+)(?:\s*[-–—,and]+\s*(\d+))?",
    re.I,
)
SECTION_CITATION = re.compile(
    r"\b(?:sections?|secs?\.?|§)\s*(\d+\.\d+(?:\s*(?:and|,|&)\s*\d+\.\d+)*)",
    re.I,
)
NUMBERED_ITEM = re.compile(
    r"(?P<label>Homework|Assignment|Quiz|Lab|Exam|Worksheet|Reading-Guide|Reading Guide)"
    r"[ -]?(?P<number>\d+)",
    re.I,
)
DRIVE_FOLDER = re.compile(
    r"https://drive\.google\.com/drive/folders/([A-Za-z0-9_-]+)"
)
LINEAR_PROJECT = re.compile(r"https://linear\.app/[^/]+/project/([^/?#]+)")
COURSE_CODE = re.compile(r"^([A-Z]{2,4})[ -]?([0-9]{3})$")
COURSE_INDEX = re.compile(r"^[A-Z]{2,4}-[0-9]{3}\.md$")
FRONTMATTER = re.compile(r"\A---\r?\n(.*?)\r?\n---(?:\r?\n|$)", re.S)
WIKILINK = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|[^\]]+)?\]\]")
REPEATED_HEADER = re.compile(r"^\s*(?:\d+|[A-Z][A-Z0-9 -]{8,})\s*$")


class ToolError(Exception):
    def __init__(self, message: str, code: str = "api") -> None:
        super().__init__(message)
        self.message = message
        self.code = code


def is_emulated_python() -> bool:
    if "pyodide" in sys.modules:
        return True
    return getattr(sys, "platform", "") in {"emscripten", "wasi"}


def require_host_python() -> None:
    if is_emulated_python():
        raise ToolError(EMULATED_PYTHON_MESSAGE, "tool")


def is_sandbox_or_scratchpad_path(raw: str) -> bool:
    return cli_args.is_sandbox_or_scratchpad_path(raw)


def require_host_path(raw: str, *, kind: str = "path") -> Path:
    try:
        return cli_args.require_host_path(raw, kind=kind, error_class=ToolError)
    except cli_args.CliError as error:
        raise ToolError(error.message, error.code) from error


def vault_root() -> Path:
    return Path(__file__).resolve().parents[2]


def to_snake(name: str) -> str:
    name = name.replace("-", "_")
    name = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name)
    return name.lower()


def to_camel(name: str) -> str:
    parts = to_snake(name).split("_")
    return parts[0] + "".join(part.title() for part in parts[1:])


def normalize_payload(payload: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for key, value in payload.items():
        normalized[to_snake(str(key))] = value
        normalized[to_camel(str(key))] = value
        normalized[str(key)] = value
    return normalized


def get_value(
    payload: dict[str, Any],
    *names: str,
    default: Any = None,
    required: bool = False,
) -> Any:
    data = normalize_payload(payload)
    for name in names:
        for candidate in (name, to_snake(name), to_camel(name)):
            if candidate in data and data[candidate] is not None:
                return data[candidate]
    if required:
        raise ToolError(f"Missing required argument: {names[0]}", "usage")
    return default


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() not in {"", "0", "false", "no", "off"}


def parse_flag_value(raw: str) -> Any:
    return cli_args.parse_flag_value(raw)


def parse_invocation(
    argv: list[str] | None = None,
    default_command: str | None = None,
) -> tuple[str, dict[str, Any]]:
    require_host_python()
    try:
        return cli_args.parse_invocation(
            argv,
            default_command=default_command,
            error_class=ToolError,
            allow_json=False,
        )
    except cli_args.CliError as error:
        raise ToolError(error.message, error.code) from error


def emit(payload: dict[str, Any], *, error: bool = False) -> None:
    stream = sys.stderr if error else sys.stdout
    json.dump(payload, stream, indent=2, default=str)
    stream.write("\n")


def run_cli(
    program: str,
    commands: dict[str, Callable[[dict[str, Any]], Any]],
    argv: list[str] | None = None,
    default_command: str | None = "run",
    example: str = '--class "MATH 212"',
) -> int:
    command = None
    try:
        command, payload = parse_invocation(argv, default_command=default_command)
        if command in HELP_TOKENS:
            emit(
                {
                    "ok": True,
                    "command": "commands",
                    "data": {
                        "program": program,
                        "commands": sorted({"commands", *commands}),
                        "default": default_command,
                        "invoke": [
                            f"python tools/run_tool/run_tool.py {program} commands",
                            f"python tools/run_tool/run_tool.py {program} {example}".rstrip(),
                            "Always use flags. Never write scratch files.",
                        ],
                    },
                }
            )
            return 0
        handler = commands.get(command)
        if handler is None:
            known = sorted({"commands", *commands})
            message = f"Unknown command: {command}. Known: {', '.join(known)}."
            close = difflib.get_close_matches(str(command or ""), known, n=3, cutoff=0.5)
            if close:
                message += f" Did you mean {', '.join(close)}?"
            message += (
                f' Example: python tools/run_tool/run_tool.py {program} {example}'.rstrip()
            )
            raise ToolError(message, "usage")
        data = handler(payload)
        emit({"ok": True, "command": command, "data": data})
        if isinstance(data, dict) and data.get("ok") is False:
            return 1
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
                "error": {"code": "api", "message": str(error)},
            },
            error=True,
        )
        return 1


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(vault_root()).as_posix()
    except ValueError:
        return str(path)


def load_frontmatter(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    match = FRONTMATTER.match(text)
    if not match:
        return {}
    loaded = yaml.safe_load(match.group(1)) or {}
    return loaded if isinstance(loaded, dict) else {}


def unwrap_wikilink(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    match = WIKILINK.search(text)
    return (match.group(1) if match else text).strip()


def hyphen_code(code: str) -> str:
    match = COURSE_CODE.match(code.strip().upper().replace("_", " "))
    if not match:
        compact = re.sub(r"[^A-Z0-9]", "", code.upper())
        letters = re.match(r"^([A-Z]{2,4})([0-9]{3})$", compact)
        if not letters:
            raise ToolError(f"Not a course code: {code}", "usage")
        return f"{letters.group(1)}-{letters.group(2)}"
    return f"{match.group(1)}-{match.group(2)}"


def spaced_code(code: str) -> str:
    hyphen = hyphen_code(code)
    dept, number = hyphen.split("-", 1)
    return f"{dept} {number}"


def compact_code(code: str) -> str:
    return hyphen_code(code).replace("-", "")


def extract_drive_folder_id(url: str | None) -> str | None:
    if not url:
        return None
    match = DRIVE_FOLDER.search(str(url))
    return match.group(1) if match else None


def extract_linear_project_slug(url: str | None) -> str | None:
    if not url:
        return None
    match = LINEAR_PROJECT.search(str(url))
    return match.group(1) if match else None


def discover_classes(root: Path | None = None) -> list[dict[str, Any]]:
    root = root or vault_root()
    courses = root / "courses"
    if not courses.is_dir():
        return []
    discovered: list[dict[str, Any]] = []
    for folder in sorted(courses.iterdir()):
        if not folder.is_dir():
            continue
        indexes = [
            path
            for path in folder.iterdir()
            if path.is_file() and COURSE_INDEX.fullmatch(path.name)
        ]
        if not indexes:
            continue
        path = indexes[0]
        metadata = load_frontmatter(path)
        code = str(metadata.get("code") or path.stem.replace("-", " "))
        try:
            hyphen = hyphen_code(code)
        except ToolError:
            continue
        textbooks_dir = folder / "textbooks"
        textbooks = (
            sorted(
                item
                for item in textbooks_dir.iterdir()
                if item.is_file() and item.suffix.lower() == ".pdf"
            )
            if textbooks_dir.is_dir()
            else []
        )
        work_dir = folder / "work"
        work_notes = (
            sorted(item for item in work_dir.glob("*.md")) if work_dir.is_dir() else []
        )
        notes_dir = folder / "notes"
        week_notes = (
            sorted(item for item in notes_dir.glob("Week-*.md"))
            if notes_dir.is_dir()
            else []
        )
        content = metadata.get("content")
        linear_project = metadata.get("linear_project")
        discovered.append(
            {
                "code": spaced_code(hyphen),
                "hyphen": hyphen,
                "compact": compact_code(hyphen),
                "title": metadata.get("title"),
                "instructor": metadata.get("instructor"),
                "folder": folder,
                "index": path,
                "syllabus": folder / "Syllabus.md",
                "linear_project": linear_project,
                "linear_slug": extract_linear_project_slug(str(linear_project or "")),
                "content": content,
                "drive_folder_id": extract_drive_folder_id(str(content or "")),
                "textbooks": textbooks,
                "work_notes": work_notes,
                "week_notes": week_notes,
            }
        )
    return discovered


def resolve_classes(payload: dict[str, Any]) -> list[dict[str, Any]]:
    requested = [
        str(item).strip()
        for item in as_list(get_value(payload, "class", "course", "code"))
        if str(item).strip()
    ]
    classes = discover_classes()
    if not requested:
        return classes
    resolved: list[dict[str, Any]] = []
    for item in requested:
        resolved.append(resolve_class(item, classes))
    return resolved


def resolve_class(
    requested: str,
    classes: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    classes = classes or discover_classes()
    needle = requested.strip()
    needle_compact = re.sub(r"[^A-Z0-9]", "", needle.upper())
    matches: list[dict[str, Any]] = []
    for course in classes:
        haystacks = {
            course["code"],
            course["hyphen"],
            course["compact"],
            course["folder"].name,
            str(course.get("title") or ""),
        }
        if any(needle.lower() == str(value).lower() for value in haystacks):
            matches.append(course)
            continue
        if needle_compact and needle_compact == course["compact"]:
            matches.append(course)
            continue
        if needle_compact and needle_compact in course["compact"]:
            matches.append(course)
    unique = {course["hyphen"]: course for course in matches}
    if len(unique) == 1:
        return next(iter(unique.values()))
    if not unique:
        raise ToolError(f"No enrolled class matches {requested!r}.", "usage")
    names = ", ".join(sorted(unique))
    raise ToolError(f"Ambiguous class {requested!r} matched {names}.", "usage")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_secret_path(path: Path) -> bool:
    name = path.name.lower()
    if name in SECRET_FILENAMES:
        return True
    return any(part in name for part in SECRET_NAME_PARTS)


def classify_item(name: str, *, size: int = 0, parent: str = "") -> dict[str, Any]:
    blob = f"{parent} {name}"
    kind = "other"
    for label, pattern in KIND_PATTERNS:
        if pattern.search(blob) or (label == "textbook" and size >= 8 * 1024 * 1024):
            kind = label
            break
    deadline = bool(DEADLINE_HINT.search(blob)) or kind in {
        "homework",
        "quiz",
        "exam",
        "lab",
    }
    extension = Path(name).suffix.lower()
    if extension == ".url":
        action = "link"
    elif extension in EPHEMERAL_EXTENSIONS:
        action = "skip"
    elif kind == "textbook":
        action = "textbook"
    elif extension in BINARY_RETAIN_EXTENSIONS:
        action = "retain"
    elif extension in {".md", ".txt"}:
        action = "convert"
    else:
        action = "review"
    return {
        "kind": kind,
        "action": action,
        "deadline": deadline,
        "week": infer_week(blob),
    }


def infer_week(text: str) -> int | None:
    match = re.search(r"\bweek[ -]?(\d{1,2})\b", text, re.I)
    if not match:
        return None
    return int(match.group(1))


def zero_pad_item_name(name: str) -> str:
    def replacer(match: re.Match[str]) -> str:
        label = match.group("label").replace(" ", "-")
        number = f"{int(match.group('number')):02d}"
        return f"{label}-{number}"

    return NUMBERED_ITEM.sub(replacer, name)


def suggested_retain_name(course: dict[str, Any], source_name: str) -> str:
    cleaned = zero_pad_item_name(source_name).replace("_", " ").strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    prefix = course["hyphen"]
    if cleaned.upper().startswith(prefix):
        return cleaned
    if cleaned.upper().startswith(course["compact"]):
        return f"{prefix} {cleaned[len(course['compact']):]}".replace("  ", " ").strip()
    return f"{prefix} {cleaned}"


def extract_page_citations(text: str) -> list[dict[str, int]]:
    citations: list[dict[str, int]] = []
    seen: set[tuple[int, int]] = set()
    for match in PAGE_CITATION.finditer(text):
        start = int(match.group(1))
        end = int(match.group(2) or match.group(1))
        if start > end:
            start, end = end, start
        key = (start, end)
        if key in seen:
            continue
        seen.add(key)
        citations.append({"start": start, "end": end})
    return citations


def extract_section_citations(text: str) -> list[str]:
    found: list[str] = []
    for match in SECTION_CITATION.finditer(text):
        for part in re.split(r"\s*(?:and|,|&)\s*", match.group(1)):
            part = part.strip()
            if part and part not in found:
                found.append(part)
    return found


def printed_spec(citations: list[dict[str, int]]) -> str | None:
    if not citations:
        return None
    parts: list[str] = []
    for item in citations:
        if item["start"] == item["end"]:
            parts.append(str(item["start"]))
        else:
            parts.append(f"{item['start']}-{item['end']}")
    return ",".join(parts)


def extract_due_hints(text: str) -> list[str]:
    hints: list[str] = []
    for match in re.finditer(
        r"due(?:\s+date)?[:\s]+([A-Za-z0-9,/\- ]{3,40})",
        text,
        re.I,
    ):
        hints.append(re.sub(r"\s+", " ", match.group(0)).strip())
    return hints


def parse_due_date(text: str, *, year: int = 2026) -> str | None:
    iso = re.search(r"\b(20\d{2}-\d{2}-\d{2})\b", text)
    if iso:
        return iso.group(1)
    named = re.search(
        r"\b(" + "|".join(MONTHS) + r")\s+(\d{1,2})(?:st|nd|rd|th)?(?:,\s*(\d{4}))?\b",
        text,
        re.I,
    )
    if named:
        month = MONTHS[named.group(1).lower()]
        day = int(named.group(2))
        if named.group(3):
            year = int(named.group(3))
        try:
            return dt.date(year, month, day).isoformat()
        except ValueError:
            return None
    numeric = re.search(r"\b(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?\b", text)
    if numeric:
        month = int(numeric.group(1))
        day = int(numeric.group(2))
        raw_year = numeric.group(3)
        if raw_year:
            year = int(raw_year)
            if year < 100:
                year += 2000
        if month > 12:
            month, day = day, month
        try:
            return dt.date(year, month, day).isoformat()
        except ValueError:
            return None
    return None


def meeting_weekdays(meetings: str) -> list[int]:
    days: list[int] = []
    cleaned = re.sub(r"\b(?:AM|PM|LAB|LECTURE)\b", " ", meetings, flags=re.I)
    for token in re.findall(r"\b[MTWRFSU]{1,5}\b", cleaned.upper()):
        for letter in token:
            weekday = WEEKDAY_LETTERS.get(letter)
            if weekday is not None and weekday not in days:
                days.append(weekday)
    return days


def lecture_dates_for_week(week: int, meetings: str) -> list[str]:
    start = TERM_START + dt.timedelta(weeks=max(week, 1) - 1)
    start -= dt.timedelta(days=start.weekday())
    days = meeting_weekdays(meetings) or [0, 2, 4]
    dates = []
    for offset in range(7):
        current = start + dt.timedelta(days=offset)
        if current.weekday() in days:
            dates.append(current.isoformat())
    return dates


def class_wikilink(course: dict[str, Any]) -> str:
    relative = rel(course["index"]).removesuffix(".md")
    return f"[[{relative}]]"


def week_wikilink(course: dict[str, Any], week: int) -> str:
    return (
        f"[[courses/{course['folder'].name}/notes/Week-{week:02d}|Week {week:02d}]]"
    )


def attachment_wikilink(path: Path, label: str | None = None) -> str:
    target = rel(path)
    title = label or path.stem
    if title.lower().startswith(path.stem[:7].lower()):
        title = path.stem
    return f"[[{target}|{title}]]"


def read_url_file(path: Path) -> str | None:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    match = re.search(r"^URL=(.+)$", text, re.I | re.M)
    return match.group(1).strip() if match else None


def payload_flags(payload: dict[str, Any], *skip: str) -> list[str]:
    args: list[str] = []
    skipped = {to_snake(name) for name in skip}
    for key, value in payload.items():
        snake = to_snake(str(key))
        if snake in skipped:
            continue
        flag = "--" + snake.replace("_", "-")
        if value is True:
            args.append(flag)
            continue
        if value is False or value is None:
            continue
        if isinstance(value, (list, dict)):
            args.extend([flag, json.dumps(value)])
        else:
            args.extend([flag, str(value)])
    return args



def needs_llm(kind: str, **fields: Any) -> dict[str, Any]:
    command = fields.pop("command", None)
    action = fields.pop("action", "run" if command else "ask_user")
    item: dict[str, Any] = {"kind": kind, "action": action}
    if command:
        item["command"] = command
    item.update({key: value for key, value in fields.items() if value is not None})
    return item


def run_catalog_tool(
    name: str,
    args: list[str] | None = None,
    *,
    timeout: int | None = 120,
    check: bool = False,
) -> subprocess.CompletedProcess[str]:
    ensure_tool(name)
    run_tool_path = str(Path(__file__).resolve().parents[1] / "run_tool")
    if run_tool_path not in sys.path:
        sys.path.insert(0, run_tool_path)
    import run_tool

    command, env, cwd = run_tool.build_command(name, args or [])
    result = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
    )
    if check and result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        raise ToolError(
            f"{name} failed ({result.returncode}): {detail[:800]}",
            "tool",
        )
    return result


def decode_json_payload(raw: str) -> dict[str, Any]:
    text = raw.strip()
    if not text:
        raise ToolError("Tool returned empty JSON.", "tool")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start : end + 1])
        raise ToolError(f"Tool returned non-JSON output: {text[:400]}", "tool")


def tool_sentinels() -> dict[str, Path]:
    root = vault_root()
    return {
        "pymarkdown": root / "tools/pymarkdown/.venv/Scripts/python.exe",
        "moodle_dl": root / "tools/moodle_dl/.venv/Scripts/python.exe",
        "markitdown": root / "tools/markitdown/.venv/Scripts/python.exe",
        "pypdf": root / "tools/pypdf/.venv/Scripts/python.exe",
        "google_auth": root / "tools/google_auth/.venv/Scripts/python.exe",
        "google_drive": root / "tools/google_drive/.venv/Scripts/python.exe",
        "gmail": root / "tools/gmail/.venv/Scripts/python.exe",
        "google_calendar": root / "tools/google_calendar/.venv/Scripts/python.exe",
        "linear": root / "tools/linear/node_modules/@linear/sdk",
        "gradescope": root / "tools/gradescope/.venv/Scripts/python.exe",
        "selenium": root / "tools/selenium/.venv/Scripts/python.exe",
        "flint": root / "tools/flint/bin/flint.exe",
        "ls_lint": root / "tools/ls_lint/bin/ls-lint-windows-amd64.exe",
    }


def ensure_tool(name: str) -> Path:
    sentinel = tool_sentinels()[name]
    if sentinel.exists():
        return sentinel
    installer = vault_root() / "tools" / name / "install.py"
    if name in {"google_drive", "gmail", "google_calendar"}:
        ensure_tool("google_auth")
    if not installer.exists():
        raise ToolError(f"Missing installer for {name}.", "tool")
    result = subprocess.run(
        [sys.executable, str(installer)],
        cwd=vault_root(),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=600,
        check=False,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        raise ToolError(
            f"{installer.name} failed ({result.returncode}): {detail[:800]}",
            "tool",
        )
    if not sentinel.exists():
        raise ToolError(f"{name} is still missing after install.", "tool")
    return sentinel


def pymarkdown_argv(*args: str) -> list[str]:
    python = vault_root() / "tools/pymarkdown/.venv/Scripts/python.exe"
    return [str(python), "-m", "pymarkdown", *args]


def run_json_tool(
    name: str,
    args: list[str],
    *,
    timeout: int | None = 120,
) -> dict[str, Any]:
    ensure_tool(name)
    result = run_catalog_tool(name, args, timeout=timeout)
    raw = result.stdout if result.stdout.strip().startswith("{") else result.stderr
    payload = decode_json_payload(raw or result.stdout or result.stderr)
    if not payload.get("ok", True):
        error = payload.get("error") or {}
        raise ToolError(
            str(error.get("message") or f"{name} failed"),
            str(error.get("code") or "tool"),
        )
    return payload.get("data") or {}


def is_moodle_url(url: str) -> bool:
    raw = str(url or "").strip()
    if not raw:
        return False
    parsed = urlparse(raw if "://" in raw else f"https://{raw}")
    host = (parsed.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    return host.startswith("moodle")


def moodle_state_dir() -> Path:
    return vault_root() / "tools/moodle_dl/state"


def moodle_config_exists() -> bool:
    return (moodle_state_dir() / "config.json").exists()


def course_matches_blob(course: dict[str, Any], blob: str) -> bool:
    compact = re.sub(r"[^a-z0-9]", "", blob.lower())
    if "fa2026" not in compact and "fall2026" not in compact:
        return False
    if course["compact"].lower() in compact:
        return True
    lowered = blob.lower()
    if course["hyphen"].lower() in lowered or course["code"].lower() in lowered:
        return True
    title = str(course.get("title") or "").lower()
    return bool(title and title in lowered)


def inventory_moodle(course: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    state = moodle_state_dir()
    if not state.is_dir():
        return []
    items: list[dict[str, Any]] = []
    for path in state.rglob("*"):
        if not path.is_file() or is_secret_path(path):
            continue
        relative = path.relative_to(state)
        if any(is_secret_path(Path(part)) for part in relative.parts):
            continue
        blob = relative.as_posix()
        if course is not None and not course_matches_blob(course, blob):
            continue
        classification = classify_item(
            path.name,
            size=path.stat().st_size,
            parent=relative.as_posix(),
        )
        items.append(
            {
                "path": str(path),
                "relative": relative.as_posix(),
                "name": path.name,
                "size": path.stat().st_size,
                "sha256": sha256_file(path),
                **classification,
            }
        )
    return items


def existing_retained(course: dict[str, Any]) -> dict[str, Path]:
    found: dict[str, Path] = {}
    roots = [vault_root() / "attachments", course["folder"] / "textbooks"]
    for root in roots:
        if not root.is_dir():
            continue
        for path in root.iterdir():
            if path.is_file() and path.name != ".gitkeep":
                found[path.name.lower()] = path
                found[sha256_file(path)] = path
    return found


def compare_retained(
    course: dict[str, Any],
    item: dict[str, Any],
) -> dict[str, Any]:
    retained = existing_retained(course)
    suggested = suggested_retain_name(course, item["name"])
    destination_root = (
        course["folder"] / "textbooks"
        if item["action"] == "textbook"
        else vault_root() / "attachments"
    )
    destination = destination_root / suggested
    by_hash = retained.get(item["sha256"])
    by_name = retained.get(suggested.lower()) or retained.get(item["name"].lower())
    if by_hash:
        status = "already_retained"
        match = by_hash
    elif by_name:
        status = "name_conflict"
        match = by_name
    elif destination.exists():
        status = "name_conflict"
        match = destination
    else:
        status = "new"
        match = None
    return {
        "suggested_name": suggested,
        "destination": str(destination),
        "status": status,
        "matched": rel(match) if match else None,
    }


def copy_new_file(source: Path, destination: Path, *, overwrite: bool = False) -> str:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        if sha256_file(source) == sha256_file(destination):
            return rel(destination)
        if not overwrite:
            raise ToolError(f"Refusing to overwrite {rel(destination)}", "safety")
    shutil.copy2(source, destination)
    return rel(destination)


def normalize_markdown(text: str) -> str:
    lines = text.replace("\r\n", "\n").replace("\f", "\n").split("\n")
    counts: dict[str, int] = {}
    for line in lines:
        stripped = line.strip()
        if stripped:
            counts[stripped] = counts.get(stripped, 0) + 1
    kept: list[str] = []
    blank = 0
    for line in lines:
        stripped = line.strip()
        if re.fullmatch(r"\s*\d+\s*", line) or stripped in {"---", "___", "•"}:
            continue
        if stripped and counts.get(stripped, 0) >= 4 and len(stripped) < 80:
            continue
        if not stripped:
            blank += 1
            if blank > 1:
                continue
        else:
            blank = 0
        kept.append(line)
    return "\n".join(kept).strip() + "\n"


def convert_pdf(source: Path, output_name: str | None = None) -> dict[str, Any]:
    ensure_tool("markitdown")
    output_dir = vault_root() / "tools/markitdown/output"
    output_dir.mkdir(parents=True, exist_ok=True)
    destination = output_dir / (output_name or f"{source.stem}.md")
    if destination.exists():
        destination.unlink()
    run_catalog_tool(
        "markitdown",
        [str(source), "-o", str(destination)],
        timeout=180,
        check=True,
    )
    raw = destination.read_text(encoding="utf-8", errors="replace")
    normalized = normalize_markdown(raw)
    destination.write_text(normalized, encoding="utf-8")
    return {
        "source": rel(source),
        "output": rel(destination),
        "characters": len(normalized),
        "page_citations": extract_page_citations(normalized),
        "section_citations": extract_section_citations(normalized),
        "due_hints": extract_due_hints(normalized),
        "due_date": parse_due_date(normalized),
        "text": normalized,
    }


def list_pdf_labels(textbook: Path) -> list[dict[str, str]]:
    ensure_tool("pypdf")
    result = run_catalog_tool(
        "pypdf", [str(textbook), "--list-labels"], timeout=60, check=True
    )
    labels: list[dict[str, str]] = []
    for line in result.stdout.splitlines():
        if "\t" not in line:
            continue
        physical, label = line.split("\t", 1)
        labels.append({"physical": physical.strip(), "label": label.strip()})
    return labels


def extract_printed_pages(
    textbook: Path,
    printed_pages: str,
    output: Path,
) -> dict[str, Any]:
    ensure_tool("pypdf")
    if output.exists():
        raise ToolError(f"Refusing to overwrite {rel(output)}", "safety")
    output.parent.mkdir(parents=True, exist_ok=True)
    run_catalog_tool(
        "pypdf",
        [str(textbook), str(output), "--printed-pages", printed_pages],
        timeout=60,
        check=True,
    )
    return {
        "textbook": rel(textbook),
        "printed_pages": printed_pages,
        "output": rel(output),
        "exists": output.exists(),
    }


def find_section_labels(textbook: Path, section: str) -> list[str]:
    ensure_tool("pypdf")
    result = run_catalog_tool(
        "pypdf",
        [str(textbook), "--find-section", section],
        timeout=120,
        check=True,
    )
    labels = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    return labels


DRIVE_FOLDER_MIME = "application/vnd.google-apps.folder"
DRIVE_NATIVE_EXPORT_PDF = {
    "application/vnd.google-apps.document": "application/pdf",
    "application/vnd.google-apps.spreadsheet": "application/pdf",
    "application/vnd.google-apps.presentation": "application/pdf",
}


def drive_download_plan(file_obj: dict[str, Any]) -> dict[str, Any]:
    mime = str(file_obj.get("mimeType") or "")
    title = str(file_obj.get("title") or "drive-file")
    file_id = file_obj.get("id")
    if mime == DRIVE_FOLDER_MIME:
        return {"action": "skip_folder", "id": file_id, "title": title}
    if mime.endswith("pdf") or title.lower().endswith(".pdf"):
        filename = title if title.lower().endswith(".pdf") else f"{title}.pdf"
        return {
            "action": "download",
            "id": file_id,
            "title": title,
            "filename": filename,
            "exportMimeType": None,
        }
    export = DRIVE_NATIVE_EXPORT_PDF.get(mime)
    if export:
        stem = Path(title).stem if Path(title).suffix else title
        return {
            "action": "download",
            "id": file_id,
            "title": title,
            "filename": f"{stem}.pdf",
            "exportMimeType": export,
        }
    return {"action": "review", "id": file_id, "title": title}


def download_drive_file(
    file_id: str,
    destination: Path,
    *,
    export_mime_type: str | None = None,
) -> dict[str, Any]:
    import base64

    args = ["download_file_content", "--fileId", str(file_id)]
    if export_mime_type:
        args.extend(["--exportMimeType", export_mime_type])
    data = run_json_tool(
        "google_drive",
        args,
        timeout=180,
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(base64.b64decode(data["base64Content"]))
    return {
        "fileId": file_id,
        "path": rel(destination),
        "mimeType": data.get("mimeType"),
        "size": destination.stat().st_size,
    }


def google_status(service: str) -> dict[str, Any]:
    try:
        data = run_json_tool(service, ["ping"])
        return {"ok": True, "authorized": bool(data.get("authorized")), "data": data}
    except ToolError as error:
        return {"ok": False, "authorized": False, "error": error.message, "code": error.code}


def list_drive_children(folder_id: str) -> list[dict[str, Any]]:
    files: list[dict[str, Any]] = []
    token = None
    while True:
        args = [
            "search_files",
            "--query",
            f"parentId = '{folder_id}'",
            "--pageSize",
            "100",
        ]
        if token:
            args.extend(["--pageToken", token])
        data = run_json_tool("google_drive", args)
        files.extend(data.get("files") or [])
        token = data.get("nextPageToken")
        if not token:
            break
    return files


def list_drive_folder(folder_id: str, *, recursive: bool = True) -> dict[str, Any]:
    if not recursive:
        return {"folderId": folder_id, "files": list_drive_children(folder_id)}
    collected: list[dict[str, Any]] = []
    seen: set[str] = set()
    stack = [folder_id]
    while stack:
        current = stack.pop()
        if current in seen:
            continue
        seen.add(current)
        for file_obj in list_drive_children(current):
            collected.append(file_obj)
            child_id = str(file_obj.get("id") or "")
            mime = str(file_obj.get("mimeType") or "")
            if child_id and mime == DRIVE_FOLDER_MIME and child_id not in seen:
                stack.append(child_id)
    return {"folderId": folder_id, "files": collected}


def run_moodle_sync(*, skip_download: bool = False) -> dict[str, Any]:
    ensure_tool("moodle_dl")
    if not moodle_config_exists():
        return {
            "synced": False,
            "needs_user": [
                needs_llm(
                    "moodle_init",
                    command="python tools/run_tool/run_tool.py moodle_dl --init --sso",
                    message="Moodle-DL is not initialized. Run the interactive SSO setup in your own terminal.",
                )
            ],
        }
    if skip_download:
        return {"synced": False, "skipped": True}
    result = run_catalog_tool("moodle_dl", timeout=1800)
    return {
        "synced": result.returncode == 0,
        "returncode": result.returncode,
        "output_tail": (result.stdout or result.stderr)[-1000:],
    }


def split_linter_output(text: str) -> list[str]:
    lines = [line.rstrip() for line in text.splitlines() if line.strip()]
    return lines[:200]


def run_vault_checks() -> dict[str, Any]:
    root = vault_root()
    ensure_tool("pymarkdown")
    ensure_tool("flint")
    ensure_tool("ls_lint")
    python = tool_sentinels()["pymarkdown"]
    checks: dict[str, Any] = {}

    def record(name: str, result: subprocess.CompletedProcess[str], extra_ok: bool = True) -> None:
        output = (result.stdout or "") + ("\n" + result.stderr if result.stderr else "")
        checks[name] = {
            "ok": result.returncode == 0 and extra_ok,
            "returncode": result.returncode,
            "findings": split_linter_output(output),
        }

    record(
        "pymarkdown",
        subprocess.run(
            pymarkdown_argv(
                "--config",
                str(root / ".pymarkdown.yml"),
                "scan",
                "--recurse",
                "--respect-gitignore",
                ".",
            ),
            cwd=root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        ),
    )
    flint = root / "tools/flint/bin/flint.exe"
    flint_result = subprocess.run(
        [str(flint), "--config", str(root / ".flint.yml"), "--color=false", "."],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    flint_text = flint_result.stdout + flint_result.stderr
    flint_has_error = bool(re.search(r"(?m)^\s+\d+:\d+\s+error\s+", flint_text))
    record("flint", flint_result, extra_ok=not flint_has_error)
    validator = subprocess.run(
        [str(python), str(root / "tools/vault_lint/validate_vault.py"), "."],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    record("vault_integrity", validator)
    tests = subprocess.run(
        [str(python), str(root / "tools/vault_lint/test_validate_vault.py")],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    record("rule_tests", tests)
    ls_lint = root / "tools/ls_lint/bin/ls-lint-windows-amd64.exe"
    record(
        "ls_lint",
        subprocess.run(
            [str(ls_lint), "--config", str(root / ".ls-lint.yml"), "--workdir", "."],
            cwd=root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        ),
    )
    failed = [name for name, payload in checks.items() if not payload["ok"]]
    remaining = []
    for name in failed:
        remaining.append(
            needs_llm(
                "lint_finding",
                checker=name,
                message=f"{name} still reports findings",
            )
        )
    return {
        "ok": not failed,
        "failed": failed,
        "checks": checks,
        "needs_llm": remaining,
    }


def autofix_markdown() -> dict[str, Any]:
    ensure_tool("pymarkdown")
    result = subprocess.run(
        pymarkdown_argv(
            "--config",
            str(vault_root() / ".pymarkdown.yml"),
            "fix",
            "--recurse",
            "--respect-gitignore",
            ".",
        ),
        cwd=vault_root(),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
        check=False,
    )
    return {
        "ok": result.returncode == 0,
        "returncode": result.returncode,
        "output": split_linter_output((result.stdout or "") + (result.stderr or "")),
    }


def iter_work_notes() -> list[dict[str, Any]]:
    notes: list[dict[str, Any]] = []
    for course in discover_classes():
        for path in course["work_notes"]:
            metadata = load_frontmatter(path)
            notes.append(
                {
                    "path": rel(path),
                    "class": course["code"],
                    "hyphen": course["hyphen"],
                    "linear": metadata.get("linear"),
                    "linear_url": metadata.get("linear_url"),
                    "kind": metadata.get("kind"),
                    "parent": metadata.get("parent"),
                    "worked": metadata.get("worked"),
                    "forbidden": sorted(
                        field for field in FORBIDDEN_FIELDS if field in metadata
                    ),
                    "metadata": metadata,
                }
            )
    return notes


def paginate_linear(command: str, base_args: list[str], key: str) -> list[Any]:
    items: list[Any] = []
    cursor = None
    for _ in range(20):
        args = [command, *base_args, "--limit", "50"]
        if cursor:
            args.extend(["--cursor", str(cursor)])
        data = run_json_tool("linear", args)
        batch = data.get(key) or []
        items.extend(batch)
        page = data.get("pageInfo") or {}
        if not page.get("hasNextPage"):
            break
        cursor = page.get("endCursor")
        if not cursor:
            break
    return items


def strip_frontmatter_keys(path: Path, keys: list[str]) -> bool:
    text = path.read_text(encoding="utf-8")
    match = FRONTMATTER.match(text)
    if not match:
        return False
    original = match.group(1)
    kept: list[str] = []
    skip_value = False
    changed = False
    for line in original.splitlines():
        if skip_value:
            if line.startswith(" ") or line.startswith("\t"):
                continue
            skip_value = False
        stripped = line.strip()
        if any(stripped == key or stripped.startswith(f"{key}:") for key in keys):
            changed = True
            skip_value = stripped.endswith(":") and stripped.split(":", 1)[1].strip() == ""
            continue
        kept.append(line)
    if not changed:
        return False
    rebuilt = "---\n" + "\n".join(kept).strip() + "\n---\n" + text[match.end() :]
    path.write_text(rebuilt, encoding="utf-8")
    return True


def upsert_frontmatter_key(path: Path, key: str, value: str) -> bool:
    text = path.read_text(encoding="utf-8")
    match = FRONTMATTER.match(text)
    if not match:
        return False
    original = match.group(1)
    if re.search(rf"^{re.escape(key)}:", original, re.M):
        return False
    insertion = f"{key}: {value}"
    updated = original.rstrip() + "\n" + insertion + "\n"
    rebuilt = "---\n" + updated + "---\n" + text[match.end() :]
    path.write_text(rebuilt, encoding="utf-8")
    return True
