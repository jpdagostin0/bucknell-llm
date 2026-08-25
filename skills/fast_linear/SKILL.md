---
name: fast_linear
description: Queries Linear and creates or updates issues. Never copy Linear-owned fields into vault frontmatter.
---

# Fast Linear

Spoken `MATH 212` becomes `--class "MATH 212"`. Never open `MATH 212.md`. The class index is `courses/MATH-212-*-Fall-2026/MATH-212.md`.

## Discover

```text
python tools/run_tool/run_tool.py fast_linear commands
```

## Run

```text
python tools/run_tool/run_tool.py fast_linear save --class "MATH 212" --title "MATH 212 — Homework 02" --dueDate 2026-09-04 --kind pset
```

Read JSON from stdout. For each `needs_llm` item: if `action` is `run`, run `command`; if `ask_user`, ask. Never copy due, status, priority, or estimate into frontmatter.

## Success

- Runner JSON on stdout (no scratch file)
- needs_llm empty or reported
- No due / status / priority / estimate in frontmatter
- Links use real hyphenated class-index paths
