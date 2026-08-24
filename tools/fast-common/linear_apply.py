from __future__ import annotations

import json
import re
import tempfile
from pathlib import Path
from typing import Any

from fast_common import (
    KIND_TO_LINEAR,
    ToolError,
    paginate_linear,
    rel,
    run_json_tool,
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
    return None


def issue_title(course: dict[str, Any], item: dict[str, Any]) -> str:
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


def create_or_match_issue(
    course: dict[str, Any],
    item: dict[str, Any],
    workspace: dict[str, Any],
    issues: list[dict[str, Any]],
    *,
    apply: bool,
) -> dict[str, Any]:
    title = issue_title(course, item)
    existing = match_existing_issue(title, issues, item)
    if existing:
        return {"status": "matched", "issue": existing, "title": title}
    kind = KIND_TO_LINEAR.get(str(item.get("kind") or ""), "pset")
    due = item.get("due_date")
    team = workspace.get("team") or {}
    project = project_id_for(course, workspace.get("projects") or [])
    kind_label = label_id(workspace.get("labels") or [], kind)
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
        "missing": missing,
    }
    if missing or not apply:
        return payload
    attachment = item.get("matched") or item.get("destination") or item.get("relative")
    week_number = int(item.get("week") or 1)
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
    cycle = cycle_id(workspace.get("cycles") or [], item.get("week"))
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


linear_workspace = linear_workspace
issues_for_course = issues_for_course
create_or_match_issue = create_or_match_issue
project_id_for = project_id_for
cycle_id = cycle_id
