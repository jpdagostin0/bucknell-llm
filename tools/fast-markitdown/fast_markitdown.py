from __future__ import annotations

from pathlib import Path
from typing import Any

from fast_common import (
    ToolError,
    convert_pdf,
    get_value,
    resolve_class,
    run_cli,
    vault_root,
)


def allowed_source(path: Path, course: dict[str, Any] | None) -> None:
    resolved = path.resolve()
    allowed = [vault_root() / "attachments", vault_root() / "tools/moodle-dl/state"]
    if course is not None:
        allowed.append(course["folder"] / "textbooks")
        allowed.append(course["folder"])
    if not any(_is_relative_to(resolved, root) for root in allowed if root.exists()):
        raise ToolError(
            "MarkItDown input must be a trusted local attachment, textbook, or Moodle staging PDF.",
            "safety",
        )


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root.resolve())
        return True
    except ValueError:
        return False


def run(payload: dict[str, Any]) -> dict[str, Any]:
    source_value = get_value(payload, "input", "source", "pdf", required=True)
    source = Path(str(source_value))
    if not source.is_absolute():
        source = (vault_root() / source).resolve()
    else:
        source = source.resolve()
    if source.suffix.lower() != ".pdf":
        raise ToolError("Input must be a PDF.", "usage")
    if not source.exists():
        raise ToolError(f"Missing PDF: {source}", "usage")
    course = None
    requested = get_value(payload, "class", "course")
    if requested:
        course = resolve_class(str(requested))
    allowed_source(source, course)
    output_name = get_value(payload, "outputName", "output_name")
    converted = convert_pdf(source, output_name)
    remaining = [
        {
            "kind": "note_rewrite",
            "output": converted["output"],
            "message": "Rewrite useful facts into the typed syllabus, week, or work note. Do not copy converter output verbatim.",
        }
    ]
    if converted["due_hints"]:
        remaining.append(
            {
                "kind": "linear_import_review",
                "output": converted["output"],
                "due_hints": converted["due_hints"],
            }
        )
    return {**converted, "needs_llm": remaining}


def main() -> int:
    return run_cli("fast-markitdown", {"run": run})


if __name__ == "__main__":
    raise SystemExit(main())
