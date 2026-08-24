from __future__ import annotations

from typing import Any

from fast_common import (
    ToolError,
    discover_classes,
    get_value,
    iter_work_notes,
    needs_llm,
    resolve_classes,
    run_cli,
    run_json_tool,
    strip_frontmatter_keys,
    truthy,
    upsert_frontmatter_key,
    vault_root,
)
from linear_apply import issues_for_course, linear_workspace


def run(payload: dict[str, Any]) -> dict[str, Any]:
    apply_changes = truthy(get_value(payload, "apply"))
    workspace = linear_workspace()
    team_id = (workspace.get("team") or {}).get("id")
    courses = resolve_classes(payload) or discover_classes()
    requested = get_value(payload, "class", "course")
    notes = iter_work_notes()
    if requested:
        allowed = {course["code"] for course in courses}
        notes = [note for note in notes if note["class"] in allowed]
    issue_map: dict[str, dict[str, Any]] = {}
    course_issues: list[dict[str, Any]] = []
    for course in courses:
        issues = issues_for_course(
            course, team_id, workspace.get("projects") or []
        )
        course_issues.append({"class": course["code"], "issues": issues})
        for issue in issues:
            identifier = issue.get("identifier")
            if identifier:
                issue_map[str(identifier)] = issue

    joins_ok: list[dict[str, Any]] = []
    broken: list[dict[str, Any]] = []
    missing_notes: list[dict[str, Any]] = []
    applied: list[str] = []
    remaining: list[dict[str, Any]] = []
    forbidden = []

    note_keys = {note["linear"] for note in notes if note.get("linear")}
    for note in notes:
        key = note.get("linear")
        if not key:
            remaining.append(
                needs_llm("missing_linear_key", path=note["path"])
            )
            continue
        issue = issue_map.get(str(key))
        if issue is None:
            try:
                issue = run_json_tool("linear", ["get_issue", "--id", str(key)])
                issue_map[str(key)] = issue
            except ToolError as error:
                broken.append({"path": note["path"], "linear": key, "error": error.message})
                remaining.append(
                    needs_llm(
                        "broken_join",
                        path=note["path"],
                        linear=key,
                        message="Work note points at a missing or inaccessible Linear issue.",
                    )
                )
                continue
        if note["forbidden"]:
            forbidden.append({"path": note["path"], "fields": note["forbidden"]})
            if apply_changes:
                path = vault_root() / note["path"]
                if strip_frontmatter_keys(path, note["forbidden"]):
                    applied.append(f"removed forbidden fields from {note['path']}")
            else:
                remaining.append(
                    needs_llm(
                        "forbidden_frontmatter",
                        path=note["path"],
                        fields=note["forbidden"],
                    )
                )
        if not note.get("linear_url") and issue.get("url"):
            if apply_changes:
                path = vault_root() / note["path"]
                if upsert_frontmatter_key(path, "linear_url", str(issue["url"])):
                    applied.append(f"added linear_url on {note['path']}")
            else:
                remaining.append(
                    needs_llm(
                        "missing_linear_url",
                        path=note["path"],
                        linear=key,
                    )
                )
        joins_ok.append(
            {
                "path": note["path"],
                "linear": key,
                "url": issue.get("url"),
                "status": issue.get("status"),
                "dueDate": issue.get("dueDate"),
                "project": (issue.get("project") or {}).get("name"),
            }
        )

    for course_block in course_issues:
        for issue in course_block["issues"]:
            identifier = issue.get("identifier")
            labels = [item.get("name") for item in issue.get("labels") or []]
            kind_labels = [
                name
                for name in labels
                if name
                in {
                    "pset",
                    "reading",
                    "lab",
                    "quiz",
                    "exam",
                    "course project",
                    "study",
                    "admin",
                }
            ]
            incomplete = []
            if not issue.get("project"):
                incomplete.append("project")
            if not issue.get("dueDate"):
                incomplete.append("dueDate")
            if len(kind_labels) != 1:
                incomplete.append("kind")
            if incomplete:
                remaining.append(
                    needs_llm(
                        "triage_incomplete",
                        linear=identifier,
                        missing=incomplete,
                    )
                )
            if identifier and identifier not in note_keys:
                missing_notes.append(
                    {
                        "linear": identifier,
                        "title": issue.get("title"),
                        "url": issue.get("url"),
                    }
                )

    remaining.append(
        needs_llm(
            "missing_work_note_is_normal",
            count=len(missing_notes),
            message="Issues without work notes are left missing unless retained prose justifies a note.",
        )
    )
    if not workspace.get("cycles"):
        remaining.append(
            needs_llm(
                "cycles_unconfigured",
                message="Weekly Week NN cycles are not configured; issue creation cannot assign cycles.",
            )
        )

    return {
        "apply": apply_changes,
        "applied": applied,
        "workspace": {
            "team": workspace.get("team"),
            "labelCount": len(workspace.get("labels") or []),
            "cycleCount": len(workspace.get("cycles") or []),
            "statusNames": [item.get("name") for item in workspace.get("statuses") or []],
        },
        "joins_ok": joins_ok,
        "broken_joins": broken,
        "forbidden_frontmatter": forbidden,
        "issues_without_notes": missing_notes,
        "needs_llm": remaining,
    }


def main() -> int:
    return run_cli("fast-linear-sync", {"run": run})


if __name__ == "__main__":
    raise SystemExit(main())
