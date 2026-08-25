from __future__ import annotations

import difflib
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

import yaml
from gradescopeapi import DEFAULT_GRADESCOPE_BASE_URL
from gradescopeapi.classes.account import Account
from gradescopeapi.classes.connection import GSConnection
from gradescopeapi.classes.upload import upload_assignment as library_upload

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "cli_args"))
import cli_args

CONFIG_KEYS = {
    "email",
    "password",
    "base_url",
    "baseurl",
    "cookies",
    "cookie",
    "cookie_header",
    "cookieheader",
    "session_cookie",
    "sessioncookie",
}
SESSION_ALIASES = ("_gradescope_session", "session_cookie", "sessioncookie", "session")


class ToolError(Exception):
    def __init__(self, message: str, code: str = "api") -> None:
        super().__init__(message)
        self.message = message
        self.code = code


def vault_root() -> Path:
    return Path(__file__).resolve().parents[2]


def env_path() -> Path:
    return vault_root() / ".env.yml"


def load_env() -> dict[str, Any]:
    path = env_path()
    if not path.exists():
        raise ToolError(
            "Missing .env.yml at the vault root. Copy the template keys and add secrets.",
            "missing_secrets",
        )
    loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(loaded, dict):
        raise ToolError(".env.yml must contain a YAML mapping.", "missing_secrets")
    return loaded


def gradescope_section() -> dict[str, Any]:
    section = load_env().get("gradescope") or {}
    if not isinstance(section, dict):
        raise ToolError("gradescope in .env.yml must be a mapping.", "missing_secrets")
    return section


def parse_cookie_header(raw: str) -> dict[str, str]:
    cookies: dict[str, str] = {}
    for part in str(raw).split(";"):
        item = part.strip()
        if not item or "=" not in item:
            continue
        name, value = item.split("=", 1)
        name = name.strip()
        value = value.strip()
        if name and value:
            cookies[name] = value
    return cookies


def cookie_pairs(section: dict[str, Any] | None = None) -> dict[str, str]:
    data = dict(section if section is not None else gradescope_section())
    cookies: dict[str, str] = {}
    for alias in ("cookies", "cookie", "cookie_header", "cookieheader"):
        raw = data.get(alias)
        if isinstance(raw, str) and raw.strip():
            cookies.update(parse_cookie_header(raw))
        elif isinstance(raw, dict):
            for name, value in raw.items():
                text = str(value or "").strip()
                if str(name).strip() and text:
                    cookies[str(name).strip()] = text
    session = ""
    for alias in SESSION_ALIASES:
        session = str(data.get(alias) or "").strip()
        if session:
            cookies["_gradescope_session"] = session
            break
    for name, value in data.items():
        key = str(name).strip()
        if not key or key.lower() in CONFIG_KEYS:
            continue
        if isinstance(value, dict):
            continue
        text = str(value or "").strip()
        if text:
            cookies[key] = text
    return cookies


def cookie_names(section: dict[str, Any] | None = None) -> list[str]:
    return sorted(cookie_pairs(section))


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


def parse_flag_value(raw: str) -> Any:
    return cli_args.parse_flag_value(raw)


def parse_invocation(argv: list[str] | None = None) -> tuple[str, dict[str, Any]]:
    try:
        return cli_args.parse_invocation(
            argv,
            default_command="commands",
            error_class=ToolError,
        )
    except cli_args.CliError as error:
        raise ToolError(error.message, error.code) from error


def emit(payload: dict[str, Any], *, error: bool = False) -> None:
    stream = sys.stderr if error else sys.stdout
    json.dump(payload, stream, indent=2, default=str)
    stream.write("\n")


def isoformat(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def serialize_course(course_id: str, course: Any, role: str, base_url: str) -> dict[str, Any]:
    return {
        "id": str(course_id),
        "role": role,
        "name": getattr(course, "name", None),
        "fullName": getattr(course, "full_name", None),
        "semester": getattr(course, "semester", None),
        "year": getattr(course, "year", None),
        "assignmentCount": getattr(course, "num_assignments", None),
        "url": f"{base_url.rstrip('/')}/courses/{course_id}",
    }


def serialize_assignment(assignment: Any) -> dict[str, Any]:
    return {
        "id": getattr(assignment, "assignment_id", None),
        "name": getattr(assignment, "name", None),
        "releaseDate": isoformat(getattr(assignment, "release_date", None)),
        "dueDate": isoformat(getattr(assignment, "due_date", None)),
        "lateDueDate": isoformat(getattr(assignment, "late_due_date", None)),
        "submissionsStatus": getattr(assignment, "submissions_status", None),
        "grade": getattr(assignment, "grade", None),
        "maxGrade": getattr(assignment, "max_grade", None),
    }


def serialize_member(member: Any) -> dict[str, Any]:
    return {
        "fullName": getattr(member, "full_name", None),
        "firstName": getattr(member, "first_name", None),
        "lastName": getattr(member, "last_name", None),
        "sid": getattr(member, "sid", None),
        "email": getattr(member, "email", None),
        "role": getattr(member, "role", None),
        "userId": getattr(member, "user_id", None),
        "numSubmissions": getattr(member, "num_submissions", None),
        "sections": getattr(member, "sections", None),
        "courseId": getattr(member, "course_id", None),
    }


def apply_cookies(session: Any, cookies: dict[str, str], base_url: str) -> None:
    host = base_url.split("://", 1)[-1].split("/", 1)[0]
    domains = [host]
    if host.startswith("www."):
        domains.append(host[4:])
    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/128.0.0.0 Safari/537.36"
            )
        }
    )
    for domain in domains:
        for name, value in cookies.items():
            session.cookies.set(name, value, domain=domain, path="/")
    session.headers["Cookie"] = "; ".join(
        f"{name}={value}" for name, value in cookies.items()
    )


def connect() -> GSConnection:
    section = gradescope_section()
    base_url = str(section.get("base_url") or DEFAULT_GRADESCOPE_BASE_URL).rstrip("/")
    cookies = cookie_pairs(section)
    connection = GSConnection(gradescope_base_url=base_url)
    if cookies:
        apply_cookies(connection.session, cookies, base_url)
        connection.logged_in = True
        connection.account = Account(connection.session, base_url)
        return connection
    email = str(section.get("email") or "").strip()
    password = str(section.get("password") or "").strip()
    if email and password:
        connection.login(email, password)
        return connection
    raise ToolError(
        "Set gradescope cookie values in .env.yml "
        "(_gradescope_session, remember_me, signed_token) "
        "or gradescope.email and gradescope.password.",
        "missing_secrets",
    )


def account_or_raise() -> tuple[GSConnection, Any]:
    connection = connect()
    if connection.account is None:
        raise ToolError("Gradescope session is not authenticated.", "needs_auth")
    response = connection.session.get(f"{connection.gradescope_base_url}/account")
    url = str(response.url or "")
    if response.status_code in {401, 403} or "/login" in url:
        raise ToolError(
            "Gradescope cookies are missing or expired. Update gradescope.* in .env.yml.",
            "needs_auth",
        )
    return connection, connection.account


def ping(_: dict[str, Any] | None = None) -> dict[str, Any]:
    names = cookie_names()
    payload: dict[str, Any] = {
        "service": "gradescope",
        "cookieNames": names,
        "cookieCount": len(names),
        "authorized": False,
    }
    if not names:
        payload["error"] = "Set gradescope cookies in .env.yml."
        return payload
    try:
        courses = get_courses({})
        payload["authorized"] = True
        payload["studentCourseCount"] = len(courses.get("student") or [])
        payload["instructorCourseCount"] = len(courses.get("instructor") or [])
    except ToolError as error:
        payload["authorized"] = False
        payload["error"] = error.message
        if error.code != "needs_auth":
            raise
    return payload


def get_courses(_: dict[str, Any] | None = None) -> dict[str, Any]:
    connection, account = account_or_raise()
    raw = account.get_courses() or {}
    grouped: dict[str, list[dict[str, Any]]] = {"student": [], "instructor": []}
    for role in ("student", "instructor"):
        items = raw.get(role) or {}
        if isinstance(items, dict):
            for course_id, course in items.items():
                grouped[role].append(
                    serialize_course(
                        str(course_id),
                        course,
                        role,
                        connection.gradescope_base_url,
                    )
                )
    return grouped


def get_assignments(payload: dict[str, Any]) -> dict[str, Any]:
    course_id = str(get_value(payload, "courseId", "course_id", "id", required=True))
    _, account = account_or_raise()
    assignments = [serialize_assignment(item) for item in account.get_assignments(course_id) or []]
    return {"courseId": course_id, "assignments": assignments}


def get_course_users(payload: dict[str, Any]) -> dict[str, Any]:
    course_id = str(get_value(payload, "courseId", "course_id", "id", required=True))
    _, account = account_or_raise()
    members = account.get_course_users(course_id) or []
    return {
        "courseId": course_id,
        "users": [serialize_member(member) for member in members],
    }


def upload_assignment(payload: dict[str, Any]) -> dict[str, Any]:
    course_id = str(get_value(payload, "courseId", "course_id", required=True))
    assignment_id = str(
        get_value(payload, "assignmentId", "assignment_id", required=True)
    )
    files = [Path(str(item)) for item in as_list(get_value(payload, "files", "file"))]
    if not files:
        raise ToolError("Pass --files with at least one local path.", "usage")
    missing = [str(path) for path in files if not path.exists()]
    if missing:
        raise ToolError(f"Missing upload files: {missing}", "usage")
    connection, _ = account_or_raise()
    handles = [path.open("rb") for path in files]
    try:
        url = library_upload(
            connection.session,
            course_id,
            assignment_id,
            *handles,
            leaderboard_name=get_value(payload, "leaderboardName", "leaderboard_name"),
            gradescope_base_url=connection.gradescope_base_url,
        )
    finally:
        for handle in handles:
            handle.close()
    if not url:
        raise ToolError(
            "Gradescope rejected the upload. The assignment may be closed or the files invalid.",
            "api",
        )
    return {
        "courseId": course_id,
        "assignmentId": assignment_id,
        "url": url,
        "files": [path.name for path in files],
    }


def commands() -> dict[str, Callable[[dict[str, Any]], Any]]:
    return {
        "ping": ping,
        "get_courses": get_courses,
        "list_courses": get_courses,
        "get_assignments": get_assignments,
        "list_assignments": get_assignments,
        "get_course_users": get_course_users,
        "upload_assignment": upload_assignment,
    }


def run_cli(argv: list[str] | None = None) -> int:
    command = None
    try:
        command, payload = parse_invocation(argv)
        table = commands()
        if command in {"help", "commands", "-h", "--help"}:
            emit(
                {
                    "ok": True,
                    "command": "commands",
                    "data": {
                        "program": "gradescope",
                        "commands": sorted({"commands", *table}),
                        "invoke": [
                            "python tools/run_tool/run_tool.py gradescope commands",
                            "python tools/run_tool/run_tool.py gradescope get_courses",
                            "Always use flags. Never write scratch files.",
                        ],
                    },
                }
            )
            return 0
        handler = table.get(command)
        if handler is None:
            known = sorted({"commands", *table})
            message = f"Unknown command: {command}. Known: {', '.join(known)}."
            close = difflib.get_close_matches(str(command or ""), known, n=3, cutoff=0.5)
            if close:
                message += f" Did you mean {', '.join(close)}?"
            message += (
                ' Example: python tools/run_tool/run_tool.py gradescope get_courses'
            )
            raise ToolError(message, "usage")
        emit({"ok": True, "command": command, "data": handler(payload)})
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


def main(argv: list[str] | None = None) -> int:
    return run_cli(argv)


if __name__ == "__main__":
    raise SystemExit(main())
