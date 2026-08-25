from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "run_tool"))
from install_env import install_main, tool_root_from, uv_venv


def install() -> None:
    uv_venv(
        tool_root_from(Path(__file__)),
        [
            "PyYAML==6.0.2",
            "google_auth==2.40.3",
            "google_auth-oauthlib==1.2.2",
            "google_auth-httplib2==0.2.0",
            "google-api-python-client==2.179.0",
        ],
        verify="google_auth commands",
    )


if __name__ == "__main__":
    raise SystemExit(install_main(install))
