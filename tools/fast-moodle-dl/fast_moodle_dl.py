from __future__ import annotations

from pathlib import Path
from typing import Any

from fast_common import (
    get_value,
    inventory_moodle,
    moodle_config_exists,
    needs_llm,
    resolve_classes,
    run_cli,
    run_moodle_sync,
    truthy,
)


def run(payload: dict[str, Any]) -> dict[str, Any]:
    moodle = run_moodle_sync(
        skip_download=truthy(get_value(payload, "skipDownload", "skip_download"))
    )
    remaining = list(moodle.get("needs_user") or [])
    courses = []
    for course in resolve_classes(payload):
        staged = inventory_moodle(course)
        courses.append(
            {
                "class": course["code"],
                "folder": course["folder"].name,
                "items": [
                    {
                        "relative": item["relative"],
                        "kind": item["kind"],
                        "action": item["action"],
                        "deadline": item["deadline"],
                        "size": item["size"],
                    }
                    for item in staged
                ],
            }
        )
    if not moodle_config_exists() and not remaining:
        remaining.append(
            needs_llm(
                "moodle_init",
                command=r".\tools\moodle-dl\moodle-dl.ps1 --init --sso",
            )
        )
    return {
        "moodle": {key: value for key, value in moodle.items() if key != "needs_user"},
        "config_present": moodle_config_exists(),
        "state": str(Path("tools/moodle-dl/state")),
        "courses": courses,
        "needs_llm": remaining,
    }


def main() -> int:
    return run_cli(
        "fast-moodle-dl",
        {
            "run": run,
        },
    )


if __name__ == "__main__":
    raise SystemExit(main())
