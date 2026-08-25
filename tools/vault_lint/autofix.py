from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def vault_root() -> Path:
    return Path(__file__).resolve().parents[2]


def main() -> int:
    root = vault_root()
    python = root / "tools" / "pymarkdown" / ".venv" / "Scripts" / "python.exe"
    if not python.exists():
        print(
            "PyMarkdown is not installed. Run python tools/pymarkdown/install.py first.",
            file=sys.stderr,
        )
        return 1
    result = subprocess.run(
        [
            str(python),
            "-m",
            "pymarkdown",
            "--config",
            str(root / ".pymarkdown.yml"),
            "fix",
            "--recurse",
            "--respect-gitignore",
            ".",
        ],
        cwd=root,
        check=False,
    )
    return int(result.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
