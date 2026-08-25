from __future__ import annotations

import re
from typing import Any

from fast_common import (
    FORBIDDEN_FIELDS,
    ToolError,
    class_wikilink,
    discover_classes,
    get_value,
    iter_work_notes,
    needs_llm,
    run_cli,
    run_json_tool,
    truthy,
    vault_root,
)
from linear_apply import issues_for_course, linear_workspace, project_id_for
from vault_apply import apply_class_index_links, scaffold_work_note

KIND_LABELS = {
    "pset",
    "reading",
    "lab",
    "quiz",
    "exam",
    "course project",
    "study",
    "admin",
}
WEEK_CYCLE = re.compile(r"(?i)\bweek\s*(\d{1,2})\b")


def assignment_frontmatter(
    course: dict[str, Any],
    issue: dict[str, Any],
    *,
    kind: str,
    week: int | None = None,
    parent: str | None = None,
) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "type": "assignment",
        "linear": issue["identifier"],
        "class": class_wikilink(course),
        "kind": kind,
    }
    if issue.get("url"):
        metadata["linear_url"] = issue["url"]
    if parent:
        metadata["parent"] = parent
    if week:
        metadata["worked"] = [
            f"[[courses/{course['folder'].name}/notes/Week-{week:02d}]]"
        ]
    for field in FORBIDDEN_FIELDS:
        metadata.pop(field, None)
    return metadata


def kind_from_issue(issue: dict[str, Any]) -> tuple[str | None, list[str]]:
    names = [
        str(item.get("name") or "")
        for item in issue.get("labels") or []
        if item.get("name")
    ]
    matched = [name for name in names if name in KIND_LABELS]
    unique = list(dict.fromkeys(matched))
    if len(unique) == 1:
        return unique[0], names
    return None, names


def week_from_cycle(issue: dict[str, Any]) -> int | None:
    cycle = issue.get("cycle") or {}
    name = str(cycle.get("name") or "")
    match = WEEK_CYCLE.search(name)
    if not match:
        return None
    return int(match.group(1))


def course_for_issue(
    issue: dict[str, Any],
    courses: list[dict[str, Any]],
    projects: list[dict[str, Any]],
    team_id: str | None = None,
) -> dict[str, Any] | None:
    project = issue.get("project") or {}
    project_id = project.get("id")
    project_url = str(project.get("url") or "")
    project_name = str(project.get("name") or "")
    if project_id:
        for course in courses:
            if project_id_for(course, projects) == project_id:
                return course
    for course in courses:
        if project_url and str(course.get("linear_project") or "") == project_url:
            return course
        if course["code"] in project_name or course["hyphen"] in project_name:
            return course
    identifier = issue.get("identifier")
    if identifier and team_id:
        for course in courses:
            found = issues_for_course(course, team_id, projects)
            if any(item.get("identifier") == identifier for item in found):
                return course
    return None


def existing_note_for(identifier: str) -> dict[str, Any] | None:
    for note in iter_work_notes():
        if str(note.get("linear") or "") == identifier:
            return note
    return None


def prompt_for_issue(issue: dict[str, Any]) -> str:
    description = str(issue.get("description") or "").strip()
    if not description:
        return ""
    return "\n".join(description.splitlines()[:40])


def run(payload: dict[str, Any]) -> dict[str, Any]:
    identifier = str(get_value(payload, "linear", "id", required=True)).strip()
    apply_changes = truthy(get_value(payload, "apply"))
    overwrite = truthy(get_value(payload, "overwrite"))
    remaining: list[dict[str, Any]] = []
    issue = run_json_tool("linear", ["get_issue", "--id", identifier])
    if not issue.get("identifier"):
        raise ToolError(f"Linear issue {identifier} was not found.", "not_found")
    identifier = str(issue["identifier"])
    workspace = linear_workspace()
    courses = discover_classes()
    course = course_for_issue(
        issue,
        courses,
        workspace.get("projects") or [],
        (workspace.get("team") or {}).get("id"),
    )
    if course is None:
        remaining.append(
            needs_llm(
                "unresolved_course",
                linear=identifier,
                project=(issue.get("project") or {}).get("name"),
                message="Could not match the issue project to a class index.",
            )
        )
        return {
            "apply": apply_changes,
            "planned": False,
            "path": None,
            "linear": identifier,
            "needs_llm": remaining,
        }

    kind, label_names = kind_from_issue(issue)
    if kind is None:
        remaining.append(
            needs_llm(
                "kind_unresolved",
                linear=identifier,
                labels=label_names,
                message="Issue needs exactly one Kind label from the vault ontology.",
            )
        )
        return {
            "apply": apply_changes,
            "planned": False,
            "path": None,
            "linear": identifier,
            "class": course["code"],
            "needs_llm": remaining,
        }

    week = week_from_cycle(issue)
    prompt = prompt_for_issue(issue)
    preview = scaffold_work_note(
        course,
        issue,
        kind=kind,
        week=week,
        prompt=prompt,
        apply=False,
    )
    if preview is None:
        raise ToolError(f"Could not plan a work note for {identifier}.", "tool")
    path = preview["path"]
    existing = existing_note_for(identifier)
    exists = (vault_root() / path).exists() or existing is not None
    if existing and existing["path"] != path:
        path = existing["path"]
    if exists and not overwrite:
        remaining.append(
            needs_llm(
                "note_exists",
                path=path,
                linear=identifier,
                message="Pass --overwrite to replace an existing work note.",
            )
        )
        return {
            "apply": apply_changes,
            "planned": False,
            "updated": False,
            "path": path,
            "linear": identifier,
            "class": course["code"],
            "kind": kind,
            "exists": True,
            "needs_llm": remaining,
        }

    target = vault_root() / path
    if exists and overwrite and apply_changes and target.exists():
        target.unlink()

    result = scaffold_work_note(
        course,
        issue,
        kind=kind,
        week=week,
        prompt=prompt,
        apply=apply_changes,
    )
    if result is None:
        raise ToolError(f"Could not scaffold a work note for {identifier}.", "tool")
    if apply_changes and result.get("updated"):
        apply_class_index_links(course, apply=True)
    if not apply_changes:
        remaining.append(
            needs_llm(
                "apply_required",
                path=result["path"],
                linear=identifier,
                message="Dry-run only. Pass --apply to write the work note.",
            )
        )
    return {
        "apply": apply_changes,
        "planned": True if overwrite and exists else result["planned"],
        "updated": bool(result.get("updated")),
        "path": result["path"],
        "linear": identifier,
        "class": course["code"],
        "kind": kind,
        "exists": exists,
        "overwrite": overwrite,
        "needs_llm": remaining,
    }


def main() -> int:
    return run_cli("fast_scaffold_work_note", {"run": run})


if __name__ == "__main__":
    raise SystemExit(main())
