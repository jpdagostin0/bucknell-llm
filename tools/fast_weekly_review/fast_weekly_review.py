from __future__ import annotations

import datetime as dt
import re
from pathlib import Path
from typing import Any

from fast_common import (
    DEADLINE_HINT,
    TERM_START,
    discover_classes,
    get_value,
    load_frontmatter,
    needs_llm,
    paginate_linear,
    parse_due_date,
    rel,
    resolve_classes,
    run_cli,
    truthy,
    vault_root,
)
from linear_apply import issues_for_course, linear_workspace

TERMINAL_STATUS_NAMES = {
    "canceled",
    "cancelled",
    "completed",
    "done",
    "excused",
    "graded",
    "missed",
    "submitted",
}
TERMINAL_STATUS_TYPES = {"canceled", "completed"}
WEEK_NAME = re.compile(r"week\s*(\d{1,2})", re.I)


def term_week(
    on: dt.date | None = None,
    *,
    term_start: dt.date = TERM_START,
) -> int:
    """Return the 1-based Fall 2026 week for a calendar date.

    Weeks are Monday-aligned from ``term_start``. Dates before the term
    clamp to week 1 rather than week 0.
    """
    today = on or dt.date.today()
    monday = term_start - dt.timedelta(days=term_start.weekday())
    week = (today - monday).days // 7 + 1
    return max(week, 1)


def week_date_range(
    week: int,
    *,
    term_start: dt.date = TERM_START,
) -> tuple[dt.date, dt.date]:
    start = term_start + dt.timedelta(weeks=max(week, 1) - 1)
    start -= dt.timedelta(days=start.weekday())
    return start, start + dt.timedelta(days=6)


def week_from_cycle(cycle: Any) -> int | None:
    if not cycle:
        return None
    if isinstance(cycle, dict):
        name = str(cycle.get("name") or "")
    else:
        name = str(cycle)
    match = WEEK_NAME.search(name)
    if match:
        return int(match.group(1))
    return None


def issue_cycle(issue: dict[str, Any]) -> dict[str, Any] | None:
    cycle = issue.get("cycle")
    return cycle if isinstance(cycle, dict) and cycle.get("id") else None


def is_open_issue(issue: dict[str, Any]) -> bool:
    status_type = str(issue.get("statusType") or "").strip().lower()
    if status_type in TERMINAL_STATUS_TYPES:
        return False
    name = str(issue.get("status") or "").strip().lower()
    return name not in TERMINAL_STATUS_NAMES


def estimate_points(issue: dict[str, Any]) -> int | None:
    value = issue.get("estimate")
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _inbox_body(text: str) -> str:
    if text.startswith("---"):
        closing = text.find("\n---", 3)
        if closing >= 0:
            return text[closing + 4 :]
    return text


def classify_inbox_file(path: Path) -> dict[str, Any]:
    metadata = load_frontmatter(path)
    note_type = metadata.get("type")
    captured = metadata.get("captured")
    text = path.read_text(encoding="utf-8", errors="replace")
    body = _inbox_body(text)
    blob = f"{path.name}\n{body}"
    due_hint = parse_due_date(body)
    deadline_bearing = bool(DEADLINE_HINT.search(blob) or due_hint)
    if deadline_bearing:
        classification = "deadline"
    elif str(note_type or "").strip().lower() == "capture":
        classification = "capture"
    else:
        classification = "capture" if not metadata else "other"
    item = {
        "path": rel(path),
        "classification": classification,
        "deadline_bearing": deadline_bearing,
    }
    if note_type is not None:
        item["type"] = note_type
    if captured is not None:
        item["captured"] = captured
    return item


def collect_inbox() -> list[dict[str, Any]]:
    inbox = vault_root() / "inbox"
    if not inbox.is_dir():
        return []
    items: list[dict[str, Any]] = []
    for path in sorted(inbox.glob("*.md")):
        if path.name.startswith("."):
            continue
        items.append(classify_inbox_file(path))
    return items


def collect_issues(
    payload: dict[str, Any],
    workspace: dict[str, Any],
) -> list[dict[str, Any]]:
    team_id = (workspace.get("team") or {}).get("id")
    requested = get_value(payload, "class", "course", "code")
    if requested:
        courses = resolve_classes(payload)
        issues: list[dict[str, Any]] = []
        seen: set[str] = set()
        for course in courses:
            for issue in issues_for_course(
                course, team_id, workspace.get("projects") or []
            ):
                key = str(issue.get("id") or issue.get("identifier") or "")
                if key and key in seen:
                    continue
                if key:
                    seen.add(key)
                issues.append(issue)
        return issues
    args: list[str] = []
    if team_id:
        args.extend(["--team", str(team_id)])
    return paginate_linear("list_issues", args, "issues")


def requested_week(payload: dict[str, Any]) -> int:
    value = get_value(payload, "week")
    if value is None or value is True:
        return term_week()
    week = int(value)
    if week < 1:
        return 1
    return week


def run(payload: dict[str, Any]) -> dict[str, Any]:
    apply_changes = truthy(get_value(payload, "apply"))
    week = requested_week(payload)
    remaining: list[dict[str, Any]] = []
    inbox = collect_inbox()
    for item in inbox:
        if item.get("deadline_bearing"):
            remaining.append(
                needs_llm(
                    "inbox_deadline",
                    path=item["path"],
                    message=(
                        "Deadline-bearing inbox files belong in Linear triage. "
                        "Do not invent issues from this file."
                    ),
                )
            )

    workspace = linear_workspace()
    cycles = workspace.get("cycles") or []
    cycles_configured = bool(cycles)
    if not cycles_configured:
        remaining.append(
            needs_llm(
                "cycles_unconfigured",
                message=(
                    "Weekly Week NN cycles are not configured; "
                    "cycle assignment and per-week load from cycles cannot be verified."
                ),
            )
        )

    issues = collect_issues(payload, workspace)
    open_issues = [issue for issue in issues if is_open_issue(issue)]

    issues_without_cycle: list[dict[str, Any]] = []
    if cycles_configured:
        for issue in open_issues:
            if issue_cycle(issue):
                continue
            issues_without_cycle.append(
                {
                    "linear": issue.get("identifier"),
                    "title": issue.get("title"),
                    "url": issue.get("url"),
                    "status": issue.get("status"),
                }
            )
            remaining.append(
                needs_llm(
                    "missing_cycle",
                    linear=issue.get("identifier"),
                    title=issue.get("title"),
                    message="Open issue has no Week NN cycle.",
                )
            )

    load_buckets: dict[tuple[int | None, str | None], dict[str, Any]] = {}
    for issue in open_issues:
        cycle = issue_cycle(issue)
        cycle_week = week_from_cycle(cycle)
        raw_name = cycle.get("name") if cycle else None
        cycle_name = str(raw_name) if raw_name else None
        key = (cycle_week, cycle_name)
        bucket = load_buckets.setdefault(
            key,
            {
                "week": cycle_week,
                "cycle": cycle_name,
                "estimate_sum": 0,
                "issue_count": 0,
                "missing_estimate": 0,
            },
        )
        bucket["issue_count"] += 1
        points = estimate_points(issue)
        if points is None:
            bucket["missing_estimate"] += 1
        else:
            bucket["estimate_sum"] += points

    weekly_load = sorted(
        load_buckets.values(),
        key=lambda item: (
            item["week"] is None,
            item["week"] if item["week"] is not None else 0,
            str(item["cycle"] or ""),
        ),
    )

    unfinished: list[dict[str, Any]] = []
    week_start, week_end = week_date_range(week)
    for issue in open_issues:
        cycle = issue_cycle(issue)
        cycle_week = week_from_cycle(cycle)
        in_week = cycle_week == week
        if not cycles_configured:
            due = issue.get("dueDate")
            due_date = None
            if due:
                try:
                    due_date = dt.date.fromisoformat(str(due)[:10])
                except ValueError:
                    due_date = None
            in_week = bool(due_date and week_start <= due_date <= week_end)
        if not in_week:
            continue
        unfinished.append(
            {
                "linear": issue.get("identifier"),
                "title": issue.get("title"),
                "url": issue.get("url"),
                "status": issue.get("status"),
                "week": week,
                "actions": ["roll", "miss", "excuse"],
            }
        )
        remaining.append(
            needs_llm(
                "unfinished_issue",
                linear=issue.get("identifier"),
                title=issue.get("title"),
                week=week,
                status=issue.get("status"),
                actions=["roll", "miss", "excuse"],
                message=(
                    "Choose roll, miss, or excuse explicitly. "
                    "Do not set Missed automatically. "
                    "Never reopen an original submission."
                ),
            )
        )

    applied: list[str] = []
    if apply_changes:
        remaining.append(
            needs_llm(
                "linear_status_unchanged",
                message=(
                    "--apply does not change Linear statuses or create issues. "
                    "Inbox deadline files were classified only."
                ),
            )
        )

    requested = get_value(payload, "class", "course", "code")
    courses = resolve_classes(payload) if requested else discover_classes()
    return {
        "apply": apply_changes,
        "week": week,
        "class": str(requested) if requested and requested is not True else None,
        "linear_mutated": False,
        "applied": applied,
        "inbox": inbox,
        "issues_without_cycle": issues_without_cycle,
        "weekly_load": weekly_load,
        "unfinished": unfinished,
        "needs_llm": remaining,
        "workspace": {
            "team": (workspace.get("team") or {}).get("name"),
            "cycleCount": len(cycles),
            "statusNames": [
                item.get("name") for item in workspace.get("statuses") or []
            ],
        },
        "classes": [course["code"] for course in courses],
    }


def main() -> int:
    return run_cli("fast_weekly_review", {"run": run})


if __name__ == "__main__":
    raise SystemExit(main())
