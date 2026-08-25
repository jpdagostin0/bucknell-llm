from __future__ import annotations

import datetime as dt
import json
import tempfile
from pathlib import Path
from typing import Any

from fast_common import (
    TERM_START,
    get_value,
    needs_llm,
    resolve_classes,
    run_cli,
    run_json_tool,
    truthy,
)
from linear_apply import cycle_id, issues_for_course, linear_workspace, project_id_for

TERM_WEEKS = 16


def week_from_due_date(
    due: dt.date | dt.datetime | str,
    *,
    start: dt.date | None = None,
    max_week: int = TERM_WEEKS,
) -> int:
    start = start or TERM_START
    if isinstance(due, dt.datetime):
        due = due.date()
    elif isinstance(due, str):
        due = dt.date.fromisoformat(due.strip()[:10])
    week = (due - start).days // 7 + 1
    return max(1, min(max_week, week))


def parse_due_date(value: Any) -> dt.date | None:
    if value is None:
        return None
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    text = str(value).strip()
    if not text:
        return None
    try:
        return dt.date.fromisoformat(text[:10])
    except ValueError:
        return None


def current_cycle_id(issue: dict[str, Any]) -> str | None:
    cycle = issue.get("cycle")
    if isinstance(cycle, dict):
        return cycle.get("id")
    if cycle:
        return str(cycle)
    return None


def set_issue_cycle(issue_id: str, cycle: str) -> dict[str, Any]:
    handle = tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", suffix=".json", delete=False
    )
    try:
        json.dump({"id": issue_id, "cycleId": cycle}, handle)
        handle.close()
        return run_json_tool(
            "linear",
            ["save_issue", "--json-file", handle.name],
        )
    finally:
        Path(handle.name).unlink(missing_ok=True)


def collect_issues(
    courses: list[dict[str, Any]],
    workspace: dict[str, Any],
) -> list[dict[str, Any]]:
    team_id = (workspace.get("team") or {}).get("id")
    projects = workspace.get("projects") or []
    seen: set[str] = set()
    collected: list[dict[str, Any]] = []
    for course in courses:
        project_id_for(course, projects)
        for issue in issues_for_course(course, team_id, projects):
            issue_id = str(issue.get("id") or issue.get("identifier") or "")
            if not issue_id or issue_id in seen:
                continue
            seen.add(issue_id)
            collected.append(issue)
    return collected


def run(payload: dict[str, Any]) -> dict[str, Any]:
    apply_requested = truthy(get_value(payload, "apply"))
    courses = resolve_classes(payload)
    workspace = linear_workspace()
    cycles = workspace.get("cycles") or []
    remaining: list[dict[str, Any]] = []
    assignments: list[dict[str, Any]] = []

    if not cycles:
        remaining.append(
            needs_llm(
                "cycles_unconfigured",
                message="Weekly Week NN cycles are not configured; skip apply rather than inventing cycles.",
            )
        )

    apply_changes = apply_requested and bool(cycles)

    for issue in collect_issues(courses, workspace):
        issue_id = issue.get("id")
        due_raw = issue.get("dueDate")
        due = parse_due_date(due_raw)
        record: dict[str, Any] = {
            "id": issue_id,
            "title": issue.get("title"),
            "dueDate": due_raw,
            "week": None,
            "cycleId": None,
            "action": "blocked",
        }
        if due is None:
            remaining.append(
                needs_llm(
                    "missing_due_date",
                    id=issue_id,
                    identifier=issue.get("identifier"),
                    title=issue.get("title"),
                    message="Issue has no dueDate; do not guess a cycle week.",
                )
            )
            assignments.append(record)
            continue

        week = week_from_due_date(due)
        target = cycle_id(cycles, week)
        record["week"] = week
        record["cycleId"] = target
        if not cycles:
            assignments.append(record)
            continue
        if not target:
            remaining.append(
                needs_llm(
                    "cycle_unmatched",
                    id=issue_id,
                    identifier=issue.get("identifier"),
                    week=week,
                    message=f"No Linear cycle named Week {week:02d} or Week {week}.",
                )
            )
            assignments.append(record)
            continue
        if current_cycle_id(issue) == target:
            record["action"] = "skip"
            assignments.append(record)
            continue
        record["action"] = "update"
        if apply_changes:
            set_issue_cycle(str(issue_id), target)
        assignments.append(record)

    return {
        "apply": apply_changes,
        "assignments": assignments,
        "needs_llm": remaining,
    }


def main() -> int:
    return run_cli("fast_assign_cycles", {"run": run})


if __name__ == "__main__":
    raise SystemExit(main())
