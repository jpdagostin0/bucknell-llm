---
name: fast_import_syllabus
description: Proposes Linear issues from dated Syllabus.md lines. Never invent due dates.
---

# Fast Import Syllabus

Spoken `MATH 212` becomes `--class "MATH 212"`. Never open `MATH 212.md`. The class index is `courses/MATH-212-*-Fall-2026/MATH-212.md`.

## Discover

```text
python tools/run_tool/run_tool.py fast_import_syllabus commands
```

## Run

```text
python tools/run_tool/run_tool.py fast_import_syllabus --class "MATH 212"
```

Read JSON from stdout. For each `needs_llm` item: if `action` is `run`, run `command`; if `ask_user`, ask. Never copy due, status, priority, or estimate into frontmatter.

`--apply` creates issues when project, due date, and kind exist. Handle `missing_due` and `missing_kind` with `ask_user`.

## Success

- Runner JSON on stdout (no scratch file)
- needs_llm empty or reported
- No due / status / priority / estimate in frontmatter
- Links use real hyphenated class-index paths
