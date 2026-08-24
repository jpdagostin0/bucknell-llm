from __future__ import annotations

import datetime as dt
import re
from pathlib import Path
from typing import Any

from fast_common import (
    FRONTMATTER,
    MONTHS,
    TERM_START,
    ToolError,
    discover_classes,
    get_value,
    load_frontmatter,
    needs_llm,
    parse_due_date,
    rel,
    resolve_classes,
    run_cli,
    truthy,
    unwrap_wikilink,
    vault_root,
    zero_pad_item_name,
)
from linear_apply import create_or_match_issue, issues_for_course, linear_workspace

LINEAR_DEADLINES = re.compile(
    r"(?:exam dates|assignment deadlines|deadlines?|due dates?).{0,120}\blinear\b"
    r"|\blinear\b.{0,120}(?:deadlines?|due dates?)"
    r"|tracked in linear"
    r"|deadlines live in linear",
    re.I,
)
KIND_EXTRACT = (
    (
        "exam",
        re.compile(
            r"\b(?:exams?|midterms?|final\s+exams?|finals)\b"
            r"|(?:^|\b)final(?:\s+exam)?\s*[:—-]",
            re.I,
        ),
    ),
    ("quiz", re.compile(r"\bquizzes\b|\bquiz\b", re.I)),
    ("lab", re.compile(r"\blabs?(?:\s+reports?)?\b|\blaboratory\b", re.I)),
    ("reading", re.compile(r"\breadings?\b", re.I)),
    ("pset", re.compile(r"\b(?:homeworks?|problem\s*sets?|psets?)\b", re.I)),
)
GRADING_WEIGHT = re.compile(r"\d+\s*%")
TENTATIVE = re.compile(r"\btentative\b", re.I)
ISO_DATE = re.compile(r"\b20\d{2}-\d{2}-\d{2}\b")
NAMED_DATE = re.compile(
    r"\b(?:" + "|".join(re.escape(name) for name in MONTHS) + r")\s+\d{1,2}"
    r"(?:st|nd|rd|th)?(?:,\s*\d{4})?\b",
    re.I,
)
NUMERIC_DATE = re.compile(r"\b\d{1,2}/\d{1,2}(?:/\d{2,4})?\b")
DUE_WORD = re.compile(r"\bdue(?!\s+to)(?:\s+dates?)?\b", re.I)
LEADING_NUMBERED = re.compile(
    r"^\s*(?:[-*+]|\d+\.)?\s*(?:\*\*)?(?:Homework|Assignment|Quiz|Lab|"
    r"Exam|Midterm|Final(?:\s+Exam)?|Problem\s*Set|Pset|Reading)"
    r"\s*[- ]?\d+",
    re.I,
)
TEXT_SUFFIXES = {".md", ".txt"}
BINARY_SUFFIXES = {".pdf", ".doc", ".docx", ".ppt", ".pptx"}


def week_from_due(due: str) -> int:
    date = dt.date.fromisoformat(due)
    week = ((date - TERM_START).days // 7) + 1
    return max(1, min(16, week))


def infer_kind(line: str) -> str | None:
    for kind, pattern in KIND_EXTRACT:
        if pattern.search(line):
            return kind
    return None


def strip_frontmatter(text: str) -> str:
    match = FRONTMATTER.match(text)
    return text[match.end() :] if match else text


def has_linear_deadlines_note(text: str) -> bool:
    return bool(LINEAR_DEADLINES.search(text))


def _clean_name(line: str, kind: str, *, tentative: bool) -> str:
    text = re.sub(r"^\s*[-*+]\s+", "", line)
    text = re.sub(r"^\s*\d+\.\s+", "", text)
    text = re.sub(r"\|", " ", text)
    text = re.sub(r"\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|[^\]]+)?\]\]", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"[*_`#>]+", " ", text)
    text = ISO_DATE.sub(" ", text)
    text = NAMED_DATE.sub(" ", text)
    text = NUMERIC_DATE.sub(" ", text)
    text = re.sub(r"\b(?:due(?:\s+date)?)\s*:?\s*", " ", text, flags=re.I)
    text = re.sub(r"\btentative\b", " ", text, flags=re.I)
    text = re.sub(r"\s+", " ", text).strip(" -:;,.()")
    text = zero_pad_item_name(text)
    if not text or len(text) < 3:
        text = {
            "pset": "Homework",
            "exam": "Exam",
            "lab": "Lab",
            "quiz": "Quiz",
            "reading": "Reading",
        }.get(kind, kind)
    if tentative and "(tentative)" not in text.lower():
        text = f"(tentative) {text}"
    return text


def extract_dated_obligations(text: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return (proposed, needs_llm) from syllabus markdown. Does not invent dates."""
    proposed: list[dict[str, Any]] = []
    remaining: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    body = strip_frontmatter(text)
    for raw in body.splitlines():
        line = raw.strip()
        if not line or line.startswith(">"):
            continue
        if LINEAR_DEADLINES.search(line):
            continue
        due = parse_due_date(line)
        kind = infer_kind(line)
        tentative = bool(TENTATIVE.search(line))
        if not due:
            if GRADING_WEIGHT.search(line):
                continue
            if kind and LEADING_NUMBERED.search(line):
                remaining.append(
                    needs_llm(
                        "missing_due",
                        line=line,
                        obligation_kind=kind,
                        message="Dated obligation is missing a parseable due date.",
                    )
                )
            continue
        if not kind:
            if DUE_WORD.search(line):
                remaining.append(
                    needs_llm(
                        "missing_kind",
                        line=line,
                        due_date=due,
                        message="Dated line has no Kind mapping.",
                    )
                )
            continue
        name = _clean_name(line, kind, tentative=tentative)
        key = (name.lower(), kind, due)
        if key in seen:
            continue
        seen.add(key)
        proposed.append(
            {
                "name": name,
                "kind": kind,
                "due_date": due,
                "week": week_from_due(due),
                "tentative": tentative,
            }
        )
    return proposed, remaining


def _source_path(course: dict[str, Any]) -> Path | None:
    syllabus = course.get("syllabus")
    if not syllabus or not Path(syllabus).is_file():
        return None
    metadata = load_frontmatter(Path(syllabus))
    raw = unwrap_wikilink(metadata.get("source"))
    if not raw or re.match(r"https?://", raw, re.I):
        return None
    path = Path(raw)
    if not path.is_absolute():
        path = vault_root() / raw
    return path if path.is_file() else None


def extra_attachment_text(course: dict[str, Any]) -> tuple[str | None, dict[str, Any] | None]:
    path = _source_path(course)
    if path is None:
        return None, None
    suffix = path.suffix.lower()
    if suffix in TEXT_SUFFIXES:
        return path.read_text(encoding="utf-8", errors="replace"), None
    converted = vault_root() / "tools/markitdown/output" / f"{path.stem}.md"
    if converted.is_file():
        return converted.read_text(encoding="utf-8", errors="replace"), None
    if suffix in BINARY_SUFFIXES:
        return None, needs_llm(
            "attachment_text_unavailable",
            path=rel(path),
            message="Retained syllabus attachment has no already-extracted text.",
        )
    return None, None


def load_syllabus_text(course: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    remaining: list[dict[str, Any]] = []
    syllabus = Path(course["syllabus"])
    if not syllabus.is_file():
        remaining.append(
            needs_llm(
                "missing_syllabus",
                course=course["code"],
                message="Course folder has no Syllabus.md.",
            )
        )
        return "", remaining
    parts = [syllabus.read_text(encoding="utf-8")]
    extra, extra_need = extra_attachment_text(course)
    if extra:
        parts.append(extra)
    elif extra_need:
        remaining.append(extra_need)
    return "\n".join(parts), remaining


def _issue_record(course: dict[str, Any], item: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    issue = result.get("issue") or {}
    return {
        "class": course["code"],
        "title": result.get("title") or item.get("name"),
        "kind": item.get("kind"),
        "due_date": item.get("due_date"),
        "week": item.get("week"),
        "linear": issue.get("identifier"),
        "url": issue.get("url"),
        "status": result.get("status"),
    }


def process_course(
    course: dict[str, Any],
    *,
    apply: bool,
    workspace: dict[str, Any] | None,
) -> dict[str, Any]:
    text, remaining = load_syllabus_text(course)
    proposed, extract_needs = extract_dated_obligations(text)
    remaining.extend(extract_needs)
    if not proposed:
        remaining.append(
            needs_llm(
                "no_dated_obligations",
                course=course["code"],
                linear_note=has_linear_deadlines_note(text),
                message="Syllabus has no dated obligations to import.",
            )
        )
        return {
            "class": course["code"],
            "proposed": [],
            "created": [],
            "matched": [],
            "needs_llm": remaining,
        }

    created: list[dict[str, Any]] = []
    matched: list[dict[str, Any]] = []
    pending: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []
    if workspace is None:
        remaining.append(
            needs_llm(
                "linear_unavailable",
                course=course["code"],
                message="Linear workspace was not loaded; issues were not matched or created.",
            )
        )
    else:
        team_id = (workspace.get("team") or {}).get("id")
        issues = issues_for_course(course, team_id, workspace.get("projects") or [])

    syllabus_rel = rel(Path(course["syllabus"])) if Path(course["syllabus"]).exists() else None
    for item in proposed:
        payload = {
            "name": item["name"],
            "kind": item["kind"],
            "due_date": item["due_date"],
            "week": item["week"],
            "matched": syllabus_rel,
        }
        record = {
            "class": course["code"],
            "name": item["name"],
            "kind": item["kind"],
            "due_date": item["due_date"],
            "week": item["week"],
            "tentative": item.get("tentative", False),
            "source": syllabus_rel,
        }
        pending.append(record)
        if workspace is None:
            continue
        result = create_or_match_issue(
            course, payload, workspace, issues, apply=apply
        )
        status = result.get("status")
        if status == "matched":
            matched.append(_issue_record(course, item, result))
            issue = result.get("issue")
            if issue:
                issues.append(issue)
        elif status == "created":
            created.append(_issue_record(course, item, result))
            issue = result.get("issue")
            if issue:
                issues.append(issue)
        else:
            missing = result.get("missing") or []
            if missing:
                remaining.append(
                    needs_llm(
                        "pending_create",
                        course=course["code"],
                        title=result.get("title"),
                        missing=missing,
                    )
                )
    return {
        "class": course["code"],
        "proposed": pending,
        "created": created,
        "matched": matched,
        "needs_llm": remaining,
    }


def run(payload: dict[str, Any]) -> dict[str, Any]:
    apply_changes = truthy(get_value(payload, "apply"))
    courses = resolve_classes(payload) or discover_classes()
    proposed: list[dict[str, Any]] = []
    created: list[dict[str, Any]] = []
    matched: list[dict[str, Any]] = []
    remaining: list[dict[str, Any]] = []
    workspace: dict[str, Any] | None = None
    try:
        workspace = linear_workspace()
    except ToolError as error:
        remaining.append(
            needs_llm(
                "linear_unavailable",
                message=error.message,
            )
        )
        if apply_changes:
            raise

    for course in courses:
        result = process_course(course, apply=apply_changes, workspace=workspace)
        proposed.extend(result["proposed"])
        created.extend(result["created"])
        matched.extend(result["matched"])
        remaining.extend(result["needs_llm"])

    return {
        "apply": apply_changes,
        "proposed": proposed,
        "created": created,
        "matched": matched,
        "needs_llm": remaining,
    }


def main() -> int:
    return run_cli("fast-import-syllabus", {"run": run})


if __name__ == "__main__":
    raise SystemExit(main())
