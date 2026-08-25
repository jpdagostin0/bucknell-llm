from __future__ import annotations

from typing import Any

from fast_common import get_value, needs_llm, payload_flags, resolve_class, run_cli, run_json_tool, truthy
from linear_apply import issues_for_course, linear_workspace, save_course_issues


def preflight(_: dict[str, Any] | None = None) -> dict[str, Any]:
    workspace = linear_workspace()
    return {
        "ping": workspace.get("ping"),
        "team": workspace.get("team"),
        "projects": workspace.get("projects"),
        "labels": [item.get("name") for item in workspace.get("labels") or []],
        "cycles": [item.get("name") for item in workspace.get("cycles") or []],
        "statuses": [item.get("name") for item in workspace.get("statuses") or []],
        "needs_llm": [],
    }


def issues(payload: dict[str, Any]) -> dict[str, Any]:
    requested = get_value(payload, "class", "course")
    team = get_value(payload, "team")
    if requested:
        course = resolve_class(str(requested))
        workspace = linear_workspace()
        found = issues_for_course(
            course,
            str(team) if team else (workspace.get("team") or {}).get("id"),
            workspace.get("projects") or [],
        )
        return {"issues": found, "count": len(found), "needs_llm": []}
    args: list[str] = []
    if team:
        args.extend(["--team", str(team)])
    query = get_value(payload, "query")
    if query:
        args.extend(["--query", str(query)])
    from fast_common import paginate_linear

    found = paginate_linear("list_issues", args, "issues")
    return {"issues": found, "count": len(found), "needs_llm": []}


def save(payload: dict[str, Any]) -> dict[str, Any]:
    apply_changes = True
    if get_value(payload, "apply") is not None:
        apply_changes = truthy(get_value(payload, "apply"))
    requested = get_value(payload, "class", "course")
    if requested or get_value(payload, "issues"):
        result = save_course_issues(payload, apply=apply_changes)
        remaining = []
        for item in result.get("pending") or []:
            remaining.append(
                needs_llm(
                    "pending_create",
                    title=item.get("title"),
                    missing=item.get("missing"),
                )
            )
        result["needs_llm"] = remaining
        return result
    if not apply_changes:
        return {
            "apply": False,
            "status": "pending_create",
            "title": get_value(payload, "title"),
            "needs_llm": [
                needs_llm(
                    "pending_create",
                    action="run",
                    command="python tools/run_tool/run_tool.py fast_linear save --apply",
                    message="Pass --apply to create.",
                    title=get_value(payload, "title"),
                )
            ],
        }
    args = ["save_issue", *payload_flags(payload, "class", "course", "apply", "issues")]
    created = run_json_tool("linear", args)
    return {"apply": True, "status": "created", "issue": created, "needs_llm": []}


def comment(payload: dict[str, Any]) -> dict[str, Any]:
    return run_json_tool("linear", ["save_comment", *payload_flags(payload)])


def run(payload: dict[str, Any]) -> dict[str, Any]:
    snapshot = preflight(payload)
    if get_value(payload, "class", "course", "query"):
        snapshot["issues"] = issues(payload)
    return snapshot


def main() -> int:
    return run_cli(
        "fast_linear",
        {
            "run": run,
            "preflight": preflight,
            "issues": issues,
            "save": save,
            "comment": comment,
        },
    )


if __name__ == "__main__":
    raise SystemExit(main())
