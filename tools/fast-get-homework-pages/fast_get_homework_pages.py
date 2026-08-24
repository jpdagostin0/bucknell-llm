from __future__ import annotations

from pathlib import Path
from typing import Any

from fast_common import (
    ToolError,
    convert_pdf,
    extract_page_citations,
    extract_printed_pages,
    extract_section_citations,
    find_section_labels,
    get_value,
    printed_spec,
    rel,
    resolve_class,
    run_cli,
    vault_root,
)


def choose_textbook(course: dict[str, Any], requested: str | None) -> Path:
    textbooks = course["textbooks"]
    if requested:
        path = Path(requested)
        if not path.is_absolute():
            path = (vault_root() / path).resolve()
        if path.exists():
            return path
        lowered = requested.lower()
        matches = [item for item in textbooks if lowered in item.name.lower()]
        if len(matches) == 1:
            return matches[0]
        raise ToolError(f"Textbook not found: {requested}", "usage")
    if len(textbooks) == 1:
        return textbooks[0]
    if not textbooks:
        raise ToolError(f"{course['code']} has no course textbooks.", "usage")
    names = ", ".join(item.name for item in textbooks)
    raise ToolError(f"Pass --textbook to choose among: {names}", "usage")


def run(payload: dict[str, Any]) -> dict[str, Any]:
    course = resolve_class(str(get_value(payload, "class", "course", required=True)))
    textbook = choose_textbook(course, get_value(payload, "textbook"))
    homework_value = get_value(payload, "homework", "input", "source")
    requested_pages = get_value(payload, "printedPages", "printed_pages", "pages")
    citations: list[dict[str, int]] = []
    sections: list[str] = []
    converted = None
    if homework_value:
        homework = Path(str(homework_value))
        if not homework.is_absolute():
            homework = (vault_root() / homework).resolve()
        if homework.suffix.lower() == ".pdf":
            converted = convert_pdf(homework)
            citations = converted["page_citations"]
            sections = converted.get("section_citations") or []
        else:
            text = homework.read_text(encoding="utf-8", errors="replace")
            citations = extract_page_citations(text)
            sections = extract_section_citations(text)
    spec = str(requested_pages) if requested_pages else printed_spec(citations)
    if not spec and sections:
        labels: list[str] = []
        for section in sections:
            labels.extend(find_section_labels(textbook, section))
        unique = []
        for label in labels:
            if label not in unique:
                unique.append(label)
        if unique:
            spec = ",".join(unique)
    if not spec:
        return {
            "ok": False,
            "class": course["code"],
            "textbook": rel(textbook),
            "citations": citations,
            "sections": sections,
            "extracted": False,
            "error": {
                "code": "ambiguous_pages",
                "message": "No unique printed page range or section map. Pass --printed-pages.",
            },
            "needs_llm": [],
        }
    slug = get_value(payload, "outputName", "output_name") or (
        f"{course['hyphen']} pages {spec.replace(',', '_')}.pdf"
    )
    output = vault_root() / "tools/pypdf/output" / str(slug)
    if output.exists():
        extracted = {
            "textbook": rel(textbook),
            "printed_pages": spec,
            "output": rel(output),
            "exists": True,
        }
    else:
        extracted = extract_printed_pages(textbook, spec, output)
    verified = None
    try:
        preview = convert_pdf(output, f"{output.stem}.md")
        needles = sections or [str(item["start"]) for item in citations]
        missing = [
            needle
            for needle in needles
            if needle and needle not in (preview.get("text") or "")
        ]
        verified = {"ok": not missing, "missing": missing, "output": preview["output"]}
    except ToolError as error:
        verified = {"ok": False, "error": error.message}
    return {
        "class": course["code"],
        "textbook": rel(textbook),
        "citations": citations,
        "sections": sections,
        "printed_pages": spec,
        "extracted": extracted,
        "verified": verified,
        "converted": {key: value for key, value in (converted or {}).items() if key != "text"},
        "needs_llm": [],
    }


def main() -> int:
    return run_cli("fast-get-homework-pages", {"run": run})


if __name__ == "__main__":
    raise SystemExit(main())
