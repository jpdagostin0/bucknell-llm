---
name: fast_dashboard
description: Reads Linear for Fall 2026 due work, exams, and weekly load. Never copy those fields into vault notes.
---

# Fast Dashboard

Spoken `MATH 212` becomes `--class "MATH 212"`. Never open `MATH 212.md`. The class index is `courses/MATH-212-*-Fall-2026/MATH-212.md`.

## Discover

```text
python tools/run_tool/run_tool.py fast_dashboard commands
```

## Run

```text
python tools/run_tool/run_tool.py fast_dashboard --class "MATH 212"
```

Read JSON from stdout. For each `needs_llm` item: if `action` is `run`, run `command`; if `ask_user`, ask. Never copy due, status, priority, or estimate into frontmatter.

Present the snapshot from stdout. Never paste due dates into Home.md.

## Success

- Runner JSON on stdout (no scratch file)
- needs_llm empty or reported
- No due / status / priority / estimate in frontmatter
- Links use real hyphenated class-index paths
