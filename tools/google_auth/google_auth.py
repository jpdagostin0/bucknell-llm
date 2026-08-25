from __future__ import annotations

import difflib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Callable

import yaml
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "cli_args"))
import cli_args

HELP_TOKENS = cli_args.HELP_TOKENS
CLI_SHELL_RULE = cli_args.ARGUMENT_RULE

SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.labels",
    "https://www.googleapis.com/auth/gmail.settings.basic",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/calendar.events",
]


class ToolError(Exception):
    def __init__(self, message: str, code: str = "api") -> None:
        super().__init__(message)
        self.message = message
        self.code = code


def vault_root() -> Path:
    return Path(__file__).resolve().parents[2]


def tool_state_dir() -> Path:
    path = Path(__file__).resolve().parent / "state"
    path.mkdir(parents=True, exist_ok=True)
    return path


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


def google_section() -> dict[str, Any]:
    section = load_env().get("google") or {}
    if not isinstance(section, dict):
        raise ToolError("google in .env.yml must be a mapping.", "missing_secrets")
    return section


def linear_api_key() -> str:
    section = load_env().get("linear") or {}
    if not isinstance(section, dict):
        raise ToolError("linear in .env.yml must be a mapping.", "missing_secrets")
    key = str(section.get("api_key") or "").strip()
    if not key:
        raise ToolError("Set linear.api_key in .env.yml.", "missing_secrets")
    return key


def google_client_config() -> dict[str, str]:
    section = google_section()
    secrets = section.get("client_secrets")
    installed: dict[str, Any] = {}
    if isinstance(secrets, dict):
        block = secrets.get("installed") or secrets.get("web") or secrets
        if isinstance(block, dict):
            installed = block
    client_id = str(
        section.get("client_id") or installed.get("client_id") or ""
    ).strip()
    client_secret = str(
        section.get("client_secret") or installed.get("client_secret") or ""
    ).strip()
    project_id = str(
        section.get("project_id") or installed.get("project_id") or ""
    ).strip()
    if not client_id or not client_secret:
        raise ToolError(
            "Set google.client_id and google.client_secret in .env.yml "
            "(shared by Drive, Gmail, and Calendar).",
            "missing_secrets",
        )
    return {
        "client_id": client_id,
        "client_secret": client_secret,
        "project_id": project_id,
        "auth_uri": str(
            installed.get("auth_uri") or "https://accounts.google.com/o/oauth2/auth"
        ),
        "token_uri": str(
            installed.get("token_uri") or "https://oauth2.googleapis.com/token"
        ),
        "revoke_uri": str(
            installed.get("revoke_uri") or "https://oauth2.googleapis.com/revoke"
        ),
        "redirect_uri": "http://localhost:8080/",
        "email": str(section.get("email") or "").strip(),
    }


def token_path() -> Path:
    return tool_state_dir() / "google_token.json"


def load_credentials(*, interactive: bool = False) -> Credentials:
    config = google_client_config()
    creds: Credentials | None = None
    if token_path().exists():
        creds = Credentials.from_authorized_user_file(str(token_path()), SCOPES)
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        save_credentials(creds)
    if creds and creds.valid:
        return creds
    if not interactive:
        raise ToolError(
            "Google OAuth token is missing or expired. "
            "Run python tools/run_tool/run_tool.py google_auth login",
            "needs_auth",
        )
    flow = InstalledAppFlow.from_client_config(
        {
            "installed": {
                "client_id": config["client_id"],
                "client_secret": config["client_secret"],
                "auth_uri": config["auth_uri"],
                "token_uri": config["token_uri"],
                "redirect_uris": ["http://localhost:8080/"],
            }
        },
        SCOPES,
    )
    creds = flow.run_local_server(port=8080, prompt="consent")
    save_credentials(creds)
    return creds


def save_credentials(creds: Credentials) -> None:
    token_path().write_text(creds.to_json(), encoding="utf-8")


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
        raise ToolError(
            f"Missing required argument: {names[0]}",
            "usage",
        )
    return default


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


def command_names(commands: dict[str, Any]) -> list[str]:
    return sorted({"commands", *commands})


def catalog_payload(
    program: str,
    commands: dict[str, Any],
    example: str = "ping",
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "program": program,
        "commands": command_names(commands),
        "invoke": [
            f"python tools/run_tool/run_tool.py {program} commands",
            f"python tools/run_tool/run_tool.py {program} {example}".rstrip(),
            "Always use flags. Never write scratch files.",
        ],
    }
    return payload


def unknown_command_error(
    command: str | None,
    commands: dict[str, Any],
    program: str,
    example: str = "ping",
) -> ToolError:
    known = command_names(commands)
    message = f"Unknown command: {command}. Known: {', '.join(known)}."
    close = difflib.get_close_matches(str(command or ""), known, n=3, cutoff=0.5)
    if close:
        message += f" Did you mean {', '.join(close)}?"
    message += (
        f' Example: python tools/run_tool/run_tool.py {program} {example}'.rstrip()
    )
    return ToolError(message, "usage")


def emit(payload: dict[str, Any], *, error: bool = False) -> None:
    stream = sys.stderr if error else sys.stdout
    json.dump(payload, stream, indent=2, default=str)
    stream.write("\n")


def run_cli(
    program: str,
    commands: dict[str, Callable[[dict[str, Any]], Any]],
    argv: list[str] | None = None,
    example: str = "ping",
) -> int:
    command = None
    try:
        command, payload = parse_invocation(argv)
        if command in HELP_TOKENS:
            emit(
                {
                    "ok": True,
                    "command": "commands",
                    "data": catalog_payload(program, commands, example=example),
                }
            )
            return 0
        handler = commands.get(command)
        if handler is None:
            raise unknown_command_error(command, commands, program, example=example)
        data = handler(payload)
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
                "error": {"code": "api", "message": str(error)},
            },
            error=True,
        )
        return 1


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def ping(_: dict[str, Any] | None = None) -> dict[str, Any]:
    config = google_client_config()
    token_exists = token_path().exists()
    authorized = False
    email = config.get("email") or None
    if token_exists:
        try:
            creds = load_credentials(interactive=False)
            authorized = bool(creds.valid)
        except ToolError:
            authorized = False
    return {
        "service": "google",
        "client_id_suffix": config["client_id"][-12:],
        "email": email,
        "token_present": token_exists,
        "authorized": authorized,
        "scopes": SCOPES,
        "env_file": str(env_path()),
    }


def login(_: dict[str, Any] | None = None) -> dict[str, Any]:
    creds = load_credentials(interactive=True)
    return {
        "authorized": bool(creds.valid),
        "token": str(token_path()),
        "scopes": list(creds.scopes or SCOPES),
    }


def google_commands() -> dict[str, Callable[[dict[str, Any]], Any]]:
    return {"ping": ping, "login": login}


def main() -> int:
    os.environ.setdefault("OAUTHLIB_RELAX_TOKEN_SCOPE", "1")
    return run_cli("google_auth", google_commands(), example="login")


if __name__ == "__main__":
    raise SystemExit(main())
