from __future__ import annotations

import inspect
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "cli_args"))
import cli_args

TEXT_LIMIT = 20000
DEFAULT_PORT = 9222
DEFAULT_HELIUM = Path(r"C:\Program Files\imput\Helium\Application\chrome.exe")
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
    return cli_args.parse_flag_value(raw)


def parse_invocation(argv: list[str] | None = None) -> tuple[str, dict[str, Any]]:
    try:
        return cli_args.parse_invocation(
            argv,
            default_command="ping",
            error_class=ToolError,
        )
    except cli_args.CliError as error:
        raise ToolError(error.message, error.code) from error


def chrome_hint(error: Exception) -> str:
    text = str(error)
    lowered = text.lower()
    if "winerror 2" in lowered or "cannot find the file specified" in lowered:
        return (
            "No Chromium browser was found. Expected Helium at "
            f"{DEFAULT_HELIUM}. Pass --binary or set HELIUM_BROWSER."
        )
    return text


def browser_candidates(explicit: str | None = None) -> list[Path]:
    paths: list[Path] = []
    if explicit:
        paths.append(Path(explicit))
    env = os.environ.get("HELIUM_BROWSER") or os.environ.get("CHROME_BINARY")
    if env:
        paths.append(Path(env))
    program_files = Path(os.environ.get("PROGRAMFILES", r"C:\Program Files"))
    local_app = Path(os.environ.get("LOCALAPPDATA", ""))
    paths.extend(
        [
            DEFAULT_HELIUM,
            program_files / "imput" / "Helium" / "Application" / "chrome.exe",
            program_files / "Google" / "Chrome" / "Application" / "chrome.exe",
            local_app / "Google" / "Chrome" / "Application" / "chrome.exe",
        ]
    )
    seen: set[str] = set()
    unique: list[Path] = []
    for path in paths:
        key = str(path).lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(path)
    return unique


def find_browser_binary(explicit: str | None = None) -> Path:
    for path in browser_candidates(explicit):
        if path.is_file():
            return path
    raise ToolError(
        "No Chromium browser was found. Expected Helium at "
        f"{DEFAULT_HELIUM}. Pass --binary or set HELIUM_BROWSER.",
        "tool",
    )


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
            "This URL's host starts with moodle. Use fast_moodle_dl, not Selenium.",
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
        "binary",
        "headless",
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


class VaultDriver:
    def __init__(self, driver: Any) -> None:
        self.driver = driver

    def ensure_driver_initialized(self) -> Any:
        return self.driver

    def _recover_window_handle(self) -> None:
        driver = self.driver
        if driver is None:
            return
        try:
            _ = driver.title
            return
        except Exception:
            pass
        handles = list(getattr(driver, "window_handles", []) or [])
        if handles:
            driver.switch_to.window(handles[-1])

    def quit(self) -> None:
        if self.driver is None:
            return
        try:
            self.driver.quit()
        finally:
            self.driver = None


def start_webdriver(payload: dict[str, Any]) -> Any:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options

    binary = find_browser_binary(
        str(payload["binary"]) if payload.get("binary") else None
    )
    data_dir = Path(str(payload.get("user_data_dir") or (state_dir() / "chrome-profile")))
    data_dir.mkdir(parents=True, exist_ok=True)
    options = Options()
    options.binary_location = str(binary)
    options.add_argument(f"--user-data-dir={data_dir}")
    options.add_argument("--remote-allow-origins=*")
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")
    options.add_argument("--disable-dev-shm-usage")
    headless = payload.get("headless")
    if headless is True or str(headless).strip().lower() in {"true", "yes", "1"}:
        options.add_argument("--headless=new")
    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(120)
    driver.set_script_timeout(120)
    driver._vault_browser = str(binary)
    return driver


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
    server.download_directory = output_dir() / "downloads"
    attached = getattr(server.driver_instance, "driver", None)
    if attached is None:
        driver = start_webdriver(payload)
        server.driver_instance = VaultDriver(driver)
        configure = getattr(server, "configure_download_directory", None)
        if callable(configure):
            configure(driver)
    return server.ensure_driver_initialized()


def compact_fns() -> dict[str, Callable[..., Any]]:
    try:
        from mcp_server_selenium.tools import compact

        return {name: getattr(compact, name) for name in COMPACT_COMMANDS}
    except ImportError:
        from mcp_server_selenium.tools import navigate, page_ready, screenshot, script, tabs

        return {
            "tabs": tabs.list_tabs,
            "navigate": navigate.navigate,
            "wait_for": page_ready.check_page_ready,
            "take_screenshot": screenshot.take_screenshot,
            "run_javascript": script.run_javascript_in_console,
        }


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
    try:
        binary = str(find_browser_binary())
        browser_ok = True
    except ToolError:
        binary = str(DEFAULT_HELIUM)
        browser_ok = False
    return {
        "ok": True,
        "tool": "selenium",
        "driver": "helium",
        "browser": binary,
        "browser_found": browser_ok,
        "engine": "helium" if "Helium" in binary else "chromium",
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
    if payload.get("headless") is None:
        payload = {**payload, "headless": True}
    driver = ensure_session(payload)
    driver.set_page_load_timeout(timeout)
    driver.get(url)
    navigation = {
        "ok": True,
        "requested_url": url,
        "wait_until": wait_until,
        "browser": getattr(driver, "_vault_browser", None),
    }
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
        shot_dir = output_dir() / "screenshots"
        shot_dir.mkdir(parents=True, exist_ok=True)
        shot_path = shot_dir / f"{slug}.png"
        driver.save_screenshot(str(shot_path))
        screenshot_result = {"path": str(shot_path)}
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
        "browser": getattr(driver, "_vault_browser", None),
        "moodle": False,
    }


def commands(_: dict[str, Any]) -> dict[str, Any]:
    return {
        "program": "selenium",
        "commands": [
            "commands",
            "ping",
            "start",
            "stop",
            "fetch",
            *COMPACT_COMMANDS,
        ],
        "invoke": [
            "python tools/run_tool/run_tool.py selenium commands",
            'python tools/run_tool/run_tool.py selenium fetch --url "https://example.com"',
            "Always use flags. Never write scratch files.",
        ],
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
                'Example: python tools/run_tool/run_tool.py selenium fetch --url "https://example.com"',
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
