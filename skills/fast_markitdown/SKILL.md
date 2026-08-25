---
name: fast_markitdown
description: Converts a trusted local PDF to ignored Markdown.
---

# Fast MarkItDown

Spoken `MATH 212` becomes `--class "MATH 212"`. Never open `MATH 212.md`. The class index is `courses/MATH-212-*-Fall-2026/MATH-212.md`.

## Discover

```text
python tools/run_tool/run_tool.py fast_markitdown commands
```

## Run

```text
python tools/run_tool/run_tool.py fast_markitdown --input "attachments/MATH-245 Syllabus Fall 2026.pdf" --class "MATH 245"
```

Read JSON from stdout. For each `needs_llm` item: if `action` is `run`, run `command`; if `ask_user`, ask. Never copy due, status, priority, or estimate into frontmatter.

## Success

- Runner JSON on stdout (no scratch file)
- needs_llm empty or reported
- No due / status / priority / estimate in frontmatter
- Links use real hyphenated class-index paths
