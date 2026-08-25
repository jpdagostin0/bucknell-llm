from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "run_tool"))
from install_env import install_main, tool_root_from, uv_venv


def install() -> None:
    uv_venv(
        tool_root_from(Path(__file__)),
        ["pymarkdownlnt==0.9.39", "pyyaml==6.0.3"],
        verify="pymarkdown version",
    )


if __name__ == "__main__":
    raise SystemExit(install_main(install))
