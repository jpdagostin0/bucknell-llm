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
    status = google_status("gmail")
    if not status.get("authorized"):
        raise ToolError(
            r"Gmail is not authorized. Run python tools/run_tool/run_tool.py google_auth login",
            "needs_auth",
        )
    return status


def inbox(payload: dict[str, Any]) -> dict[str, Any]:
    require_auth()
    query = get_value(payload, "query", default="is:unread newer_than:7d")
    page_size = int(get_value(payload, "pageSize", "page_size", default=10))
    data = run_json_tool(
        "gmail",
        ["search_threads", "--query", str(query), "--pageSize", str(page_size)],
    )
    threads = []
    for thread in data.get("threads") or []:
        threads.append(
            {
                "id": thread.get("id"),
                "subject": thread.get("subject"),
                "sender": thread.get("sender"),
                "date": thread.get("date"),
                "snippet": thread.get("snippet"),
                "messageCount": len(thread.get("messages") or []),
            }
        )
    return {"query": query, "threads": threads, "needs_llm": []}


def get(payload: dict[str, Any]) -> dict[str, Any]:
    require_auth()
    thread_id = get_value(payload, "id", "threadId", "thread_id")
    message_id = get_value(payload, "messageId", "message_id")
    if thread_id:
        return run_json_tool("gmail", ["get_thread", "--id", str(thread_id)])
    if message_id:
        return run_json_tool("gmail", ["get_message", "--id", str(message_id)])
    raise ToolError("Pass --id for a thread or --messageId for a message.", "usage")


def _mutate(command: str, payload: dict[str, Any]) -> dict[str, Any]:
    require_auth()
    return run_json_tool("gmail", [command, *payload_flags(payload)])


def send(payload: dict[str, Any]) -> dict[str, Any]:
    return _mutate("send_message", payload)


def reply(payload: dict[str, Any]) -> dict[str, Any]:
    return _mutate("reply", payload)


def draft(payload: dict[str, Any]) -> dict[str, Any]:
    return _mutate("create_draft", payload)


def trash(payload: dict[str, Any]) -> dict[str, Any]:
    return _mutate("trash_message", payload)


def label(payload: dict[str, Any]) -> dict[str, Any]:
    return _mutate("label_message", payload)


def run(payload: dict[str, Any]) -> dict[str, Any]:
    return inbox(payload)


def main() -> int:
    return run_cli(
        "fast_gmail",
        {
            "run": run,
            "inbox": inbox,
            "get": get,
            "send": send,
            "reply": reply,
            "draft": draft,
            "trash": trash,
            "label": label,
        },
    )


if __name__ == "__main__":
    raise SystemExit(main())
