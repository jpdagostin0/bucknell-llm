from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "run_tool"))
from install_env import gh_release_download, install_main, tool_root_from


VERSION = "v2.3.1"
ASSET_NAME = "ls-lint-windows-amd64.exe"


def install() -> None:
    tool_root = tool_root_from(Path(__file__))
    bin_dir = tool_root / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    gh_release_download("loeffel-io/ls-lint", VERSION, ASSET_NAME, bin_dir)
    print(f"ls_lint {VERSION} installed in {bin_dir}")
    print("Run python tools/run_tool/run_tool.py ls_lint --help to verify it.")


if __name__ == "__main__":
    raise SystemExit(install_main(install))
