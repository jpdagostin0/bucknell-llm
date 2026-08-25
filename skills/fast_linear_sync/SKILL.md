---
name: fast_linear_sync
description: Reconciles Linear issues and vault work notes. Dry-run first.
---

# Fast Linear Sync

Spoken `MATH 212` becomes `--class "MATH 212"`. Never open `MATH 212.md`. The class index is `courses/MATH-212-*-Fall-2026/MATH-212.md`.

## Discover

```text
python tools/run_tool/run_tool.py fast_linear_sync commands
```

## Run

```text
python tools/run_tool/run_tool.py fast_linear_sync --class "MATH 212"
```

Read JSON from stdout. For each `needs_llm` item: if `action` is `run`, run `command`; if `ask_user`, ask. Never copy due, status, priority, or estimate into frontmatter.

`--apply` writes joins and can create supplied issues.

## Success

- Runner JSON on stdout (no scratch file)
- needs_llm empty or reported
- No due / status / priority / estimate in frontmatter
- Links use real hyphenated class-index paths
