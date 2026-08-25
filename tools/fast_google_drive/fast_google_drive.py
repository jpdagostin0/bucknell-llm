from __future__ import annotations

from typing import Any

from fast_common import (
    ToolError,
    copy_new_file,
    download_drive_file,
    get_value,
    google_status,
    list_drive_folder,
    resolve_class,
    run_cli,
    run_json_tool,
    suggested_retain_name,
    truthy,
    vault_root,
)


def require_auth() -> dict[str, Any]:
    status = google_status("google_drive")
    if not status.get("authorized"):
        raise ToolError(
            r"Drive is not authorized. Run python tools/run_tool/run_tool.py google_auth login",
            "needs_auth",
        )
    return status


def run(payload: dict[str, Any]) -> dict[str, Any]:
    require_auth()
    requested = get_value(payload, "class", "course")
    folder_id = get_value(payload, "folderId", "folder_id")
    if requested:
        course = resolve_class(str(requested))
        folder_id = folder_id or course.get("drive_folder_id")
        if not folder_id:
            raise ToolError(f"{course['code']} has no Google Drive content URL.", "usage")
        listed = list_drive_folder(str(folder_id))
        return {
            "class": course["code"],
            "folderId": folder_id,
            "files": listed.get("files") or [],
            "needs_llm": [],
        }
    if folder_id:
        listed = list_drive_folder(str(folder_id))
        return {"folderId": folder_id, "files": listed.get("files") or [], "needs_llm": []}
    recent = run_json_tool("google_drive", ["list_recent_files", "--pageSize", "10"])
    return {"recent": recent.get("files") or [], "needs_llm": []}


def download(payload: dict[str, Any]) -> dict[str, Any]:
    require_auth()
    file_id = get_value(payload, "fileId", "file_id", "id", required=True)
    title = str(get_value(payload, "title", default=f"{file_id}.bin"))
    requested = get_value(payload, "class", "course")
    apply_changes = truthy(get_value(payload, "apply"))
    staging = vault_root() / "tools/fast_google_drive/output" / title
    downloaded = download_drive_file(str(file_id), staging)
    retained = None
    if apply_changes:
        if not requested:
            raise ToolError("Pass --class to retain a Drive file in the vault.", "usage")
        course = resolve_class(str(requested))
        destination = vault_root() / "attachments" / suggested_retain_name(course, title)
        retained = copy_new_file(
            staging,
            destination,
            overwrite=truthy(get_value(payload, "overwrite")),
        )
    return {**downloaded, "retained": retained, "needs_llm": []}


def main() -> int:
    return run_cli("fast_google_drive", {"run": run, "download": download})


if __name__ == "__main__":
    raise SystemExit(main())
