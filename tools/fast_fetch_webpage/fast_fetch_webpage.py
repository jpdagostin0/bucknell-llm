from __future__ import annotations

from typing import Any

from fast_common import (
    ToolError,
    get_value,
    is_moodle_url,
    needs_llm,
    run_cli,
    run_json_tool,
    truthy,
)


def run(payload: dict[str, Any]) -> dict[str, Any]:
    url = str(get_value(payload, "url", required=True))
    if is_moodle_url(url):
        raise ToolError(
            "This URL's host starts with moodle. Use fast_moodle_dl, not Selenium.",
            "routing",
        )
    args = ["fetch", "--url", url]
    wait_until = get_value(payload, "wait_until", "waitUntil")
    if wait_until:
        args.extend(["--wait_until", str(wait_until)])
    name = get_value(payload, "name")
    if name:
        args.extend(["--name", str(name)])
    if payload.get("screenshot") is False or str(payload.get("screenshot") or "").lower() in {
        "false",
        "no",
        "0",
    }:
        args.extend(["--screenshot", "false"])
    if truthy(get_value(payload, "quit")):
        args.extend(["--quit", "true"])
    fetched = run_json_tool("selenium", args, timeout=180)
    remaining = [
        needs_llm(
            "note_rewrite",
            url=url,
            output=fetched.get("text_path"),
            message=(
                "Read the captured text or HTML and rewrite useful facts into a typed "
                "vault note. Do not copy Linear-owned due dates into frontmatter."
            ),
        )
    ]
    return {**fetched, "needs_llm": remaining}


def main() -> int:
    return run_cli("fast_fetch_webpage", {"run": run})


if __name__ == "__main__":
    raise SystemExit(main())
