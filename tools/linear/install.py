from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "run_tool"))
from install_env import find_node, find_npm, install_main, run_checked, tool_root_from


def install() -> None:
    tool_root = tool_root_from(Path(__file__))
    state = tool_root / "state"
    state.mkdir(parents=True, exist_ok=True)
    node = find_node(use_record=False)
    npm = find_npm(node)
    (state / "node-path.txt").write_text(str(node), encoding="utf-8")
    run_checked(
        [str(npm), "install", "--omit=dev"],
        "Failed to install Linear CLI dependencies.",
        cwd=tool_root,
    )
    print(f"linear installed with {node}")
    print("Run python tools/run_tool/run_tool.py linear commands to verify it.")


if __name__ == "__main__":
    raise SystemExit(install_main(install))
