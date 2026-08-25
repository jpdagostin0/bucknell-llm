from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "run_tool"))
from install_env import install_main, tool_root_from, uv_venv


def install() -> None:
    uv_venv(
        tool_root_from(Path(__file__)),
        ["markitdown[pdf,docx]==0.1.7"],
        verify="markitdown --help",
    )


if __name__ == "__main__":
    raise SystemExit(install_main(install))
