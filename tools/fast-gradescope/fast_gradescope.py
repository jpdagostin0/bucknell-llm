from __future__ import annotations

import json
import re
from typing import Any

from fast_common import (
    ToolError,
    get_value,
    hyphen_code,
    needs_llm,
    resolve_class,
    run_cli,
    run_json_tool,
    spaced_code,
)


def require_gradescope() -> dict[str, Any]:
    status = run_json_tool("gradescope", ["ping"])
    if not status.get("authorized"):
        raise ToolError(
            "Gradescope is not authorized. Update gradescope cookies in .env.yml.",
            "needs_auth",
        )
    return status


def _courses() -> dict[str, Any]:
    return run_json_tool("gradescope", ["get_courses"])


def course_blob(course: dict[str, Any]) -> str:
    return " ".join(
        str(course.get(key) or "")
        for key in ("name", "fullName", "semester", "year", "id")
    )


def matches_class(course: dict[str, Any], requested: str) -> bool:
    blob = re.sub(r"[^a-z0-9]", "", course_blob(course).lower())
    hyphen = hyphen_code(requested).lower().replace("-", "")
    spaced = re.sub(r"[^a-z0-9]", "", spaced_code(requested).lower())
    title = ""
    try:
        title = re.sub(r"[^a-z0-9]", "", str(resolve_class(requested).get("title") or "").lower())
    except ToolError:
        title = ""
    if hyphen and hyphen in blob:
        return True
    if spaced and spaced in blob:
        return True
    return bool(title and title in blob)


def flatten_courses(grouped: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for role in ("student", "instructor"):
        for course in grouped.get(role) or []:
            items.append(course)
    return items


def courses(payload: dict[str, Any]) -> dict[str, Any]:
    require_gradescope()
    grouped = _courses()
    requested = get_value(payload, "class", "course")
    items = flatten_courses(grouped)
    if requested:
        items = [course for course in items if matches_class(course, str(requested))]
    remaining = []
    if requested and not items:
        remaining.append(
            needs_llm(
                "gradescope_course_unmatched",
                requested=str(requested),
                message="No Gradescope course matched this class code. Confirm enrollment or the cookie account.",
            )
        )
    return {
        "class": requested,
        "courses": items,
        "studentCourseCount": len(grouped.get("student") or []),
        "instructorCourseCount": len(grouped.get("instructor") or []),
        "needs_llm": remaining,
    }


def assignments(payload: dict[str, Any]) -> dict[str, Any]:
    require_gradescope()
    course_id = get_value(payload, "courseId", "course_id", "id")
    requested = get_value(payload, "class", "course")
    selected = []
    if course_id:
        selected = [{"id": str(course_id)}]
    elif requested:
        selected = courses(payload).get("courses") or []
    else:
        selected = flatten_courses(_courses())
    results = []
    remaining = []
    for course in selected:
        data = run_json_tool(
            "gradescope",
            ["get_assignments", "--courseId", str(course.get("id"))],
        )
        results.append(
            {
                "courseId": course.get("id"),
                "name": course.get("name"),
                "fullName": course.get("fullName"),
                "assignments": data.get("assignments") or [],
            }
        )
    if requested and not selected:
        remaining.append(
            needs_llm(
                "gradescope_course_unmatched",
                requested=str(requested),
            )
        )
    remaining.append(
        needs_llm(
            "linear_import_review",
            message="Deadline-bearing Gradescope assignments stay in Linear. Do not copy due dates into vault frontmatter.",
        )
    )
    return {"courses": results, "needs_llm": remaining}


def upload(payload: dict[str, Any]) -> dict[str, Any]:
    require_gradescope()
    files = get_value(payload, "files", "file", required=True)
    args = [
        "upload_assignment",
        "--courseId",
        str(get_value(payload, "courseId", "course_id", required=True)),
        "--assignmentId",
        str(get_value(payload, "assignmentId", "assignment_id", required=True)),
    ]
    if isinstance(files, list):
        args.extend(["--files", json.dumps(files)])
    else:
        args.extend(["--files", str(files)])
    return run_json_tool("gradescope", args)


def run(payload: dict[str, Any]) -> dict[str, Any]:
    try:
        status = require_gradescope()
    except ToolError as error:
        return {
            "authorized": False,
            "needs_llm": [
                needs_llm(
                    "gradescope_auth",
                    message=error.message,
                )
            ],
        }
    snapshot = courses(payload)
    if get_value(payload, "class", "course", "courseId", "course_id"):
        snapshot["assignments"] = assignments(payload)
    snapshot["ping"] = {
        "authorized": status.get("authorized"),
        "cookieCount": status.get("cookieCount"),
        "cookieNames": status.get("cookieNames"),
    }
    return snapshot


def main() -> int:
    return run_cli(
        "fast-gradescope",
        {
            "run": run,
            "courses": courses,
            "assignments": assignments,
            "upload": upload,
        },
    )


if __name__ == "__main__":
    raise SystemExit(main())
