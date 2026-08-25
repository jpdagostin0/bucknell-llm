from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


class ToolError(Exception):
    def __init__(self, message: str, code: str = "usage") -> None:
        super().__init__(message)
        self.message = message
        self.code = code


def vault_root() -> Path:
    return Path(__file__).resolve().parents[2]


HOST_IO_RULE = (
    "Always call python tools/run_tool/run_tool.py <tool> ... with forward slashes. "
    "Always use --flag value. Repeat a flag for lists. Never write a session script. "
    "Never write scratch files to .lmstudio/scratchpads, C:/tmp, /inputs, or /outputs. "
    "Read JSON from stdout."
)
EMULATED_PYTHON_MESSAGE = (
    "This CLI cannot run in an in-memory Python sandbox. "
    "Always use a real python.exe: python tools/run_tool/run_tool.py <tool> ..."
)


def is_emulated_python() -> bool:
    if "pyodide" in sys.modules:
        return True
    return getattr(sys, "platform", "") in {"emscripten", "wasi"}


def require_host_python() -> None:
    if is_emulated_python():
        raise ToolError(EMULATED_PYTHON_MESSAGE, "tool")


def emit_error(message: str, code: str = "usage", *, invoke: list[str] | None = None) -> int:
    payload: dict[str, Any] = {"ok": False, "error": {"code": code, "message": message}}
    if invoke:
        payload["error"]["invoke"] = invoke
    json.dump(payload, sys.stderr, indent=2)
    sys.stderr.write("\n")
    return 1


def find_node(root: Path) -> Path:
    from install_env import InstallError, find_node as locate_node

    try:
        return locate_node(root)
    except InstallError as error:
        raise ToolError(error.message, "tool") from error


def pymarkdown_python(root: Path) -> Path:
    path = root / "tools" / "pymarkdown" / ".venv" / "Scripts" / "python.exe"
    if path.is_file():
        return path
    which = shutil.which("python")
    if which:
        return Path(which)
    return Path(sys.executable)


def venv_python(root: Path, tool: str) -> Path:
    return root / "tools" / tool / ".venv" / "Scripts" / "python.exe"


def entry_argv(python: Path, entry: str, argv0: str, extra: list[str]) -> list[str]:
    """Launch a console-script entry point without a uv trampoline .exe."""
    module, function = entry.split(":", 1)
    code = (
        "import sys; "
        f"from {module} import {function} as _run; "
        "args = sys.argv[1:]; "
        "args = args[1:] if args[:1] == ['--'] else args; "
        f"sys.argv = [{argv0!r}, *args]; "
        "raise SystemExit(_run())"
    )
    return [str(python), "-c", code, "--", *extra]


def require_file(path: Path, install: str) -> Path:
    if not path.exists():
        raise ToolError(f"Missing {path}. Run {install} first.", "tool")
    return path


FRONTMATTER = re.compile(r"\A---\r?\n(.*?)\r?\n---", re.S)
FALSEY = {"false", "no", "0", "off"}


def _readme_fields(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    match = FRONTMATTER.match(path.read_text(encoding="utf-8"))
    if not match:
        return {}
    fields: dict[str, str] = {}
    for line in match.group(1).splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or ":" not in stripped:
            continue
        key, raw = stripped.split(":", 1)
        fields[key.strip()] = raw.strip().strip("\"'")
    return fields


def _truthy_field(fields: dict[str, str], key: str, default: bool = True) -> bool:
    if key not in fields:
        return default
    return fields[key].lower() not in FALSEY


def discover_python_tools(root: Path, catalog: dict[str, dict[str, Any]]) -> None:
    tools_dir = root / "tools"
    if not tools_dir.is_dir():
        return
    fast_path = str(root / "tools" / "fast_common")
    python = pymarkdown_python(root)
    for folder in sorted(tools_dir.iterdir()):
        name = folder.name
        if not folder.is_dir() or name in catalog:
            continue
        script = folder / f"{name}.py"
        readme = folder / "README.md"
        if not script.is_file() or not readme.is_file():
            continue
        fields = _readme_fields(readme)
        if fields.get("type") != "tool" or not _truthy_field(fields, "invoke"):
            continue
        spec: dict[str, Any] = {
            "kind": "python",
            "python": python,
            "script": script,
            "install": "python tools/pymarkdown/install.py",
        }
        if name.startswith("fast_"):
            spec["pythonpath"] = fast_path
        catalog[name] = spec


def tool_catalog(root: Path) -> dict[str, dict[str, Any]]:
    google_auth = str(root / "tools" / "google_auth")
    fast_path = str(root / "tools" / "fast_common")
    fast_python = pymarkdown_python(root)
    catalog: dict[str, dict[str, Any]] = {
        "linear": {
            "kind": "node",
            "script": root / "tools" / "linear" / "linear_cli.js",
            "need": root / "tools" / "linear" / "node_modules" / "@linear" / "sdk",
            "install": "python tools/linear/install.py",
        },
        "gmail": {
            "kind": "python",
            "python": root / "tools" / "gmail" / ".venv" / "Scripts" / "python.exe",
            "script": root / "tools" / "gmail" / "gmail.py",
            "pythonpath": google_auth,
            "install": "python tools/gmail/install.py",
        },
        "google_drive": {
            "kind": "python",
            "python": root / "tools" / "google_drive" / ".venv" / "Scripts" / "python.exe",
            "script": root / "tools" / "google_drive" / "google_drive.py",
            "pythonpath": google_auth,
            "install": "python tools/google_drive/install.py",
        },
        "google_calendar": {
            "kind": "python",
            "python": root / "tools" / "google_calendar" / ".venv" / "Scripts" / "python.exe",
            "script": root / "tools" / "google_calendar" / "google_calendar.py",
            "pythonpath": google_auth,
            "install": "python tools/google_calendar/install.py",
        },
        "google_auth": {
            "kind": "python",
            "python": root / "tools" / "google_auth" / ".venv" / "Scripts" / "python.exe",
            "script": root / "tools" / "google_auth" / "google_auth.py",
            "pythonpath": str(root / "tools" / "google_auth"),
            "install": "python tools/google_auth/install.py",
        },
        "moodle_dl": {
            "kind": "entry",
            "python": venv_python(root, "moodle_dl"),
            "entry": "moodle_dl.main:main",
            "argv0": "moodle-dl",
            "install": "python tools/moodle_dl/install.py",
            "ensure_dir": root / "tools" / "moodle_dl" / "state",
            "extra_unless": "--path",
            "extra_args": ["--path", str(root / "tools" / "moodle_dl" / "state")],
        },
        "markitdown": {
            "kind": "module",
            "python": venv_python(root, "markitdown"),
            "module": "markitdown",
            "install": "python tools/markitdown/install.py",
        },
        "pypdf": {
            "kind": "python",
            "python": root / "tools" / "pypdf" / ".venv" / "Scripts" / "python.exe",
            "script": root / "tools" / "pypdf" / "extract_pages.py",
            "install": "python tools/pypdf/install.py",
        },
        "gradescope": {
            "kind": "python",
            "python": root / "tools" / "gradescope" / ".venv" / "Scripts" / "python.exe",
            "script": root / "tools" / "gradescope" / "gradescope.py",
            "install": "python tools/gradescope/install.py",
        },
        "selenium": {
            "kind": "python",
            "python": root / "tools" / "selenium" / ".venv" / "Scripts" / "python.exe",
            "script": root / "tools" / "selenium" / "selenium_cli.py",
            "install": "python tools/selenium/install.py",
        },
        "flint": {
            "kind": "exe",
            "executable": root / "tools" / "flint" / "bin" / "flint.exe",
            "install": "python tools/flint/install.py",
        },
        "ls_lint": {
            "kind": "exe",
            "executable": root / "tools" / "ls_lint" / "bin" / "ls-lint-windows-amd64.exe",
            "install": "python tools/ls_lint/install.py",
        },
        "pymarkdown": {
            "kind": "module",
            "python": venv_python(root, "pymarkdown"),
            "module": "pymarkdown",
            "install": "python tools/pymarkdown/install.py",
        },
        "vault_lint": {
            "kind": "python",
            "python": fast_python,
            "script": root / "tools" / "vault_lint" / "validate_vault.py",
            "install": "python tools/pymarkdown/install.py",
        },
        "vault_lint_check": {
            "kind": "python",
            "python": fast_python,
            "script": root / "tools" / "vault_lint" / "check.py",
            "install": "python tools/pymarkdown/install.py",
        },
        "example_tool": {
            "kind": "python",
            "python": Path(sys.executable),
            "script": root / "tools" / "tool_template" / "example_tool.py",
            "install": "python tools/tool_template/install.py",
        },
        "read_file_lines": {
            "kind": "python",
            "python": fast_python,
            "script": root / "tools" / "read_file_lines" / "read_file_lines.py",
            "install": "python tools/pymarkdown/install.py",
        },
        "search_content": {
            "kind": "python",
            "python": fast_python,
            "script": root / "tools" / "search_content" / "search_content.py",
            "install": "python tools/pymarkdown/install.py",
        },
    }
    for fast in (
        "fast_linear",
        "fast_gmail",
        "fast_gradescope",
        "fast_google_drive",
        "fast_google_calendar",
        "fast_moodle_dl",
        "fast_markitdown",
        "fast_get_homework_pages",
        "fast_check_vault",
        "fast_fix_vault",
        "fast_clean_vault",
        "fast_linear_sync",
        "fast_sync_class",
        "fast_import_syllabus",
        "fast_assign_cycles",
        "fast_dashboard",
        "fast_weekly_review",
        "fast_scaffold_work_note",
        "fast_selenium",
        "fast_fetch_webpage",
        "fast_index_repo",
    ):
        catalog[fast] = {
            "kind": "python",
            "python": fast_python,
            "script": root / "tools" / fast / f"{fast}.py",
            "pythonpath": fast_path,
            "install": "python tools/pymarkdown/install.py",
        }
    discover_python_tools(root, catalog)
    return catalog


INVOKE_EXAMPLE = [
    'python tools/run_tool/run_tool.py commands',
    'python tools/run_tool/run_tool.py fast_dashboard --class "MATH 212"',
    "python tools/run_tool/run_tool.py <tool> commands",
]


def spec(name: str, root: Path) -> dict[str, Any]:
    catalog = tool_catalog(root)
    if name not in catalog:
        known = ", ".join(sorted(catalog))
        raise ToolError(
            f"Unknown tool {name!r}. Known: {known}. "
            f"Example: {INVOKE_EXAMPLE[1]}",
            "usage",
        )
    return catalog[name]


def catalog_names(root: Path | None = None) -> list[str]:
    return sorted(tool_catalog(root or vault_root()))


def build_command(
    name: str, args: list[str], root: Path | None = None
) -> tuple[list[str], dict[str, str], Path]:
    root = root or vault_root()
    tool = spec(name, root)
    env = os.environ.copy()
    cwd = root
    install = str(tool.get("install") or "")
    extra = list(args)
    extra_unless = tool.get("extra_unless")
    extra_args = list(tool.get("extra_args") or [])
    if extra_args and (not extra_unless or extra_unless not in extra):
        extra.extend(extra_args)
    ensure_dir = tool.get("ensure_dir")
    if isinstance(ensure_dir, Path):
        ensure_dir.mkdir(parents=True, exist_ok=True)
    need = tool.get("need")
    if isinstance(need, Path):
        require_file(need, install)
    pythonpath = tool.get("pythonpath")
    if pythonpath:
        env["PYTHONPATH"] = str(pythonpath)

    kind = tool["kind"]
    if kind == "node":
        node = find_node(root)
        script = require_file(Path(tool["script"]), install)
        return [str(node), str(script), *extra], env, cwd
    if kind == "python":
        python = require_file(Path(tool["python"]), install)
        script = require_file(Path(tool["script"]), install)
        return [str(python), str(script), *extra], env, cwd
    if kind == "module":
        python = require_file(Path(tool["python"]), install)
        return [str(python), "-m", str(tool["module"]), *extra], env, cwd
    if kind == "entry":
        python = require_file(Path(tool["python"]), install)
        return (
            entry_argv(
                python,
                str(tool["entry"]),
                str(tool.get("argv0") or name),
                extra,
            ),
            env,
            cwd,
        )
    if kind == "exe":
        executable = require_file(Path(tool["executable"]), install)
        return [str(executable), *extra], env, cwd
    raise ToolError(f"Unsupported tool kind {kind!r}.", "tool")


def dispatch(name: str, args: list[str], *, root: Path | None = None) -> int:
    command, env, cwd = build_command(name, args, root)
    completed = subprocess.run(command, cwd=cwd, env=env, check=False)
    return int(completed.returncode)


def main(argv: list[str] | None = None) -> int:
    try:
        require_host_python()
    except ToolError as error:
        return emit_error(error.message, error.code, invoke=INVOKE_EXAMPLE)
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in {"-h", "--help", "commands", "--list"}:
        json.dump(
            {
                "ok": True,
                "command": "commands",
                "data": {
                    "program": "run_tool",
                    "tools": catalog_names(),
                    "invoke": INVOKE_EXAMPLE,
                },
            },
            sys.stdout,
            indent=2,
        )
        sys.stdout.write("\n")
        return 0
    try:
        return dispatch(argv[0], argv[1:])
    except ToolError as error:
        return emit_error(error.message, error.code, invoke=INVOKE_EXAMPLE)


if __name__ == "__main__":
    raise SystemExit(main())
