from __future__ import annotations

import json
import os
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


def emit_error(message: str, code: str = "usage") -> int:
    json.dump(
        {"ok": False, "error": {"code": code, "message": message}},
        sys.stderr,
        indent=2,
    )
    sys.stderr.write("\n")
    return 1


def find_node(root: Path) -> Path:
    record = root / "tools" / "linear" / "state" / "node-path.txt"
    if record.is_file():
        recorded = record.read_text(encoding="utf-8").strip()
        if recorded and Path(recorded).is_file():
            return Path(recorded)
    which = shutil.which("node")
    if which:
        return Path(which)
    home = Path.home()
    for candidate in (
        home / ".unsloth" / "node" / "node.exe",
        home / "miniconda3" / "envs" / "agi" / "node.exe",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "nodejs" / "node.exe",
        Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "nodejs" / "node.exe",
    ):
        if candidate.is_file():
            return candidate
    raise ToolError("Node.js 18+ is required. Run tools/linear/install.ps1 first.", "tool")


def pymarkdown_python(root: Path) -> Path:
    path = root / "tools" / "pymarkdown" / ".venv" / "Scripts" / "python.exe"
    if path.is_file():
        return path
    which = shutil.which("python")
    if which:
        return Path(which)
    return Path(sys.executable)


def require_file(path: Path, install: str) -> Path:
    if not path.exists():
        raise ToolError(f"Missing {path}. Run {install} first.", "tool")
    return path


def tool_catalog(root: Path) -> dict[str, dict[str, Any]]:
    google_auth = str(root / "tools" / "google-auth")
    fast_path = str(root / "tools" / "fast-common")
    fast_python = pymarkdown_python(root)
    catalog: dict[str, dict[str, Any]] = {
        "linear": {
            "kind": "node",
            "script": root / "tools" / "linear" / "linear_cli.js",
            "need": root / "tools" / "linear" / "node_modules" / "@linear" / "sdk",
            "install": r".\tools\linear\install.ps1",
        },
        "gmail": {
            "kind": "python",
            "python": root / "tools" / "gmail" / ".venv" / "Scripts" / "python.exe",
            "script": root / "tools" / "gmail" / "gmail.py",
            "pythonpath": google_auth,
            "install": r".\tools\gmail\install.ps1",
        },
        "google-drive": {
            "kind": "python",
            "python": root / "tools" / "google-drive" / ".venv" / "Scripts" / "python.exe",
            "script": root / "tools" / "google-drive" / "google_drive.py",
            "pythonpath": google_auth,
            "install": r".\tools\google-drive\install.ps1",
        },
        "google-calendar": {
            "kind": "python",
            "python": root / "tools" / "google-calendar" / ".venv" / "Scripts" / "python.exe",
            "script": root / "tools" / "google-calendar" / "google_calendar.py",
            "pythonpath": google_auth,
            "install": r".\tools\google-calendar\install.ps1",
        },
        "google-auth": {
            "kind": "python",
            "python": root / "tools" / "google-auth" / ".venv" / "Scripts" / "python.exe",
            "script": root / "tools" / "google-auth" / "google_auth.py",
            "pythonpath": str(root / "tools" / "google-auth"),
            "install": r".\tools\google-auth\install.ps1",
        },
        "moodle-dl": {
            "kind": "exe",
            "executable": root / "tools" / "moodle-dl" / ".venv" / "Scripts" / "moodle-dl.exe",
            "install": r".\tools\moodle-dl\install.ps1",
            "ensure_dir": root / "tools" / "moodle-dl" / "state",
            "extra_unless": "--path",
            "extra_args": ["--path", str(root / "tools" / "moodle-dl" / "state")],
        },
        "markitdown": {
            "kind": "exe",
            "executable": root / "tools" / "markitdown" / ".venv" / "Scripts" / "markitdown.exe",
            "install": r".\tools\markitdown\install.ps1",
        },
        "pypdf": {
            "kind": "python",
            "python": root / "tools" / "pypdf" / ".venv" / "Scripts" / "python.exe",
            "script": root / "tools" / "pypdf" / "extract_pages.py",
            "install": r".\tools\pypdf\install.ps1",
        },
        "gradescope": {
            "kind": "python",
            "python": root / "tools" / "gradescope" / ".venv" / "Scripts" / "python.exe",
            "script": root / "tools" / "gradescope" / "gradescope.py",
            "install": r".\tools\gradescope\install.ps1",
        },
        "selenium": {
            "kind": "python",
            "python": root / "tools" / "selenium" / ".venv" / "Scripts" / "python.exe",
            "script": root / "tools" / "selenium" / "selenium_cli.py",
            "install": r".\tools\selenium\install.ps1",
        },
        "flint": {
            "kind": "exe",
            "executable": root / "tools" / "flint" / "bin" / "flint.exe",
            "install": r".\tools\flint\install.ps1",
        },
        "ls-lint": {
            "kind": "exe",
            "executable": root / "tools" / "ls-lint" / "bin" / "ls-lint-windows-amd64.exe",
            "install": r".\tools\ls-lint\install.ps1",
        },
        "pymarkdown": {
            "kind": "exe",
            "executable": root / "tools" / "pymarkdown" / ".venv" / "Scripts" / "pymarkdown.exe",
            "install": r".\tools\pymarkdown\install.ps1",
        },
        "vault-lint": {
            "kind": "python",
            "python": fast_python,
            "script": root / "tools" / "vault-lint" / "validate_vault.py",
            "install": r".\tools\vault-lint\check.ps1",
        },
        "vault-lint-check": {
            "kind": "powershell",
            "script": root / "tools" / "vault-lint" / "check.ps1",
            "install": r".\tools\pymarkdown\install.ps1",
        },
        "example-tool": {
            "kind": "python",
            "python": Path(sys.executable),
            "script": root / "tools" / "tool-template" / "example_tool.py",
            "install": r".\tools\tool-template\install.ps1",
        },
        "read-file-lines": {
            "kind": "python",
            "python": fast_python,
            "script": root / "tools" / "read-file-lines" / "read_file_lines.py",
            "install": r".\tools\pymarkdown\install.ps1",
        },
    }
    catalog["read_file_lines"] = catalog["read-file-lines"]
    for fast in (
        "fast-linear",
        "fast-gmail",
        "fast-gradescope",
        "fast-google-drive",
        "fast-google-calendar",
        "fast-moodle-dl",
        "fast-markitdown",
        "fast-get-homework-pages",
        "fast-check-vault",
        "fast-fix-vault",
        "fast-clean-vault",
        "fast-linear-sync",
        "fast-sync-class",
        "fast-import-syllabus",
        "fast-assign-cycles",
        "fast-dashboard",
        "fast-weekly-review",
        "fast-scaffold-work-note",
        "fast-selenium",
        "fast-fetch-webpage",
    ):
        module = fast.replace("-", "_")
        catalog[fast] = {
            "kind": "python",
            "python": fast_python,
            "script": root / "tools" / fast / f"{module}.py",
            "pythonpath": fast_path,
            "install": r".\tools\pymarkdown\install.ps1",
        }
    return catalog


def spec(name: str, root: Path) -> dict[str, Any]:
    catalog = tool_catalog(root)
    if name not in catalog:
        known = ", ".join(sorted(catalog))
        raise ToolError(f"Unknown tool {name!r}. Known: {known}", "usage")
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
    if kind == "exe":
        executable = require_file(Path(tool["executable"]), install)
        return [str(executable), *extra], env, cwd
    if kind == "powershell":
        powershell = (
            os.environ.get("POWERSHELL")
            or shutil.which("powershell.exe")
            or "powershell.exe"
        )
        script = require_file(Path(tool["script"]), install)
        return [
            str(powershell),
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script),
            *extra,
        ], env, cwd
    raise ToolError(f"Unsupported tool kind {kind!r}.", "tool")


def dispatch(name: str, args: list[str], *, root: Path | None = None) -> int:
    command, env, cwd = build_command(name, args, root)
    completed = subprocess.run(command, cwd=cwd, env=env, check=False)
    return int(completed.returncode)


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in {"-h", "--help", "commands", "--list"}:
        json.dump(
            {
                "ok": True,
                "command": "commands",
                "data": {
                    "program": "run-tool",
                    "tools": catalog_names(),
                    "usage": [
                        r".\tools\run-tool\run-tool.ps1 <tool> [args...]",
                        "python tools/run-tool/run_tool.py <tool> [args...]",
                        r".\tools\run-tool\run-tool.ps1 google-calendar upcoming --days 14",
                        r".\tools\run-tool\run-tool.ps1 google-calendar commands",
                        r".\tools\run-tool\run-tool.ps1 gmail get_thread --threadId ID",
                        r".\tools\run-tool\run-tool.ps1 read_file_lines <path> [start] [end]",
                    ],
                    "shell": "powershell",
                    "rule": (
                        "Do not write a session script. Put JSON payloads in --json-file. "
                        "Use Windows PowerShell or a real python.exe. "
                        "Do not wrap PowerShell cmdlets in bash -c. "
                        "Do not use pyodide or any emulated interpreter. "
                        "Discover a tool's commands with: python tools/run-tool/run_tool.py <tool> commands"
                    ),
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
        return emit_error(error.message, error.code)


if __name__ == "__main__":
    raise SystemExit(main())
