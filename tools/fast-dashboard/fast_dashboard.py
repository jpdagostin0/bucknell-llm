from __future__ import annotations

import datetime as dt
import re
import sys
from pathlib import Path
from typing import Any

_FAST_COMMON = Path(__file__).resolve().parents[1] / "fast-common"
if str(_FAST_COMMON) not in sys.path:
    sys.path.insert(0, str(_FAST_COMMON))

from fast_common import (  # noqa: E402
    TERM_START,
    ToolError,
    discover_classes,
    emit,
    get_value,
    needs_llm,
    parse_invocation,
    resolve_classes,
    run_cli,
)
from linear_apply import issues_for_course, linear_workspace  # noqa: E402

CLOSED_STATUS_NAMES = frozenset(
    {
        "done",
        "canceled",
        "cancelled",
        "completed",
        "graded",
        "missed",
        "excused",
    }
)
CLOSED_STATUS_TYPES = frozenset({"completed", "canceled"})
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
WEEK_NAME = re.compile(r"\bweek\s*(\d{1,2})\b", re.I)


def status_name(issue: dict[str, Any]) -> str:
    status = issue.get("status")
    if isinstance(status, dict):
        return str(status.get("name") or "").strip()
    return str(status or "").strip()


def status_type(issue: dict[str, Any]) -> str:
    raw = issue.get("statusType")
    if raw:
        return str(raw).strip().lower()
    status = issue.get("status")
    if isinstance(status, dict):
        return str(status.get("type") or "").strip().lower()
    return ""


def is_open_issue(issue: dict[str, Any]) -> bool:
    if status_type(issue) in CLOSED_STATUS_TYPES:
        return False
    return status_name(issue).lower() not in CLOSED_STATUS_NAMES


def label_names(issue: dict[str, Any]) -> list[str]:
    names: list[str] = []
    for item in issue.get("labels") or []:
        if isinstance(item, str) and item.strip():
            names.append(item.strip())
        elif isinstance(item, dict) and item.get("name"):
            names.append(str(item["name"]).strip())
    return names


def issue_kind(issue: dict[str, Any]) -> str | None:
    kind = issue.get("kind")
    if kind:
        return str(kind)
    lowered = {name.lower(): name for name in KIND_LABELS}
    for name in label_names(issue):
        match = lowered.get(name.lower())
        if match:
            return match
    return None


def is_exam_issue(issue: dict[str, Any]) -> bool:
    kind = issue_kind(issue)
    if kind and kind.lower() == "exam":
        return True
    return any(name.lower() == "exam" for name in label_names(issue))


def parse_iso_date(value: Any) -> dt.date | None:
    if value in (None, ""):
        return None
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return dt.date.fromisoformat(text[:10])
    except ValueError:
        return None


def cycle_name(issue: dict[str, Any]) -> str | None:
    cycle = issue.get("cycle")
    if isinstance(cycle, dict):
        name = cycle.get("name")
        return str(name) if name else None
    if isinstance(cycle, str) and cycle.strip():
        return cycle.strip()
    return None


def week_from_cycle_name(name: str | None) -> int | None:
    if not name:
        return None
    match = WEEK_NAME.search(name)
    return int(match.group(1)) if match else None


def week_from_due_date(value: Any) -> int | None:
    parsed = parse_iso_date(value)
    if parsed is None:
        return None
    delta = (parsed - TERM_START).days
    if delta < 0:
        return None
    return (delta // 7) + 1


def week_for_issue(issue: dict[str, Any]) -> int | None:
    return week_from_cycle_name(cycle_name(issue)) or week_from_due_date(
        issue.get("dueDate")
    )


def due_sort_key(issue: dict[str, Any]) -> tuple[int, str]:
    parsed = parse_iso_date(issue.get("dueDate"))
    if parsed is None:
        return (1, "9999-12-31")
    return (0, parsed.isoformat())


def summarize_issue(issue: dict[str, Any], course: dict[str, Any] | None) -> dict[str, Any]:
    due = parse_iso_date(issue.get("dueDate"))
    week = week_for_issue(issue)
    return {
        "identifier": issue.get("identifier"),
        "title": issue.get("title"),
        "class": None if course is None else course.get("code"),
        "kind": issue_kind(issue),
        "dueDate": due.isoformat() if due else issue.get("dueDate"),
        "status": status_name(issue) or None,
        "priority": issue.get("priority"),
        "estimate": issue.get("estimate"),
        "cycle": cycle_name(issue),
        "week": week,
        "url": issue.get("url"),
    }


def collect_dashboard(
    course_issues: list[tuple[dict[str, Any], list[dict[str, Any]]]],
    *,
    cycles: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    due_work: list[dict[str, Any]] = []
    exams: list[dict[str, Any]] = []
    buckets: dict[str, dict[str, Any]] = {}
    remaining: list[dict[str, Any]] = []
    seen: set[str] = set()

    for course, issues in course_issues:
        for issue in issues:
            identifier = str(issue.get("identifier") or issue.get("id") or "")
            if identifier and identifier in seen:
                continue
            if identifier:
                seen.add(identifier)
            if not is_open_issue(issue):
                continue
            summary = summarize_issue(issue, course)
            kind = summary["kind"]
            if not kind:
                remaining.append(
                    needs_llm(
                        "missing_kind",
                        linear=summary["identifier"],
                        title=summary["title"],
                    )
                )
            if not summary["dueDate"]:
                remaining.append(
                    needs_llm(
                        "missing_due_date",
                        linear=summary["identifier"],
                        title=summary["title"],
                    )
                )
            if summary["estimate"] is None:
                remaining.append(
                    needs_llm(
                        "missing_estimate",
                        linear=summary["identifier"],
                        title=summary["title"],
                    )
                )
            if is_exam_issue(issue):
                exams.append(summary)
            else:
                due_work.append(summary)
            week = summary["week"]
            key = f"Week {week:02d}" if week else "Unscheduled"
            bucket = buckets.setdefault(
                key,
                {
                    "week": week,
                    "cycle": key,
                    "estimate_total": 0,
                    "issue_count": 0,
                    "unestimated": 0,
                    "issues": [],
                },
            )
            estimate = summary["estimate"]
            if isinstance(estimate, (int, float)):
                bucket["estimate_total"] += estimate
            else:
                bucket["unestimated"] += 1
            bucket["issue_count"] += 1
            bucket["issues"].append(summary["identifier"] or summary["title"])

    due_work.sort(key=lambda item: due_sort_key(item))
    exams.sort(key=lambda item: due_sort_key(item))
    weekly_load = sorted(
        buckets.values(),
        key=lambda item: (item["week"] is None, item["week"] or 0, item["cycle"]),
    )
    if not cycles:
        remaining.append(
            needs_llm(
                "cycles_unconfigured",
                message="Weekly Week NN cycles were not returned; weekly_load falls back to due dates from 2026-08-24.",
            )
        )
    remaining.append(
        needs_llm(
            "live_linear_state",
            message="Present this snapshot in chat. Do not copy due, status, priority, or estimate into vault frontmatter or Home.md.",
        )
    )
    return {
        "due_work": due_work,
        "exams": exams,
        "weekly_load": weekly_load,
        "needs_llm": remaining,
    }


def fetch_dashboard(payload: dict[str, Any]) -> dict[str, Any]:
    workspace = linear_workspace()
    team_id = (workspace.get("team") or {}).get("id")
    courses = resolve_classes(payload) or discover_classes()
    course_issues: list[tuple[dict[str, Any], list[dict[str, Any]]]] = []
    for course in courses:
        issues = issues_for_course(
            course, team_id, workspace.get("projects") or []
        )
        course_issues.append((course, issues))
    snapshot = collect_dashboard(course_issues, cycles=workspace.get("cycles") or [])
    snapshot["classes"] = [course["code"] for course in courses]
    return snapshot


def render_markdown(snapshot: dict[str, Any]) -> str:
    lines = ["# Fall 2026 dashboard", ""]

    def table(title: str, rows: list[dict[str, Any]]) -> None:
        lines.append(f"## {title}")
        lines.append("")
        if not rows:
            lines.append("None.")
            lines.append("")
            return
        lines.append("| Class | Issue | Due | Status | Estimate |")
        lines.append("| --- | --- | --- | --- | --- |")
        for item in rows:
            identifier = item.get("identifier") or ""
            title_text = item.get("title") or ""
            issue = f"{identifier} {title_text}".strip()
            lines.append(
                "| "
                + " | ".join(
                    [
                        str(item.get("class") or ""),
                        issue,
                        str(item.get("dueDate") or ""),
                        str(item.get("status") or ""),
                        str(item.get("estimate") if item.get("estimate") is not None else ""),
                    ]
                )
                + " |"
            )
        lines.append("")

    table("Due work", snapshot.get("due_work") or [])
    table("Exams", snapshot.get("exams") or [])
    lines.append("## Weekly load")
    lines.append("")
    weekly = snapshot.get("weekly_load") or []
    if not weekly:
        lines.append("None.")
        lines.append("")
    for bucket in weekly:
        lines.append(f"### {bucket['cycle']}")
        lines.append("")
        lines.append(
            f"Estimate total: {bucket['estimate_total']} across {bucket['issue_count']} open issues"
            + (
                f" ({bucket['unestimated']} unestimated)."
                if bucket.get("unestimated")
                else "."
            )
        )
        lines.append("")
        for identifier in bucket.get("issues") or []:
            lines.append(f"- {identifier}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def run(payload: dict[str, Any]) -> dict[str, Any]:
    return fetch_dashboard(payload)


def markdown(payload: dict[str, Any]) -> dict[str, Any]:
    snapshot = fetch_dashboard(payload)
    snapshot["markdown"] = render_markdown(snapshot)
    return snapshot


def main() -> int:
    argv = list(sys.argv[1:])
    command = argv[0] if argv and not argv[0].startswith("-") else "run"
    if command == "markdown":
        try:
            _, payload = parse_invocation(argv, default_command="run")
            sys.stdout.write(render_markdown(fetch_dashboard(payload)))
            return 0
        except ToolError as error:
            emit(
                {
                    "ok": False,
                    "command": "markdown",
                    "error": {"code": error.code, "message": error.message},
                },
                error=True,
            )
            return 1
    return run_cli(
        "fast-dashboard",
        {"run": run, "markdown": markdown},
    )


if __name__ == "__main__":
    raise SystemExit(main())
