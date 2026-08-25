from __future__ import annotations

import shutil
import zipfile
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "run_tool"))
from install_env import InstallError, gh_release_download, install_main, tool_root_from


VERSION = "v0.0.6"
ARCHIVE_NAME = "flint_0.0.6_Windows_x86_64.zip"


def install() -> None:
    tool_root = tool_root_from(Path(__file__))
    bin_dir = tool_root / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    gh_release_download("hay-kot/flint", VERSION, ARCHIVE_NAME, tool_root)
    archive = tool_root / ARCHIVE_NAME
    with zipfile.ZipFile(archive) as zf:
        zf.extractall(bin_dir)
    archive.unlink(missing_ok=True)
    found = next(bin_dir.rglob("flint.exe"), None)
    if found is None:
        raise InstallError("The Flint archive did not contain flint.exe.")
    destination = bin_dir / "flint.exe"
    if found != destination:
        shutil.copy2(found, destination)
    print(f"Flint {VERSION} installed in {bin_dir}")
    print("Run python tools/run_tool/run_tool.py flint --help to verify it.")


if __name__ == "__main__":
    raise SystemExit(install_main(install))
