from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "run_tool"))
from install_env import install_main, tool_root_from, uv_venv


def install() -> None:
    tool_root = tool_root_from(Path(__file__))
    uv_venv(tool_root)
    print("example_tool environment is ready. This template has no extra packages.")
    print("Run python tools/run_tool/run_tool.py example_tool ping")


if __name__ == "__main__":
    raise SystemExit(install_main(install))
