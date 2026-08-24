from __future__ import annotations

import argparse
import inspect
import json
import re
import sys
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

TEXT_LIMIT = 20000
DEFAULT_PORT = 9222
COMPACT_COMMANDS = (
    "tabs",
    "navigate",
    "wait_for",
    "query_elements",
    "interact_element",
    "take_screenshot",
    "browser_logs",
    "local_storage",
    "get_element_style",
    "run_javascript",
)


class ToolError(Exception):
    def __init__(self, message: str, code: str = "usage") -> None:
        super().__init__(message)
        self.message = message
        self.code = code


def vault_root() -> Path:
    return Path(__file__).resolve().parents[2]


def tool_root() -> Path:
    return Path(__file__).resolve().parent


def state_dir() -> Path:
    return tool_root() / "state"


def output_dir() -> Path:
    return tool_root() / "output"


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
            raise ToolError(f"Unexpected argument: {token}", "usage")
        payload[key] = parse_flag_value(token)
        key = None
    if key is not None:
        payload[key] = True
    return str(parsed.command), payload


def chrome_hint(error: Exception) -> str:
    text = str(error)
    lowered = text.lower()
    if "winerror 2" in lowered or "cannot find the file specified" in lowered:
        return (
            "Chrome was not found. Install Google Chrome and ensure chrome.exe is "
            "on PATH, then retry. Selenium does not use Moodle-DL."
        )
    return text


def emit(payload: dict[str, Any], *, error: bool = False) -> None:
    stream = sys.stderr if error else sys.stdout
    json.dump(payload, stream, indent=2)
    stream.write("\n")


def is_moodle_url(url: str) -> bool:
    raw = str(url or "").strip()
    if not raw:
        return False
    parsed = urlparse(raw if "://" in raw else f"https://{raw}")
    host = (parsed.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    return host.startswith("moodle")


def require_http_url(url: str) -> str:
    raw = str(url or "").strip()
    if not raw:
        raise ToolError("url is required.", "usage")
    parsed = urlparse(raw if "://" in raw else f"https://{raw}")
    if parsed.scheme not in {"http", "https"}:
        raise ToolError("Only http and https URLs are allowed.", "safety")
    if not parsed.netloc:
        raise ToolError("url must include a host.", "usage")
    normalized = raw if "://" in raw else f"https://{raw}"
    if is_moodle_url(normalized):
        raise ToolError(
            "This URL's host starts with moodle. Use moodle-dl, not Selenium.",
            "routing",
        )
    return normalized


def page_slug(url: str, name: str | None = None) -> str:
    if name:
        slug = re.sub(r"[^A-Za-z0-9._-]+", "-", str(name).strip()).strip("-")
        if slug:
            return slug[:80]
    parsed = urlparse(url)
    host = (parsed.hostname or "page").replace(".", "-")
    path = re.sub(r"[^A-Za-z0-9]+", "-", parsed.path).strip("-") or "index"
    return f"{host}-{path}"[:80]


def filter_kwargs(fn: Callable[..., Any], payload: dict[str, Any]) -> dict[str, Any]:
    accepted = set(inspect.signature(fn).parameters)
    ignored = {
        "user_data_dir",
        "port",
        "profile",
        "driver",
        "quit",
        "screenshot",
        "include_html",
        "name",
        "class",
        "course",
    }
    return {
        key: value
        for key, value in payload.items()
        if key in accepted and key not in ignored
    }


def coerce_selector(value: Any) -> Any:
    if not isinstance(value, dict):
        return value
    from pydantic import TypeAdapter
    from mcp_server_selenium.tools.compact_models import Selector

    return TypeAdapter(Selector).validate_python(value)


def decode_result(raw: Any) -> Any:
    if isinstance(raw, (dict, list)):
        return raw
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"text": raw}
    return raw


def ensure_output_dirs() -> None:
    for path in (
        state_dir(),
        output_dir(),
        output_dir() / "downloads",
        output_dir() / "screenshots",
        output_dir() / "pages",
    ):
        path.mkdir(parents=True, exist_ok=True)


def ensure_session(payload: dict[str, Any] | None = None) -> Any:
    payload = payload or {}
    ensure_output_dirs()
    from mcp_server_selenium import server

    server.workspace_root = vault_root()
    data_dir = Path(str(payload.get("user_data_dir") or (state_dir() / "chrome-profile")))
    data_dir.mkdir(parents=True, exist_ok=True)
    server.user_data_dir = str(data_dir)
    server.debug_port = int(payload.get("port") or DEFAULT_PORT)
    if payload.get("profile"):
        server.profile = str(payload["profile"])
    if payload.get("driver"):
        server.driver_type = str(payload["driver"])
    server.download_directory = output_dir() / "downloads"
    if server.driver_instance is None:
        server.initialize_driver_instance()
    return server.ensure_driver_initialized()


def compact_fns() -> dict[str, Callable[..., Any]]:
    from mcp_server_selenium.tools import compact

    return {name: getattr(compact, name) for name in COMPACT_COMMANDS}


def compact_call(name: str, payload: dict[str, Any]) -> Any:
    ensure_session(payload)
    fn = compact_fns()[name]
    args = filter_kwargs(fn, payload)
    if "selector" in args:
        args["selector"] = coerce_selector(args["selector"])
    if name == "navigate":
        url = args.get("url") or payload.get("url")
        args["url"] = require_http_url(str(url or ""))
    return decode_result(fn(**args))


def ping(_: dict[str, Any]) -> dict[str, Any]:
    import mcp_server_selenium

    return {
        "ok": True,
        "tool": "selenium",
        "package": "mcp-server-selenium",
        "module": mcp_server_selenium.__name__,
        "chrome": "required",
    }


def start(payload: dict[str, Any]) -> dict[str, Any]:
    driver = ensure_session(payload)
    return {
        "ok": True,
        "session": True,
        "current_url": getattr(driver, "current_url", ""),
        "profile": str(state_dir() / "chrome-profile"),
    }


def stop(_: dict[str, Any]) -> dict[str, Any]:
    from mcp_server_selenium.server import quit_driver

    quit_driver()
    return {"ok": True, "session": False}


def fetch(payload: dict[str, Any]) -> dict[str, Any]:
    url = require_http_url(str(payload.get("url") or ""))
    wait_until = str(payload.get("wait_until") or "complete")
    timeout = float(payload.get("timeout") or 60)
    include_html = payload.get("include_html", True)
    screenshot = payload.get("screenshot", True)
    slug = page_slug(url, payload.get("name") if isinstance(payload.get("name"), str) else None)
    driver = ensure_session(payload)
    from mcp_server_selenium.tools.compact import navigate, take_screenshot

    navigation = decode_result(
        navigate(url=url, wait_until=wait_until, timeout=timeout)
    )
    title = str(getattr(driver, "title", "") or "")
    final_url = str(getattr(driver, "current_url", "") or url)
    text = str(driver.execute_script("return document.body ? document.body.innerText : '';") or "")
    html = str(getattr(driver, "page_source", "") or "")
    pages = output_dir() / "pages"
    pages.mkdir(parents=True, exist_ok=True)
    text_path = pages / f"{slug}.txt"
    text_path.write_text(text, encoding="utf-8")
    html_path = None
    if include_html is not False:
        html_path = pages / f"{slug}.html"
        html_path.write_text(html, encoding="utf-8")
    screenshot_result = None
    if screenshot is not False:
        screenshot_result = decode_result(
            take_screenshot(
                file_name=slug,
                directory=str(output_dir() / "screenshots"),
                mode=str(payload.get("mode") or "viewport"),
            )
        )
    if payload.get("quit"):
        stop({})
    return {
        "ok": True,
        "requested_url": url,
        "final_url": final_url,
        "title": title,
        "navigation": navigation,
        "text": text[:TEXT_LIMIT],
        "text_truncated": len(text) > TEXT_LIMIT,
        "text_path": str(text_path),
        "html_path": str(html_path) if html_path else None,
        "screenshot": screenshot_result,
        "moodle": False,
    }


def commands(_: dict[str, Any]) -> dict[str, Any]:
    return {
        "commands": [
            "commands",
            "ping",
            "start",
            "stop",
            "fetch",
            *COMPACT_COMMANDS,
        ],
        "package": "mcp-server-selenium==0.1.8",
        "routing": (
            "If a URL's host does not start with moodle, do not use moodle-dl. "
            "Use selenium fetch instead."
        ),
    }


HANDLERS: dict[str, Callable[[dict[str, Any]], Any]] = {
    "ping": ping,
    "start": start,
    "stop": stop,
    "fetch": fetch,
    "commands": commands,
}


def main(argv: list[str] | None = None) -> int:
    try:
        command, payload = parse_invocation(argv)
        if command in COMPACT_COMMANDS:
            data = compact_call(command, payload)
            emit({"ok": True, "command": command, "data": data})
            return 0
        handler = HANDLERS.get(command)
        if handler is None:
            known = sorted({"commands", *HANDLERS, *COMPACT_COMMANDS})
            raise ToolError(
                f"Unknown command: {command}. Known: {', '.join(known)}. "
                "Discover commands with `commands` or `--help`.",
                "usage",
            )
        data = handler(payload)
        emit({"ok": True, "command": command, "data": data})
        return 0
    except ToolError as error:
        emit(
            {
                "ok": False,
                "command": locals().get("command"),
                "error": {"code": error.code, "message": error.message},
            },
            error=True,
        )
        return 1
    except Exception as error:
        emit(
            {
                "ok": False,
                "command": locals().get("command"),
                "error": {"code": "api", "message": chrome_hint(error)},
            },
            error=True,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
