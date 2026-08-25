---
name: read_file_lines
description: Read a local text file by 1-based line numbers. Never read .env.yml.
---

# Read File Lines

Spoken `MATH 212` becomes `--class "MATH 212"`. Never open `MATH 212.md`. The class index is `courses/MATH-212-*-Fall-2026/MATH-212.md`.

## Discover

```text
python tools/run_tool/run_tool.py read_file_lines commands
```

## Run

```text
python tools/run_tool/run_tool.py read_file_lines courses/MATH-212-Differential-Equations-Fall-2026/MATH-212.md 1 35
```

Read JSON from stdout. For each `needs_llm` item: if `action` is `run`, run `command`; if `ask_user`, ask. Never copy due, status, priority, or estimate into frontmatter.

## Success

- Runner JSON on stdout (no scratch file)
- needs_llm empty or reported
- No due / status / priority / estimate in frontmatter
- Links use real hyphenated class-index paths
