from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from fast_common import (
    TERM_START,
    attachment_wikilink,
    class_wikilink,
    lecture_dates_for_week,
    load_frontmatter,
    rel,
    strip_frontmatter_keys,
    vault_root,
    week_wikilink,
)

SCAFFOLD_MARKERS = (
    "Add the instructor",
    "awaiting the instructor-provided syllabus",
    "catalog is reference material",
    "Add an objective",
    "Add the stable grading",
)


def is_scaffold(text: str) -> bool:
    return any(marker.lower() in text.lower() for marker in SCAFFOLD_MARKERS)


def split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    if not text.startswith("---"):
        return {}, text
    lines = text.splitlines()
    try:
        closing = lines.index("---", 1)
    except ValueError:
        return {}, text
    metadata = yaml.safe_load("\n".join(lines[1:closing])) or {}
    body = "\n".join(lines[closing + 1 :]).lstrip("\n")
    return metadata if isinstance(metadata, dict) else {}, body


def dump_note(metadata: dict[str, Any], body: str) -> str:
    dumped = yaml.safe_dump(metadata, sort_keys=False, allow_unicode=True).strip()
    return f"---\n{dumped}\n---\n\n{body.lstrip()}\n"


def replace_section(text: str, heading: str, body: str) -> str:
    pattern = re.compile(
        rf"(^## {re.escape(heading)}\n)(.*?)(?=^## |\Z)",
        re.M | re.S,
    )
    replacement = f"## {heading}\n\n{body.strip()}\n\n"
    if pattern.search(text):
        return pattern.sub(replacement, text, count=1)
    return text.rstrip() + "\n\n" + replacement


def extract_markdown_section(text: str, heading: str) -> str:
    pattern = re.compile(
        rf"^#+ +{re.escape(heading)}\s*$",
        re.I | re.M,
    )
    match = pattern.search(text)
    if not match:
        return ""
    rest = text[match.end() :]
    next_heading = re.search(r"^#+ ", rest, re.M)
    block = rest[: next_heading.start()] if next_heading else rest
    return block.strip()


def extract_topics(text: str, limit: int = 8) -> list[str]:
    topics: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        heading = re.match(r"^#{1,3} +(.+)$", stripped)
        bullet = re.match(r"^[-*] +(.+)$", stripped)
        candidate = ""
        if heading:
            candidate = heading.group(1).strip()
        elif bullet:
            candidate = bullet.group(1).strip()
        candidate = re.sub(r"\[\[.*?\]\]", "", candidate).strip(" :-")
        if (
            candidate
            and 3 < len(candidate) < 120
            and candidate.lower() not in {"topics", "materials", "notes"}
            and candidate not in topics
        ):
            topics.append(candidate)
        if len(topics) >= limit:
            break
    return topics


def extract_syllabus_facts(text: str) -> dict[str, Any]:
    instructor = None
    email = None
    office = None
    hours = None
    for match in re.finditer(r"^\s*(?:instructor|professor)\s*[:\-]\s*(.+)$", text, re.I | re.M):
        instructor = match.group(1).strip()
        break
    for match in re.finditer(r"\b([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})\b", text):
        email = match.group(1)
        break
    for match in re.finditer(r"^\s*office(?: hours)?\s*[:\-]\s*(.+)$", text, re.I | re.M):
        value = match.group(1).strip()
        if "hour" in match.group(0).lower():
            hours = value
        else:
            office = value
    description = extract_markdown_section(text, "Course Description") or extract_markdown_section(
        text, "Description"
    )
    objectives = extract_markdown_section(text, "Learning Objectives") or extract_markdown_section(
        text, "Objectives"
    )
    grading = extract_markdown_section(text, "Grading Breakdown") or extract_markdown_section(
        text, "Grading"
    )
    units = extract_markdown_section(text, "Units") or extract_markdown_section(text, "Schedule")
    return {
        "instructor": instructor,
        "email": email,
        "office": office,
        "office_hours": hours,
        "description": description,
        "objectives": objectives,
        "grading": grading,
        "units": units,
    }


def apply_syllabus(
    course: dict[str, Any],
    converted_text: str,
    source_pdf: Path | None,
    *,
    apply: bool,
) -> dict[str, Any]:
    path = course["syllabus"]
    current = path.read_text(encoding="utf-8") if path.exists() else ""
    facts = extract_syllabus_facts(converted_text)
    planned = {
        "path": rel(path),
        "scaffold": is_scaffold(current),
        "facts": {key: bool(value) for key, value in facts.items()},
        "updated": False,
    }
    if not apply:
        return planned
    metadata, body = split_frontmatter(current) if current else (
        {
            "type": "syllabus",
            "class": class_wikilink(course),
            "source": "https://example.edu/course/syllabus",
        },
        current,
    )
    if source_pdf and source_pdf.exists():
        metadata["source"] = f"[[{rel(source_pdf)}]]"
    if not planned["scaffold"]:
        if current != dump_note(metadata, body if body else current.split("---", 2)[-1]):
            path.write_text(dump_note(metadata, body), encoding="utf-8")
            planned["updated"] = True
        return planned

    title = f"{course['hyphen']} Syllabus"
    source_line = ""
    if source_pdf and source_pdf.exists():
        source_line = (
            f"> [!source]\n"
            f"> Retained instructor syllabus: {attachment_wikilink(source_pdf)}\n\n"
        )
    description = facts["description"] or "Add the instructor's course description."
    objectives = facts["objectives"] or "- Add an objective."
    grading = facts["grading"] or "Add the stable grading categories and weights from the instructor syllabus."
    units = facts["units"] or "Add instructor-defined unit headings and retained course material."
    policies = ["Exam dates and assignment deadlines are tracked in Linear rather than duplicated here."]
    if facts["office_hours"]:
        policies.append(f"- **Office hours:** {facts['office_hours']}")
    if facts["email"]:
        policies.append(f"- **Email:** {facts['email']}")
    body = (
        f"# {title}\n\n"
        f"{source_line}"
        f"## Course Description\n\n{description}\n\n"
        f"## Learning Objectives\n\n{objectives}\n\n"
        f"## Grading Breakdown\n\n{grading}\n\n"
        f"## Units\n\n{units}\n\n"
        f"## Policies and Resources\n\n" + "\n".join(policies) + "\n"
    )
    metadata = {
        "type": "syllabus",
        "class": class_wikilink(course),
        "source": metadata.get("source") or "https://example.edu/course/syllabus",
    }
    if source_pdf and source_pdf.exists():
        metadata["source"] = f"[[{rel(source_pdf)}]]"
    path.write_text(dump_note(metadata, body), encoding="utf-8")
    planned["updated"] = True
    return planned


def apply_class_index_links(
    course: dict[str, Any],
    facts: dict[str, Any] | None = None,
    *,
    apply: bool,
) -> dict[str, Any]:
    path = course["index"]
    text = path.read_text(encoding="utf-8")
    metadata, body = split_frontmatter(text)
    facts = facts or {}
    changed = False
    if facts.get("instructor") and not metadata.get("instructor"):
        metadata["instructor"] = facts["instructor"]
        changed = True
    info_lines = []
    if facts.get("instructor") and "**Instructor:**" not in body:
        info_lines.append(f"- **Instructor:** {facts['instructor']}")
    if facts.get("office") and "**Office:**" not in body:
        info_lines.append(f"- **Office:** {facts['office']}")
    if facts.get("office_hours") and "**Office hours:**" not in body:
        info_lines.append(f"- **Office hours:** {facts['office_hours']}")
    if facts.get("email") and "**Email:**" not in body:
        info_lines.append(f"- **Email:** {facts['email']}")
    if info_lines and "## Course Information" in body:
        body = body.replace(
            "## Course Information\n",
            "## Course Information\n\n" + "\n".join(info_lines) + "\n",
            1,
        )
        changed = True

    textbooks = sorted(
        path.parent.joinpath("textbooks").glob("*.pdf")
        if path.parent.joinpath("textbooks").is_dir()
        else []
    )
    weeks = sorted((path.parent / "notes").glob("Week-*.md"))
    work = sorted((path.parent / "work").glob("*.md"))
    textbook_body = (
        "\n".join(f"- {attachment_wikilink(item)}" for item in textbooks)
        if textbooks
        else "No textbooks have been retained yet."
    )
    notes_body = (
        "\n".join(
            f"- {week_wikilink(course, int(item.stem.split('-')[1]))}"
            for item in weeks
        )
        if weeks
        else "No weekly notes have been created yet."
    )
    work_body = (
        "\n".join(
            f"- [[{rel(item).removesuffix('.md')}|{item.stem}]]" for item in work
        )
        if work
        else "No work notes have been created yet."
    )
    if textbooks:
        if not all(rel(item) in body for item in textbooks):
            if "## Textbooks" in body:
                new_body = replace_section(body, "Textbooks", textbook_body)
            else:
                new_body = body.replace(
                    "## Notes", f"## Textbooks\n\n{textbook_body}\n\n## Notes", 1
                )
            if new_body != body:
                body = new_body
                changed = True
    if weeks and not all(
        f"notes/Week-{item.stem.split('-')[1]}" in body for item in weeks
    ):
        new_body = replace_section(body, "Notes", notes_body)
        if new_body != body:
            body = new_body
            changed = True
    elif not weeks and "## Notes" not in body:
        body = replace_section(body, "Notes", notes_body)
        changed = True
    if work and not all(rel(item).removesuffix(".md") in body for item in work):
        new_body = replace_section(body, "Work", work_body)
        if new_body != body:
            body = new_body
            changed = True
    if apply and changed:
        path.write_text(dump_note(metadata, body), encoding="utf-8")
    return {"path": rel(path), "updated": bool(apply and changed), "planned": changed}


def material_label(filename: str) -> str:
    stem = Path(filename).stem
    stem = re.sub(r"^[A-Z]{2,4}-[0-9]{3}\s+", "", stem)
    return stem.replace("--", " — ")


def upsert_week_note(
    course: dict[str, Any],
    week: int,
    materials: list[dict[str, Any]],
    *,
    apply: bool,
) -> dict[str, Any]:
    notes_dir = course["folder"] / "notes"
    path = notes_dir / f"Week-{week:02d}.md"
    meetings = ""
    if course.get("index"):
        meetings = str(load_frontmatter(course["index"]).get("meetings") or "")
    dates = lecture_dates_for_week(week, meetings)
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    metadata, body = split_frontmatter(existing) if existing else ({}, "")
    metadata["type"] = "week"
    metadata["class"] = class_wikilink(course)
    metadata["week"] = week
    metadata["lectures"] = dates or metadata.get("lectures") or [TERM_START.isoformat()]
    if not metadata.get("unit"):
        metadata["unit"] = f"Week {week:02d}"
    if not body:
        heading = f"# {course['hyphen']} — Week {week:02d}\n\n"
        date_blocks = []
        for value in metadata["lectures"]:
            date_blocks.append(
                f"## {value}\n\n### Topics\n\n- Add a topic.\n\n### Materials\n\n"
            )
        body = heading + "\n".join(date_blocks) + "\n## Weekly Synthesis\n\nSummarize the week's key ideas and unresolved questions.\n"

    created = not bool(existing)
    original_body = body
    for material in materials:
        link = material["link"]
        target = str(link).split("|", 1)[0].strip("[]")
        if link in body or target in body:
            continue
        date = material.get("date") or (metadata["lectures"][-1] if material.get("kind") == "homework" else metadata["lectures"][0])
        marker = f"## {date}"
        if marker not in body:
            body += f"\n{marker}\n\n### Topics\n\n- Add a topic.\n\n### Materials\n\n"
        materials_heading = body.find("### Materials", body.find(marker))
        next_heading = body.find("\n## ", materials_heading + 1)
        insert_at = next_heading if next_heading != -1 else len(body)
        insertion = f"- {link}\n"
        body = body[:insert_at].rstrip() + "\n" + insertion + body[insert_at:]
        topics = material.get("topics") or []
        if topics and "Add a topic." in body:
            topic_block = "\n".join(f"- {topic}" for topic in topics)
            # Replace only the placeholder under this date if still templated.
            date_start = body.find(marker)
            date_topics = body.find("### Topics", date_start)
            if date_topics != -1 and "Add a topic." in body[date_topics : date_topics + 80]:
                body = (
                    body[:date_topics]
                    + "### Topics\n\n"
                    + topic_block
                    + "\n\n"
                    + body[body.find("### Materials", date_topics) :]
                )
    synthesis_topics = [item for material in materials for item in material.get("topics") or []]
    if (
        apply
        and synthesis_topics
        and "Summarize the week's key ideas" in body
    ):
        summary = "; ".join(synthesis_topics[:6])
        body = body.replace(
            "Summarize the week's key ideas and unresolved questions.",
            f"This week covers {summary}.",
        )
    planned = created or body != original_body
    if not created:
        closing = existing.find("---", 3)
        original_front = existing[: closing + 3] if closing != -1 else ""
        updated = original_front + "\n\n" + body.lstrip()
        if not updated.endswith("\n"):
            updated += "\n"
    else:
        updated = dump_note(metadata, body)
    if apply and planned:
        notes_dir.mkdir(parents=True, exist_ok=True)
        path.write_text(updated, encoding="utf-8")
    return {"path": rel(path), "week": week, "updated": bool(apply and planned), "planned": planned}


def scaffold_work_note(
    course: dict[str, Any],
    issue: dict[str, Any],
    *,
    kind: str,
    week: int | None,
    prompt: str,
    apply: bool,
) -> dict[str, Any] | None:
    if not issue.get("identifier"):
        return None
    slug = re.sub(r"[^A-Za-z0-9 ]+", "", issue.get("title") or "Work")
    slug = re.sub(r"\s+", " ", slug).strip()
    if slug.upper().startswith(course["code"]):
        filename = f"{course['hyphen']} {slug[len(course['code']):].strip()}.md"
    else:
        filename = f"{course['hyphen']} {slug}.md"
    filename = filename.replace(":", " ")
    path = course["folder"] / "work" / filename
    if path.exists():
        return {"path": rel(path), "updated": False, "planned": False}
    metadata: dict[str, Any] = {
        "type": "assignment",
        "linear": issue["identifier"],
        "class": class_wikilink(course),
        "kind": kind,
    }
    if issue.get("url"):
        metadata["linear_url"] = issue["url"]
    if week:
        metadata["worked"] = [f"[[courses/{course['folder'].name}/notes/Week-{week:02d}]]"]
    body = (
        f"# {issue.get('title')}\n\n"
        f"## Prompt\n\n{prompt.strip() or 'Retain the assignment prompt or a stable source link.'}\n\n"
        f"## Working Notes\n\nRecord reasoning, derivations, drafts, and decisions worth keeping.\n\n"
        f"## References\n\n- Linear: {issue.get('url') or issue['identifier']}\n"
    )
    if apply:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(dump_note(metadata, body), encoding="utf-8")
    return {"path": rel(path), "updated": apply, "planned": True}


def repair_class_index_links() -> list[str]:
    from fast_common import discover_classes

    updated: list[str] = []
    for course in discover_classes():
        result = apply_class_index_links(course, apply=True)
        if result["updated"]:
            updated.append(result["path"])
    return updated


def repair_forbidden_frontmatter() -> list[str]:
    updated: list[str] = []
    root = vault_root()
    for path in root.rglob("*.md"):
        relative = path.relative_to(root)
        if relative.parts and relative.parts[0] in {"skills", "tools"}:
            continue
        metadata = load_frontmatter(path)
        forbidden = [key for key in ("status", "due", "priority", "estimate") if key in metadata]
        if forbidden and strip_frontmatter_keys(path, forbidden):
            updated.append(rel(path))
    return updated


def qualify_unique_wikilinks() -> list[str]:
    root = vault_root()
    by_stem: dict[str, list[Path]] = {}
    for path in root.rglob("*"):
        if path.is_file() and path.suffix in {".md", ".pdf"}:
            by_stem.setdefault(path.stem, []).append(path)
    updated: list[str] = []
    pattern = re.compile(r"\[\[([^\]|#/]+)(?:\|([^\]]+))?\]\]")
    for path in root.rglob("*.md"):
        relative = path.relative_to(root)
        if relative.parts and relative.parts[0] in {"skills", "tools", ".obsidian"}:
            continue
        text = path.read_text(encoding="utf-8")
        changed = text

        def replacer(match: re.Match[str]) -> str:
            target = match.group(1)
            label = match.group(2)
            matches = by_stem.get(target, [])
            if len(matches) != 1:
                return match.group(0)
            qualified = rel(matches[0]).removesuffix(".md")
            display = label or target
            return f"[[{qualified}|{display}]]"

        changed = pattern.sub(replacer, text)
        if changed != text:
            path.write_text(changed, encoding="utf-8")
            updated.append(rel(path))
    return updated


apply_class_index_links = apply_class_index_links
scaffold_work_note = scaffold_work_note
