from __future__ import annotations

import base64
import os
import tempfile
from pathlib import Path
from typing import Any

from google_auth import (
    ToolError,
    as_list,
    get_value,
    google_client_config,
    load_credentials,
    ping as google_ping,
    run_cli,
)
from simplegmail import Gmail


def gmail_client() -> Gmail:
    creds = load_credentials(interactive=False)
    return Gmail(credentials=creds)


def serialize_message(message: Any, *, include_body: bool = False) -> dict[str, Any]:
    payload = {
        "id": getattr(message, "id", None),
        "threadId": getattr(message, "thread_id", None) or getattr(message, "threadId", None),
        "subject": getattr(message, "subject", None),
        "sender": getattr(message, "sender", None),
        "recipient": getattr(message, "recipient", None),
        "cc": getattr(message, "cc", None),
        "bcc": getattr(message, "bcc", None),
        "date": str(getattr(message, "date", "") or ""),
        "snippet": getattr(message, "snippet", None),
        "labelIds": getattr(message, "label_ids", None),
    }
    if include_body:
        payload["plain"] = getattr(message, "plain", None)
        payload["html"] = getattr(message, "html", None)
        attachments = []
        for attachment in getattr(message, "attachments", None) or []:
            attachments.append(
                {
                    "filename": getattr(attachment, "filename", None),
                    "mimeType": getattr(attachment, "filetype", None)
                    or getattr(attachment, "mime_type", None),
                    "id": getattr(attachment, "id", None),
                }
            )
        payload["attachments"] = attachments
    return payload


def sender_address() -> str:
    email = google_client_config().get("email") or ""
    return email or "me"


def write_attachments(attachments: list[Any]) -> list[str]:
    paths: list[str] = []
    for item in attachments:
        if isinstance(item, str):
            paths.append(item)
            continue
        filename = item.get("filename") or "attachment.bin"
        content = item.get("content") or item.get("base64Content")
        if not content:
            continue
        path = Path(tempfile.gettempdir()) / filename
        path.write_bytes(base64.b64decode(content))
        paths.append(str(path))
    return paths


def ping(_: dict[str, Any]) -> dict[str, Any]:
    result = google_ping()
    result["service"] = "gmail"
    if result.get("authorized"):
        client = gmail_client()
        labels = client.list_labels()
        result["labelCount"] = len(labels)
    return result


def search_threads(payload: dict[str, Any]) -> dict[str, Any]:
    client = gmail_client()
    query = get_value(payload, "query", default="")
    page_size = int(get_value(payload, "pageSize", "page_size", "max_results", default=20))
    include_trash = bool(get_value(payload, "includeTrash", "include_trash", default=False))
    messages = client.get_messages(
        query=query or None,
        max_results=page_size,
        include_spam_trash=include_trash,
        attachments="reference",
    )
    threads: dict[str, dict[str, Any]] = {}
    for message in messages:
        serialized = serialize_message(message)
        thread_id = serialized["threadId"] or serialized["id"]
        thread = threads.setdefault(
            thread_id,
            {"id": thread_id, "messages": []},
        )
        thread["messages"].append(serialized)
        thread.setdefault("subject", serialized["subject"])
        thread.setdefault("snippet", serialized["snippet"])
        thread.setdefault("sender", serialized["sender"])
        thread.setdefault("date", serialized["date"])
    return {"threads": list(threads.values())}


def get_message(payload: dict[str, Any]) -> dict[str, Any]:
    message_id = get_value(payload, "id", "messageId", "message_id", required=True)
    client = gmail_client()
    messages = client.get_messages(query=f"rfc822msgid:{message_id}", max_results=1)
    if not messages:
        messages = [
            item
            for item in client.get_messages(query="", max_results=50, attachments="reference")
            if getattr(item, "id", None) == message_id
        ]
    if not messages:
        raise ToolError(f"Message not found: {message_id}", "api")
    return serialize_message(messages[0], include_body=True)


def get_thread(payload: dict[str, Any]) -> dict[str, Any]:
    thread_id = get_value(payload, "id", "threadId", "thread_id", required=True)
    client = gmail_client()
    messages = client.get_messages(
        query=None,
        max_results=100,
        attachments="reference",
    )
    matched = [
        serialize_message(item, include_body=True)
        for item in messages
        if (getattr(item, "thread_id", None) or getattr(item, "threadId", None)) == thread_id
        or getattr(item, "id", None) == thread_id
    ]
    if not matched:
        # Gmail search can target a thread id directly in some accounts.
        matched = [
            serialize_message(item, include_body=True)
            for item in client.get_messages(query=thread_id, max_results=20)
        ]
    return {"id": thread_id, "messages": matched}


def list_labels(_: dict[str, Any]) -> dict[str, Any]:
    client = gmail_client()
    labels = []
    for label in client.list_labels():
        labels.append(
            {
                "id": getattr(label, "id", None),
                "name": getattr(label, "name", None),
            }
        )
    return {"labels": labels}


def list_drafts(payload: dict[str, Any]) -> dict[str, Any]:
    client = gmail_client()
    page_size = int(get_value(payload, "pageSize", "page_size", default=20))
    drafts = client.get_drafts()
    return {
        "drafts": [
            serialize_message(item)
            for item in drafts[:page_size]
        ]
    }


def _message_kwargs(payload: dict[str, Any]) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "sender": sender_address(),
        "to": as_list(get_value(payload, "to")),
        "cc": as_list(get_value(payload, "cc")) or None,
        "bcc": as_list(get_value(payload, "bcc")) or None,
        "subject": get_value(payload, "subject"),
        "msg_plain": get_value(payload, "body", "msg_plain", "msgPlain"),
        "msg_html": get_value(payload, "htmlBody", "html_body", "msg_html"),
    }
    attachments = as_list(get_value(payload, "attachments"))
    if attachments:
        kwargs["attachments"] = write_attachments(attachments)
    return {key: value for key, value in kwargs.items() if value not in (None, [])}


def send_message(payload: dict[str, Any]) -> dict[str, Any]:
    client = gmail_client()
    draft_id = get_value(payload, "draftId", "draft_id")
    if draft_id:
        raise ToolError(
            "Sending an existing draft by id is not supported by simplegmail; "
            "create and send the message instead.",
            "usage",
        )
    message = client.send_message(**_message_kwargs(payload))
    return serialize_message(message)


def create_draft(payload: dict[str, Any]) -> dict[str, Any]:
    client = gmail_client()
    kwargs = _message_kwargs(payload)
    reply_to = get_value(payload, "replyToMessageId", "reply_to_message_id")
    if reply_to:
        original = [
            item
            for item in client.get_messages(max_results=50)
            if getattr(item, "id", None) == reply_to
        ]
        if original:
            kwargs["reply_to"] = original[0]
    draft = client.create_draft(**kwargs)
    return {"id": draft.get("id") if isinstance(draft, dict) else getattr(draft, "id", None)}


def reply(payload: dict[str, Any]) -> dict[str, Any]:
    client = gmail_client()
    message_id = get_value(payload, "messageId", "message_id", "id", required=True)
    originals = [
        item
        for item in client.get_messages(max_results=50)
        if getattr(item, "id", None) == message_id
    ]
    if not originals:
        raise ToolError(f"Message not found: {message_id}", "api")
    kwargs = _message_kwargs(payload)
    kwargs["reply_to"] = originals[0]
    kwargs.setdefault("to", originals[0].sender)
    kwargs.setdefault("subject", originals[0].subject)
    message = client.send_message(**kwargs)
    return serialize_message(message)


def update_message_labels(payload: dict[str, Any]) -> dict[str, Any]:
    message_id = get_value(payload, "id", "messageId", "message_id", required=True)
    add_labels = as_list(get_value(payload, "addLabelIds", "add_label_ids", "labels"))
    remove_labels = as_list(get_value(payload, "removeLabelIds", "remove_label_ids"))
    client = gmail_client()
    messages = [
        item
        for item in client.get_messages(max_results=50)
        if getattr(item, "id", None) == message_id
    ]
    if not messages:
        raise ToolError(f"Message not found: {message_id}", "api")
    message = messages[0]
    for label in add_labels:
        message.add_label(label)
    for label in remove_labels:
        message.remove_label(label) if hasattr(message, "remove_label") else None
    return serialize_message(message)


def label_message(payload: dict[str, Any]) -> dict[str, Any]:
    payload = dict(payload)
    payload["addLabelIds"] = as_list(get_value(payload, "labelIds", "label_ids", "labels"))
    return update_message_labels(payload)


def unlabel_message(payload: dict[str, Any]) -> dict[str, Any]:
    payload = dict(payload)
    payload["removeLabelIds"] = as_list(get_value(payload, "labelIds", "label_ids", "labels"))
    return update_message_labels(payload)


def trash_message(payload: dict[str, Any]) -> dict[str, Any]:
    message_id = get_value(payload, "id", "messageId", "message_id", required=True)
    client = gmail_client()
    messages = [
        item
        for item in client.get_messages(max_results=50)
        if getattr(item, "id", None) == message_id
    ]
    if not messages:
        raise ToolError(f"Message not found: {message_id}", "api")
    messages[0].trash()
    return serialize_message(messages[0])


def untrash_message(payload: dict[str, Any]) -> dict[str, Any]:
    message_id = get_value(payload, "id", "messageId", "message_id", required=True)
    client = gmail_client()
    messages = [
        item
        for item in client.get_messages(
            max_results=50,
            include_spam_trash=True,
        )
        if getattr(item, "id", None) == message_id
    ]
    if not messages:
        raise ToolError(f"Message not found: {message_id}", "api")
    messages[0].untrash()
    return serialize_message(messages[0])


def create_label(payload: dict[str, Any]) -> dict[str, Any]:
    raise ToolError(
        "Creating Gmail labels is not exposed by simplegmail. Use list_labels to inspect existing labels.",
        "usage",
    )


def commands() -> dict[str, Any]:
    return {
        "ping": ping,
        "search_threads": search_threads,
        "get_thread": get_thread,
        "get_message": get_message,
        "list_labels": list_labels,
        "list_drafts": list_drafts,
        "create_draft": create_draft,
        "send_message": send_message,
        "reply": reply,
        "label_message": label_message,
        "unlabel_message": unlabel_message,
        "update_message_labels": update_message_labels,
        "trash_message": trash_message,
        "untrash_message": untrash_message,
        "create_label": create_label,
    }


def main() -> int:
    os.environ.setdefault("OAUTHLIB_RELAX_TOKEN_SCOPE", "1")
    return run_cli(
        "gmail",
        commands(),
        example='search_threads --query "is:unread newer_than:7d" --pageSize 10',
    )


if __name__ == "__main__":
    raise SystemExit(main())
