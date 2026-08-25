from __future__ import annotations

import json
from typing import Any

from fast_common import get_value, is_moodle_url, needs_llm, run_cli, run_json_tool


def run(payload: dict[str, Any]) -> dict[str, Any]:
    status = run_json_tool("selenium", ["ping"])
    remaining = [
        needs_llm(
            "selenium_session",
            message=(
                "Use fast_fetch_webpage for a public URL. Compact selenium commands "
                "are only for clicks, forms, or screenshots after load."
            ),
        )
    ]
    url = get_value(payload, "url")
    if url and is_moodle_url(str(url)):
        remaining = [
            needs_llm(
                "use_moodle_dl",
                url=str(url),
                message="This URL's host starts with moodle. Use fast_moodle_dl, not Selenium.",
            )
        ]
    elif url:
        remaining = [
            needs_llm(
                "selenium_session",
                action="run",
                command=(
                    "python tools/run_tool/run_tool.py fast_fetch_webpage "
                    f"--url {json.dumps(str(url))}"
                ),
            )
        ]
    return {"ping": status, "needs_llm": remaining}


def main() -> int:
    return run_cli("fast_selenium", {"run": run, "ping": run})


if __name__ == "__main__":
    raise SystemExit(main())
