from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from fast_common import (
    KIND_TO_LINEAR,
    ToolError,
    attachment_wikilink,
    compare_retained,
    convert_pdf,
    copy_new_file,
    download_drive_file,
    drive_download_plan,
    extract_printed_pages,
    find_section_labels,
    get_value,
    google_status,
    inventory_moodle,
    list_drive_folder,
    needs_llm,
    parse_due_date,
    printed_spec,
    read_url_file,
    rel,
    resolve_classes,
    run_cli,
    run_moodle_sync,
    suggested_retain_name,
    truthy,
    vault_root,
)
from linear_apply import create_or_match_issue, issues_for_course, linear_workspace
from vault_apply import (
    apply_class_index_links,
    apply_syllabus,
    extract_syllabus_facts,
    extract_topics,
    material_label,
    scaffold_work_note,
    upsert_week_note,
)


def inspect_drive(course: dict[str, Any], staged_names: set[str]) -> dict[str, Any]:
    folder_id = course.get("drive_folder_id")
    if not folder_id:
        return {"skipped": True, "reason": "no content URL"}
    status = google_status("google-drive")
    if not status.get("authorized"):
        return {
            "skipped": True,
            "status": status,
            "needs_user": [
                needs_llm(
                    "google_auth",
                    command=r".\tools\google-auth\google-auth.ps1 login",
                    message="Drive is not authorized.",
                )
            ],
        }
    listed = list_drive_folder(folder_id)
    missing = []
    for file_obj in listed.get("files") or []:
        title = str(file_obj.get("title") or "")
        if title.lower() not in staged_names:
            missing.append(
                {
                    "id": file_obj.get("id"),
                    "title": title,
                    "mimeType": file_obj.get("mimeType"),
                    "modifiedDate": file_obj.get("modifiedDate"),
                }
            )
    return {
        "folderId": folder_id,
        "fileCount": len(listed.get("files") or []),
        "not_in_moodle": missing,
    }


def extract_homework_pages(
    course: dict[str, Any],
    converted: dict[str, Any],
    item: dict[str, Any],
) -> dict[str, Any] | None:
    textbooks = course.get("textbooks") or []
    if not textbooks:
        return None
    textbook = textbooks[0]
    spec = printed_spec(converted.get("page_citations") or [])
    if not spec:
        labels: list[str] = []
        for section in converted.get("section_citations") or []:
            labels.extend(find_section_labels(textbook, section))
        unique = []
        for label in labels:
            if label not in unique:
                unique.append(label)
        if unique:
            spec = ",".join(unique)
    if not spec:
        return None
    output = (
        vault_root()
        / "tools/pypdf/output"
        / f"{course['hyphen']} {Path(item['name']).stem} pages.pdf"
    )
    if output.exists():
        return {"output": rel(output), "printed_pages": spec, "exists": True}
    try:
        return extract_printed_pages(textbook, spec, output)
    except ToolError as error:
        return {"error": error.message, "printed_pages": spec}


def process_course(course: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    apply_changes = truthy(get_value(payload, "apply", "retain"))
    overwrite = truthy(get_value(payload, "overwrite"))
    convert = not truthy(get_value(payload, "skipConvert", "skip_convert"))
    staged = inventory_moodle(course)
    staged_names = {item["name"].lower() for item in staged}
    drive = inspect_drive(course, staged_names)
    remaining = list(drive.get("needs_user") or [])
    retained: list[dict[str, Any]] = []
    copied: list[str] = []
    converted_docs: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    review: list[dict[str, Any]] = []
    pending: list[dict[str, Any]] = []
    week_materials: dict[int, list[dict[str, Any]]] = defaultdict(list)
    syllabus_text = ""
    syllabus_pdf: Path | None = None
    converted_by_relative: dict[str, dict[str, Any]] = {}

    for item in staged:
        comparison = compare_retained(course, item)
        record = {**item, **comparison, "path": item["relative"]}
        record.pop("sha256", None)
        dest = Path(comparison["destination"])
        retained_path = Path(vault_root() / comparison["matched"]) if comparison["matched"] else dest
        if item["action"] == "skip":
            skipped.append(record)
            continue
        if item["action"] == "link":
            url = read_url_file(Path(item["path"]))
            if url and item.get("week"):
                week_materials[int(item["week"])].append(
                    {"link": f"[{item['name']}]({url})", "kind": "link"}
                )
            skipped.append(record)
            continue

        converted = None
        if convert and str(item["name"]).lower().endswith(".pdf"):
            try:
                converted = convert_pdf(
                    Path(item["path"]),
                    f"{course['hyphen']} {item['name']}".replace(".pdf", ".md"),
                )
                converted_docs.append(
                    {key: value for key, value in converted.items() if key != "text"}
                )
                converted_by_relative[item["relative"]] = converted
                record["due_date"] = converted.get("due_date")
                record["due_hints"] = converted.get("due_hints")
            except ToolError as error:
                remaining.append(
                    needs_llm(
                        "convert_failed",
                        class_code=course["code"],
                        path=item["relative"],
                        message=error.message,
                    )
                )

        if comparison["status"] == "name_conflict" and not overwrite:
            pending.append(
                {
                    "action": "overwrite",
                    "path": item["relative"],
                    "matched": comparison["matched"],
                    "message": "Pass --apply --overwrite to replace the retained file.",
                }
            )
            review.append(record)
            continue
        if item["action"] in {"retain", "textbook"}:
            if comparison["status"] == "new" or (
                comparison["status"] == "name_conflict" and overwrite
            ):
                if apply_changes:
                    copied.append(
                        copy_new_file(
                            Path(item["path"]),
                            dest,
                            overwrite=overwrite,
                        )
                    )
                    record["status"] = "copied"
                    retained_path = dest
                else:
                    pending.append(
                        {
                            "action": "retain",
                            "path": item["relative"],
                            "destination": comparison["destination"],
                        }
                    )
            retained.append(record)

        if item["kind"] == "syllabus" and converted:
            syllabus_text = converted.get("text") or ""
            if retained_path.exists():
                syllabus_pdf = retained_path
        link_target = retained_path if retained_path.exists() else dest
        week = item.get("week")
        if week:
            material = {
                "link": attachment_wikilink(
                    link_target, material_label(link_target.name)
                ),
                "kind": item["kind"],
                "topics": extract_topics(converted["text"]) if converted else [],
            }
            week_materials[int(week)].append(material)
        if converted and item["kind"] == "homework" and apply_changes:
            pages = extract_homework_pages(course, converted, item)
            if pages:
                record["homework_pages"] = pages

    downloaded = []
    for file_obj in drive.get("not_in_moodle") or []:
        plan = drive_download_plan(file_obj)
        if plan["action"] == "skip_folder":
            continue
        if plan["action"] == "review":
            pending.append(
                {
                    "action": "drive_review",
                    "title": plan.get("title"),
                    "id": plan.get("id"),
                }
            )
            continue
        title = str(plan.get("filename") or plan.get("title") or "drive-file")
        suggested = suggested_retain_name(course, title)
        dest = vault_root() / "attachments" / suggested
        if dest.exists():
            continue
        if apply_changes:
            staging = vault_root() / "tools/google-drive/output" / suggested
            try:
                download_drive_file(
                    str(file_obj["id"]),
                    staging,
                    export_mime_type=plan.get("exportMimeType"),
                )
                copied.append(copy_new_file(staging, dest))
                downloaded.append(rel(dest))
            except ToolError as error:
                remaining.append(
                    needs_llm(
                        "drive_download_failed",
                        title=title,
                        message=error.message,
                    )
                )
        else:
            pending.append(
                {
                    "action": "drive_download",
                    "title": title,
                    "id": file_obj.get("id"),
                }
            )

    notes_updated = []
    for week, materials in sorted(week_materials.items()):
        notes_updated.append(
            upsert_week_note(course, week, materials, apply=apply_changes)
        )

    syllabus_result = None
    facts = extract_syllabus_facts(syllabus_text) if syllabus_text else {}
    if syllabus_text:
        syllabus_result = apply_syllabus(
            course, syllabus_text, syllabus_pdf, apply=apply_changes
        )
    index_result = apply_class_index_links(course, facts, apply=apply_changes)

    linear_results: list[dict[str, Any]] = []
    work_notes: list[dict[str, Any]] = []
    deadline_items = [
        item
        for item in retained
        if item.get("deadline") or item.get("kind") in KIND_TO_LINEAR
    ]
    if deadline_items:
        try:
            workspace = linear_workspace()
            existing = issues_for_course(
                course,
                (workspace.get("team") or {}).get("id"),
                workspace.get("projects") or [],
            )
            for item in deadline_items:
                if item.get("kind") not in {"homework", "quiz", "exam", "lab"}:
                    continue
                converted = converted_by_relative.get(item.get("relative") or "")
                if converted and not item.get("due_date"):
                    item["due_date"] = converted.get("due_date") or parse_due_date(
                        " ".join(converted.get("due_hints") or [])
                    )
                try:
                    result = create_or_match_issue(
                        course, item, workspace, existing, apply=apply_changes
                    )
                except ToolError as error:
                    result = {
                        "status": "error",
                        "title": item.get("suggested_name"),
                        "message": error.message,
                    }
                linear_results.append(result)
                issue = result.get("issue")
                if (
                    apply_changes
                    and issue
                    and converted
                    and int(converted.get("characters") or 0) >= 400
                ):
                    note = scaffold_work_note(
                        course,
                        issue,
                        kind=KIND_TO_LINEAR.get(str(item.get("kind")), "pset"),
                        week=item.get("week"),
                        prompt="\n".join((converted.get("text") or "").splitlines()[:40]),
                        apply=True,
                    )
                    if note:
                        work_notes.append(note)
            if work_notes:
                apply_class_index_links(course, facts, apply=True)
        except ToolError as error:
            remaining.append(
                needs_llm("linear_unavailable", message=error.message)
            )

    return {
        "class": course["code"],
        "folder": rel(course["folder"]),
        "drive": {key: value for key, value in drive.items() if key != "needs_user"},
        "staged": len(staged),
        "retained": retained,
        "copied": copied,
        "downloaded": downloaded,
        "converted": converted_docs,
        "skipped": skipped,
        "review": review,
        "pending": pending,
        "notes": notes_updated,
        "syllabus": syllabus_result,
        "class_index": index_result,
        "linear": linear_results,
        "work_notes": work_notes,
        "needs_llm": remaining,
    }


def run(payload: dict[str, Any]) -> dict[str, Any]:
    moodle = run_moodle_sync(
        skip_download=truthy(get_value(payload, "skipDownload", "skip_download"))
    )
    remaining = list(moodle.get("needs_user") or [])
    courses = []
    for course in resolve_classes(payload):
        result = process_course(course, payload)
        remaining.extend(result["needs_llm"])
        courses.append(result)
    if not courses:
        raise ToolError("No enrolled classes matched the request.", "usage")
    return {
        "moodle": {key: value for key, value in moodle.items() if key != "needs_user"},
        "apply": truthy(get_value(payload, "apply", "retain")),
        "courses": courses,
        "needs_llm": remaining,
    }


def main() -> int:
    return run_cli("fast-sync-class", {"run": run})


if __name__ == "__main__":
    raise SystemExit(main())
