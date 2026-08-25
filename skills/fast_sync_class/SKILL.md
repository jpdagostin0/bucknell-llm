---
name: fast_sync_class
description: Synchronizes one Fall 2026 class from Moodle into the vault. Mechanical steps are in the runner.
---

# Fast Sync Class

Spoken `MATH 212` becomes `--class "MATH 212"`. Never open `MATH 212.md`. The class index is `courses/MATH-212-*-Fall-2026/MATH-212.md`.

## Discover

```text
python tools/run_tool/run_tool.py fast_sync_class commands
```

## Run

```text
python tools/run_tool/run_tool.py fast_sync_class --class "MATH 212"
```

Read JSON from stdout. For each `needs_llm` item: if `action` is `run`, run `command`; if `ask_user`, ask. Never copy due, status, priority, or estimate into frontmatter.

Dry-run first. `--apply` writes when inputs are unambiguous. Handle each `needs_llm.kind` one at a time.

## Success

- Runner JSON on stdout (no scratch file)
- needs_llm empty or reported
- No due / status / priority / estimate in frontmatter
- Links use real hyphenated class-index paths
