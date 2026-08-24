from __future__ import annotations

from typing import Any

from fast_common import (
    ToolError,
    get_value,
    google_status,
    payload_flags,
    run_cli,
    run_json_tool,
)


def require_auth() -> dict[str, Any]:
    status = google_status("google-calendar")
    if not status.get("authorized"):
        raise ToolError(
            r"Calendar is not authorized. Run .\tools\google-auth\google-auth.ps1 login",
            "needs_auth",
        )
    return status


def upcoming(payload: dict[str, Any]) -> dict[str, Any]:
    require_auth()
    args = [
        "upcoming",
        "--days",
        str(int(get_value(payload, "days", default=14))),
        "--maxResults",
        str(get_value(payload, "maxResults", "max_results", default=50)),
    ]
    time_min = get_value(payload, "timeMin", "time_min")
    time_max = get_value(payload, "timeMax", "time_max")
    query = get_value(payload, "query")
    calendar = get_value(payload, "calendarId", "calendar_id")
    if time_min:
        args.extend(["--timeMin", str(time_min)])
    if time_max:
        args.extend(["--timeMax", str(time_max)])
    if query:
        args.extend(["--query", str(query)])
    if calendar:
        args.extend(["--calendarId", str(calendar)])
    data = run_json_tool("google-calendar", args)
    return {
        "days": data.get("days"),
        "timeMin": data.get("timeMin"),
        "timeMax": data.get("timeMax"),
        "events": data.get("events") or [],
        "needs_llm": [],
    }


def create(payload: dict[str, Any]) -> dict[str, Any]:
    require_auth()
    return run_json_tool("google-calendar", ["create_event", *payload_flags(payload)])


def update(payload: dict[str, Any]) -> dict[str, Any]:
    require_auth()
    return run_json_tool("google-calendar", ["update_event", *payload_flags(payload)])


def delete(payload: dict[str, Any]) -> dict[str, Any]:
    require_auth()
    return run_json_tool("google-calendar", ["delete_event", *payload_flags(payload)])


def respond(payload: dict[str, Any]) -> dict[str, Any]:
    require_auth()
    return run_json_tool("google-calendar", ["respond_to_event", *payload_flags(payload)])


def run(payload: dict[str, Any]) -> dict[str, Any]:
    return upcoming(payload)


def main() -> int:
    return run_cli(
        "fast-google-calendar",
        {
            "run": run,
            "upcoming": upcoming,
            "create": create,
            "update": update,
            "delete": delete,
            "respond": respond,
        },
    )


if __name__ == "__main__":
    raise SystemExit(main())
