from __future__ import annotations

from typing import Any

from fast_common import get_value, payload_flags, resolve_class, run_cli, run_json_tool
from linear_apply import issues_for_course, linear_workspace, project_id_for


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
    requested = get_value(payload, "class", "course")
    args = ["save_issue", *payload_flags(payload, "class", "course")]
    if requested and not get_value(payload, "projectId", "project_id", "project"):
        workspace = linear_workspace()
        course = resolve_class(str(requested))
        project = project_id_for(course, workspace.get("projects") or [])
        if project:
            args.extend(["--projectId", project])
        team = workspace.get("team") or {}
        if team.get("id") and not get_value(payload, "team"):
            args.extend(["--team", team["id"]])
    return run_json_tool("linear", args)


def comment(payload: dict[str, Any]) -> dict[str, Any]:
    return run_json_tool("linear", ["save_comment", *payload_flags(payload)])


def run(payload: dict[str, Any]) -> dict[str, Any]:
    snapshot = preflight(payload)
    if get_value(payload, "class", "course", "query"):
        snapshot["issues"] = issues(payload)
    return snapshot


def main() -> int:
    return run_cli(
        "fast-linear",
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
