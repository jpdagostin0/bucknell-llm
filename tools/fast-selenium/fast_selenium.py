from __future__ import annotations

from typing import Any

from fast_common import get_value, is_moodle_url, needs_llm, run_cli, run_json_tool


def run(payload: dict[str, Any]) -> dict[str, Any]:
    status = run_json_tool("selenium", ["ping"])
    remaining = [
        needs_llm(
            "selenium_session",
            message=(
                "Use fetch-webpage for a public URL. Use compact selenium commands "
                "only when the page needs clicks, forms, or screenshots after load."
            ),
        )
    ]
    url = get_value(payload, "url")
    if url and is_moodle_url(str(url)):
        remaining = [
            needs_llm(
                "use_moodle_dl",
                url=str(url),
                message="This URL's host starts with moodle. Use moodle-dl, not Selenium.",
            )
        ]
    return {"ping": status, "needs_llm": remaining}


def main() -> int:
    return run_cli("fast-selenium", {"run": run, "ping": run})


if __name__ == "__main__":
    raise SystemExit(main())
