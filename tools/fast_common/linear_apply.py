from __future__ import annotations

import datetime as dt
import json
import re
import tempfile
from pathlib import Path
from typing import Any

from fast_common import (
    KIND_TO_LINEAR,
    TERM_START,
    ToolError,
    as_list,
    get_value,
    paginate_linear,
    rel,
    resolve_class,
    run_json_tool,
    truthy,
    vault_root,
)


def linear_workspace() -> dict[str, Any]:
    ping = run_json_tool("linear", ["ping"])
    teams = run_json_tool("linear", ["list_teams"]).get("teams") or []
    team = next(
        (item for item in teams if "Fall 2026" in str(item.get("name") or "")),
        teams[0] if teams else None,
    )
    labels: list[dict[str, Any]] = []
    cycles: list[dict[str, Any]] = []
    statuses: list[dict[str, Any]] = []
    if team:
        labels = run_json_tool("linear", ["list_issue_labels"]).get("labels") or []
        try:
            cycles = (
                run_json_tool("linear", ["list_cycles", "--team", team["id"]]).get("cycles")
                or []
            )
        except ToolError:
            cycles = []
        try:
            statuses = (
                run_json_tool(
                    "linear", ["list_issue_statuses", "--team", team["id"]]
                ).get("statuses")
                or []
            )
        except ToolError:
            statuses = []
    projects = paginate_linear("list_projects", [], "projects")
    return {
        "ping": ping,
        "team": team,
        "labels": labels,
        "cycles": cycles,
        "statuses": statuses,
        "projects": projects,
    }


def issues_for_course(
    course: dict[str, Any],
    team_id: str | None,
    projects: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    args: list[str] = []
    if team_id:
        args.extend(["--team", team_id])
    project = project_id_for(course, projects or [])
    if project:
        args.extend(["--project", project])
    else:
        args.extend(["--query", course["code"]])
    return paginate_linear("list_issues", args, "issues")


def normalize_title(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def match_existing_issue(
    title: str,
    issues: list[dict[str, Any]],
    item: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    needle = normalize_title(title)
    matched_path = str((item or {}).get("matched") or "").replace("\\", "/")
    matched_name = Path(matched_path).name if matched_path else ""
    for issue in issues:
        current = normalize_title(str(issue.get("title") or ""))
        if needle == current or needle in current or current in needle:
            return issue
        description = str(issue.get("description") or "").replace("\\", "/")
        if matched_path and matched_path in description:
            return issue
        if matched_name and matched_name in description:
            return issue
    return None


def project_id_for(course: dict[str, Any], projects: list[dict[str, Any]]) -> str | None:
    slug = str(course.get("linear_slug") or "")
    url = str(course.get("linear_project") or "")
    code = course["code"].lower()
    hyphen = course["hyphen"].lower()
    for project in projects:
        project_id = project.get("id")
        slug_id = str(project.get("slugId") or "")
        if url and str(project.get("url") or "") == url:
            return project_id
        if slug and slug_id and (slug == slug_id or slug.endswith(slug_id)):
            return project_id
        name = str(project.get("name") or "").lower()
        if code in name or hyphen in name:
            return project_id
    return None


def label_id(labels: list[dict[str, Any]], name: str) -> str | None:
    for label in labels:
        if str(label.get("name") or "").lower() == name.lower():
            return label.get("id")
    return None


def cycle_id(cycles: list[dict[str, Any]], week: int | None) -> str | None:
    if not week:
        return None
    wanted = {f"week {week:02d}", f"week {week}"}
    for cycle in cycles:
        name = str(cycle.get("name") or "").lower()
        if name in wanted:
            return cycle.get("id")
        if cycle.get("number") == week:
            return cycle.get("id")
    return None


def issue_title(course: dict[str, Any], item: dict[str, Any]) -> str:
    explicit = str(item.get("title") or "").strip()
    if explicit:
        if explicit.lower().startswith(course["code"].lower()):
            return explicit
        return f"{course['code']} — {explicit}"
    source = str(
        item.get("matched") or item.get("suggested_name") or item.get("name") or "Work"
    )
    stem = Path(source).name.rsplit(".", 1)[0]
    stem = re.sub(rf"^{re.escape(course['hyphen'])}\s+", "", stem)
    compact = re.match(r"^([HRWQL])(\d{2})\b(?:\s*[-–—]+\s*|\s+)?(.*)$", stem, re.I)
    if compact:
        kind_name = {
            "H": "Homework",
            "R": "Reading",
            "W": "Worksheet",
            "Q": "Quiz",
            "L": "Lab",
        }[compact.group(1).upper()]
        rest = compact.group(3).strip(" -–—")
        stem = f"{kind_name} {compact.group(2)}"
        if rest:
            stem = f"{stem} — {rest}"
    return f"{course['code']} — {stem}"


def week_from_due(due: Any) -> int | None:
    text = str(due or "").strip()[:10]
    if not text:
        return None
    try:
        date = dt.date.fromisoformat(text)
    except ValueError:
        return None
    return max(1, min(16, (date - TERM_START).days // 7 + 1))


def attachment_paths(item: dict[str, Any]) -> list[str]:
    paths: list[str] = []
    for value in [
        *as_list(item.get("files")),
        *as_list(item.get("file")),
        *as_list(item.get("attachments")),
        item.get("matched"),
        item.get("destination"),
        item.get("relative"),
    ]:
        if not value:
            continue
        raw = value.get("path") if isinstance(value, dict) else value
        text = str(raw or "").strip()
        if not text or text.startswith("http"):
            continue
        candidate = Path(text)
        if not candidate.is_file():
            candidate = vault_root() / text
        if candidate.is_file():
            relative = rel(candidate)
            if relative not in paths:
                paths.append(relative)
    return paths


def create_or_match_issue(
    course: dict[str, Any],
    item: dict[str, Any],
    workspace: dict[str, Any],
    issues: list[dict[str, Any]],
    *,
    apply: bool,
) -> dict[str, Any]:
    title = issue_title(course, item)
    files = attachment_paths(item)
    existing = match_existing_issue(title, issues, item)
    if existing:
        result = {"status": "matched", "issue": existing, "title": title}
        if apply and files:
            attached = []
            for file in files:
                attached.append(
                    run_json_tool(
                        "linear",
                        [
                            "attach_file",
                            "--issue",
                            str(existing.get("id") or existing.get("identifier")),
                            "--file",
                            file,
                        ],
                    )
                )
            result["attachments"] = attached
        return result
    kind = KIND_TO_LINEAR.get(str(item.get("kind") or ""), "pset")
    due = item.get("due_date") or item.get("dueDate")
    team = workspace.get("team") or {}
    project = project_id_for(course, workspace.get("projects") or [])
    kind_label = label_id(workspace.get("labels") or [], kind)
    week = item.get("week") or week_from_due(due)
    missing = []
    if not team.get("id"):
        missing.append("team")
    if not project:
        missing.append("project")
    if not due:
        missing.append("dueDate")
    if not kind_label:
        missing.append("kind")
    payload = {
        "title": title,
        "status": "pending_create",
        "kind": kind,
        "dueDate": due,
        "files": files,
        "missing": missing,
    }
    if missing or not apply:
        return payload
    attachment = files[0] if files else (
        item.get("matched") or item.get("destination") or item.get("relative")
    )
    week_number = int(week or 1)
    week_path = rel(course["folder"] / "notes" / f"Week-{week_number:02d}.md")
    description = f"Vault source: `{attachment}`\nWeek context: `{week_path}`"
    body: dict[str, Any] = {
        "title": title,
        "team": team["id"],
        "projectId": project,
        "dueDate": str(due),
        "labelIds": [kind_label],
        "description": description,
        "estimate": 2 if kind in {"pset", "lab"} else 1,
    }
    if files:
        body["files"] = files
    cycle = cycle_id(workspace.get("cycles") or [], week)
    if cycle:
        body["cycleId"] = cycle
    handle = tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", suffix=".json", delete=False
    )
    try:
        json.dump(body, handle)
        handle.close()
        created = run_json_tool(
            "linear",
            ["save_issue", "--json-file", handle.name],
        )
    finally:
        Path(handle.name).unlink(missing_ok=True)
    return {"status": "created", "issue": created, "title": title}


def save_course_issues(
    payload: dict[str, Any],
    workspace: dict[str, Any] | None = None,
    *,
    apply: bool | None = None,
) -> dict[str, Any]:
    apply_changes = truthy(get_value(payload, "apply")) if apply is None else apply
    workspace = workspace or linear_workspace()
    specs = as_list(get_value(payload, "issues"))
    if not specs:
        specs = [payload]
    created: list[dict[str, Any]] = []
    matched: list[dict[str, Any]] = []
    pending: list[dict[str, Any]] = []
    results: list[dict[str, Any]] = []
    for spec in specs:
        if not isinstance(spec, dict):
            continue
        merged = {key: value for key, value in payload.items() if key != "issues"}
        merged.update(spec)
        requested = get_value(merged, "class", "course")
        if not requested:
            pending.append({"status": "pending_create", "missing": ["class"]})
            continue
        course = resolve_class(str(requested))
        existing = issues_for_course(
            course,
            (workspace.get("team") or {}).get("id"),
            workspace.get("projects") or [],
        )
        files = as_list(get_value(merged, "file", "files", "attachment", "attachments"))
        item = {
            "title": get_value(merged, "title"),
            "name": get_value(merged, "title", "name") or "Work",
            "kind": get_value(merged, "kind", "label") or "pset",
            "due_date": get_value(merged, "dueDate", "due_date"),
            "files": files,
            "matched": files[0] if files else None,
            "week": get_value(merged, "week") or week_from_due(
                get_value(merged, "dueDate", "due_date")
            ),
        }
        if isinstance(item["matched"], dict):
            item["matched"] = item["matched"].get("path") or item["matched"].get("file")
        result = create_or_match_issue(
            course, item, workspace, existing, apply=apply_changes
        )
        results.append(result)
        status = result.get("status")
        if status == "created":
            created.append(result)
            issue = result.get("issue")
            if issue:
                existing.append(issue)
        elif status == "matched":
            matched.append(result)
        else:
            pending.append(result)
    return {
        "apply": apply_changes,
        "created": created,
        "matched": matched,
        "pending": pending,
        "results": results,
    }


linear_workspace = linear_workspace
issues_for_course = issues_for_course
create_or_match_issue = create_or_match_issue
save_course_issues = save_course_issues
project_id_for = project_id_for
cycle_id = cycle_id
