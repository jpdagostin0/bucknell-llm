from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path


class InstallError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def vault_root() -> Path:
    return Path(__file__).resolve().parents[2]


def tool_root_from(path: Path) -> Path:
    return path.resolve().parent


def require_command(name: str, message: str | None = None) -> str:
    located = shutil.which(name)
    if not located:
        raise InstallError(message or f"{name} is required.")
    return located


def require_uv() -> str:
    return require_command("uv", "uv is required. Install uv, then rerun this script.")


def require_gh() -> str:
    return require_command(
        "gh", "GitHub CLI is required. Install gh, then rerun this script."
    )


def run_checked(
    command: list[str],
    message: str,
    *,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, cwd=cwd, check=False)
    if result.returncode != 0:
        raise InstallError(message)
    return result


def uv_venv_command(environment: Path, python: str = "3.12") -> list[str]:
    return [require_uv(), "venv", str(environment), "--python", python]


def uv_pip_command(python_exe: Path, packages: list[str]) -> list[str]:
    return [require_uv(), "pip", "install", "--python", str(python_exe), *packages]


def venv_python(tool_root: Path) -> Path:
    return tool_root / ".venv" / "Scripts" / "python.exe"


def uv_venv(
    tool_root: Path,
    packages: list[str] | None = None,
    *,
    python: str = "3.12",
    verify: str | None = None,
) -> Path:
    environment = tool_root / ".venv"
    python_exe = venv_python(tool_root)
    run_checked(
        uv_venv_command(environment, python),
        f"Failed to create the {tool_root.name} virtual environment.",
    )
    if packages:
        run_checked(
            uv_pip_command(python_exe, packages),
            f"Failed to install {tool_root.name} dependencies.",
        )
    print(f"{tool_root.name} installed in {environment}")
    if verify:
        print(f"Run python tools/run_tool/run_tool.py {verify} to verify it.")
    return python_exe


def gh_release_download(
    repo: str,
    version: str,
    pattern: str,
    dest: Path,
) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    run_checked(
        [
            require_gh(),
            "release",
            "download",
            version,
            "--repo",
            repo,
            "--pattern",
            pattern,
            "--dir",
            str(dest),
            "--clobber",
        ],
        f"Failed to download {repo} {version}.",
    )


def find_node(root: Path | None = None, *, use_record: bool = True) -> Path:
    root = root or vault_root()
    if use_record:
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
    raise InstallError(
        "Node.js 18+ is required. Run python tools/linear/install.py first."
        if use_record
        else "Node.js 18+ is required. Install Node, then rerun this script."
    )


def find_npm(node_path: Path) -> Path:
    which = shutil.which("npm.cmd") or shutil.which("npm")
    if which:
        return Path(which)
    sibling = node_path.parent / "npm.cmd"
    if sibling.is_file():
        return sibling
    raise InstallError(f"npm was not found next to {node_path}.")


def install_main(fn) -> int:
    try:
        fn()
    except InstallError as error:
        print(error.message, file=sys.stderr)
        return 1
    return 0
