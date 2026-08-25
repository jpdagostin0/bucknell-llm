from __future__ import annotations

import base64
import io
import os
import re
from typing import Any

from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive

from google_auth import (
    get_value,
    load_credentials,
    ping as google_ping,
    run_cli,
)

SHARED_FILE = {"supportsAllDrives": True}
SHARED_LIST = {"supportsAllDrives": True, "includeItemsFromAllDrives": True}


class PyDriveCredentials:
    """Adapt google_auth credentials for PyDrive2.

    google.oauth2.credentials.Credentials has no access_token_expired attribute,
    which PyDrive2 FetchMetadata/Upload still checks.
    """

    def __init__(self, credentials: Any) -> None:
        self._credentials = credentials

    @property
    def access_token_expired(self) -> bool:
        return not bool(self._credentials.valid)

    def refresh(self, http: Any = None) -> None:
        self._credentials.refresh(Request())

    def __getattr__(self, name: str) -> Any:
        return getattr(self._credentials, name)


EXPORT_DEFAULTS = {
    "application/vnd.google-apps.document": "text/plain",
    "application/vnd.google-apps.spreadsheet": "text/csv",
    "application/vnd.google-apps.presentation": "text/plain",
    "application/vnd.google-apps.folder": None,
}


def drive_client() -> tuple[GoogleDrive, Any]:
    creds = load_credentials(interactive=False)
    service = build("drive", "v2", credentials=creds, cache_discovery=False)
    settings = {
        "client_config_backend": "settings",
        "client_config": {
            "client_id": creds.client_id or "unused",
            "client_secret": creds.client_secret or "unused",
        },
        "save_credentials": False,
        "oauth_scope": list(creds.scopes or []),
    }
    auth = GoogleAuth(settings=settings)
    auth.credentials = PyDriveCredentials(creds)
    auth.service = service
    return GoogleDrive(auth), service


def serialize_file(file_obj: Any) -> dict[str, Any]:
    parents = file_obj.get("parents") or []
    parent_ids = [
        parent.get("id") if isinstance(parent, dict) else parent for parent in parents
    ]
    return {
        "id": file_obj.get("id"),
        "title": file_obj.get("title") or file_obj.get("name"),
        "mimeType": file_obj.get("mimeType"),
        "parents": parent_ids,
        "createdDate": file_obj.get("createdDate") or file_obj.get("createdTime"),
        "modifiedDate": file_obj.get("modifiedDate") or file_obj.get("modifiedTime"),
        "md5Checksum": file_obj.get("md5Checksum"),
        "fileSize": file_obj.get("fileSize") or file_obj.get("size"),
        "webViewLink": file_obj.get("alternateLink") or file_obj.get("webViewLink"),
        "iconLink": file_obj.get("iconLink"),
        "owners": file_obj.get("owners"),
        "shared": file_obj.get("shared"),
        "explicitlyTrashed": file_obj.get("explicitlyTrashed")
        or (file_obj.get("labels") or {}).get("trashed"),
    }


def translate_query(query: str | None) -> str:
    if not query:
        return "trashed = false"

    def parent_clause(match: re.Match[str]) -> str:
        value = match.group(1).strip()
        if value.strip("\"'") == "root":
            return "'root' in parents"
        return f"{value} in parents"

    return re.sub(
        r"parentId\s*=\s*('[^']+'|\"[^\"]+\"|[^\s]+)",
        parent_clause,
        query,
    )


def list_files(query: str, page_size: int, page_token: str | None) -> dict[str, Any]:
    _, service = drive_client()
    request = {
        "q": query,
        "maxResults": page_size,
        **SHARED_LIST,
    }
    if page_token:
        request["pageToken"] = page_token
    response = service.files().list(**request).execute()
    files = [serialize_file(item) for item in response.get("items", [])]
    return {
        "files": files,
        "nextPageToken": response.get("nextPageToken"),
    }


def ping(_: dict[str, Any]) -> dict[str, Any]:
    result = google_ping()
    result["service"] = "google_drive"
    if result.get("authorized"):
        _, service = drive_client()
        about = service.about().get().execute()
        result["user"] = {
            "displayName": (about.get("user") or {}).get("displayName"),
            "emailAddress": (about.get("user") or {}).get("emailAddress"),
        }
    return result


def search_files(payload: dict[str, Any]) -> dict[str, Any]:
    query = translate_query(get_value(payload, "query"))
    page_size = int(get_value(payload, "pageSize", "page_size", default=10))
    page_token = get_value(payload, "pageToken", "page_token")
    return list_files(query, page_size, page_token)


def list_recent_files(payload: dict[str, Any]) -> dict[str, Any]:
    page_size = int(get_value(payload, "pageSize", "page_size", default=10))
    page_token = get_value(payload, "pageToken", "page_token")
    order_by = get_value(payload, "orderBy", "order_by", default="recency")
    order = {
        "recency": "modifiedDate desc",
        "lastModified": "modifiedDate desc",
        "lastModifiedByMe": "modifiedByMeDate desc",
    }.get(str(order_by), "modifiedDate desc")
    _, service = drive_client()
    request = {
        "q": "trashed = false",
        "maxResults": page_size,
        "orderBy": order,
        **SHARED_LIST,
    }
    if page_token:
        request["pageToken"] = page_token
    response = service.files().list(**request).execute()
    return {
        "files": [serialize_file(item) for item in response.get("items", [])],
        "nextPageToken": response.get("nextPageToken"),
    }


def get_file_metadata(payload: dict[str, Any]) -> dict[str, Any]:
    file_id = get_value(payload, "fileId", "file_id", required=True)
    _, service = drive_client()
    file_obj = service.files().get(fileId=file_id, **SHARED_FILE).execute()
    return serialize_file(file_obj)


def get_file_permissions(payload: dict[str, Any]) -> dict[str, Any]:
    file_id = get_value(payload, "fileId", "file_id", required=True)
    _, service = drive_client()
    response = service.permissions().list(fileId=file_id, **SHARED_FILE).execute()
    return {"permissions": response.get("items", [])}


def _download_bytes(file_id: str, export_mime_type: str | None = None) -> tuple[bytes, str]:
    _, service = drive_client()
    meta = service.files().get(fileId=file_id, **SHARED_FILE).execute()
    mime = meta.get("mimeType", "application/octet-stream")
    if mime.startswith("application/vnd.google-apps"):
        export_type = export_mime_type or EXPORT_DEFAULTS.get(mime) or "text/plain"
        request = service.files().export(fileId=file_id, mimeType=export_type)
        mime = export_type
    else:
        request = service.files().get_media(fileId=file_id, **SHARED_FILE)
    buffer = io.BytesIO()
    downloader = MediaIoBaseDownload(buffer, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    return buffer.getvalue(), mime


def download_file_content(payload: dict[str, Any]) -> dict[str, Any]:
    file_id = get_value(payload, "fileId", "file_id", required=True)
    export_mime = get_value(payload, "exportMimeType", "export_mime_type")
    content, mime = _download_bytes(file_id, export_mime)
    return {
        "fileId": file_id,
        "mimeType": mime,
        "base64Content": base64.b64encode(content).decode("ascii"),
    }


def read_file_content(payload: dict[str, Any]) -> dict[str, Any]:
    file_id = get_value(payload, "fileId", "file_id", required=True)
    content, mime = _download_bytes(file_id)
    text = content.decode("utf-8", errors="replace")
    result: dict[str, Any] = {"fileId": file_id, "mimeType": mime, "text": text}
    if get_value(payload, "includeComments", "include_comments"):
        _, service = drive_client()
        comments = service.comments().list(fileId=file_id).execute()
        result["comments"] = comments.get("items", [])
    return result


def create_file(payload: dict[str, Any]) -> dict[str, Any]:
    title = get_value(payload, "title", required=True)
    parent_id = get_value(payload, "parentId", "parent_id")
    mime_type = get_value(payload, "mimeType", "mime_type")
    content_mime = get_value(payload, "contentMimeType", "content_mime_type")
    text_content = get_value(payload, "textContent", "text_content")
    base64_content = get_value(payload, "base64Content", "base64_content", "content")
    metadata: dict[str, Any] = {"title": title}
    if parent_id:
        metadata["parents"] = [{"id": parent_id}]
    if mime_type:
        metadata["mimeType"] = mime_type
    drive, service = drive_client()
    if text_content is None and base64_content is None:
        file_obj = drive.CreateFile(metadata)
        file_obj.Upload()
        return serialize_file(file_obj)
    data = (
        text_content.encode("utf-8")
        if text_content is not None
        else base64.b64decode(base64_content)
    )
    upload_mime = content_mime or mime_type or "application/octet-stream"
    media = MediaIoBaseUpload(io.BytesIO(data), mimetype=upload_mime, resumable=False)
    created = service.files().insert(
        body=metadata, media_body=media, **SHARED_FILE
    ).execute()
    return serialize_file(created)


def copy_file(payload: dict[str, Any]) -> dict[str, Any]:
    file_id = get_value(payload, "fileId", "file_id", required=True)
    title = get_value(payload, "title")
    parent_id = get_value(payload, "parentId", "parent_id")
    body: dict[str, Any] = {}
    if title:
        body["title"] = title
    if parent_id:
        body["parents"] = [{"id": parent_id}]
    _, service = drive_client()
    copied = service.files().copy(fileId=file_id, body=body, **SHARED_FILE).execute()
    return serialize_file(copied)


def update_file(payload: dict[str, Any]) -> dict[str, Any]:
    file_id = get_value(payload, "fileId", "file_id", required=True)
    title = get_value(payload, "title")
    parent_id = get_value(payload, "parentId", "parent_id")
    text_content = get_value(payload, "textContent", "text_content")
    base64_content = get_value(payload, "base64Content", "base64_content", "content")
    content_mime = get_value(payload, "contentMimeType", "content_mime_type")
    body: dict[str, Any] = {}
    if title:
        body["title"] = title
    if parent_id:
        body["parents"] = [{"id": parent_id}]
    _, service = drive_client()
    media = None
    if text_content is not None or base64_content is not None:
        data = (
            text_content.encode("utf-8")
            if text_content is not None
            else base64.b64decode(base64_content)
        )
        media = MediaIoBaseUpload(
            io.BytesIO(data),
            mimetype=content_mime or "application/octet-stream",
            resumable=False,
        )
    updated = service.files().update(
        fileId=file_id,
        body=body,
        media_body=media,
        **SHARED_FILE,
    ).execute()
    return serialize_file(updated)


def trash_file(payload: dict[str, Any]) -> dict[str, Any]:
    file_id = get_value(payload, "fileId", "file_id", required=True)
    _, service = drive_client()
    trashed = service.files().trash(fileId=file_id, **SHARED_FILE).execute()
    return serialize_file(trashed)


def share_file(payload: dict[str, Any]) -> dict[str, Any]:
    file_id = get_value(payload, "fileId", "file_id", required=True)
    role = get_value(payload, "role", default="reader")
    email = get_value(payload, "email", "emailAddress", "email_address")
    permission_type = get_value(payload, "type", default="user" if email else "anyone")
    body: dict[str, Any] = {"role": role, "type": permission_type}
    if email:
        body["value"] = email
    _, service = drive_client()
    permission = service.permissions().insert(
        fileId=file_id,
        body=body,
        sendNotificationEmails=bool(get_value(payload, "sendNotificationEmails", default=False)),
        **SHARED_FILE,
    ).execute()
    return {"fileId": file_id, "permission": permission}


def commands() -> dict[str, Any]:
    return {
        "ping": ping,
        "search_files": search_files,
        "list_recent_files": list_recent_files,
        "get_file_metadata": get_file_metadata,
        "get_file_permissions": get_file_permissions,
        "read_file_content": read_file_content,
        "download_file_content": download_file_content,
        "create_file": create_file,
        "copy_file": copy_file,
        "update_file": update_file,
        "share_file": share_file,
        "trash_file": trash_file,
    }


def main() -> int:
    os.environ.setdefault("OAUTHLIB_RELAX_TOKEN_SCOPE", "1")
    return run_cli(
        "google_drive",
        commands(),
        example="search_files --query \"title contains 'MATH-212'\"",
    )


if __name__ == "__main__":
    raise SystemExit(main())
