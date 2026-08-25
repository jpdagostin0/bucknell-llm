---
name: fast_get_homework_pages
description: Extracts the smallest cited textbook page range. Never guess a page offset.
---

# Fast Get Homework Pages

Spoken `MATH 212` becomes `--class "MATH 212"`. Never open `MATH 212.md`. The class index is `courses/MATH-212-*-Fall-2026/MATH-212.md`.

## Discover

```text
python tools/run_tool/run_tool.py fast_get_homework_pages commands
```

## Run

```text
python tools/run_tool/run_tool.py fast_get_homework_pages --class "MATH 212" --homework "attachments/MATH-212 Homework-01 Section-1-1.pdf"
```

Read JSON from stdout. For each `needs_llm` item: if `action` is `run`, run `command`; if `ask_user`, ask. Never copy due, status, priority, or estimate into frontmatter.

## Success

- Runner JSON on stdout (no scratch file)
- needs_llm empty or reported
- No due / status / priority / estimate in frontmatter
- Links use real hyphenated class-index paths
