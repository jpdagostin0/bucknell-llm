---
name: fast_selenium
description: Installs and pings the Selenium CLI for non-Moodle pages.
---

# Fast Selenium

Spoken `MATH 212` becomes `--class "MATH 212"`. Never open `MATH 212.md`. The class index is `courses/MATH-212-*-Fall-2026/MATH-212.md`.

## Discover

```text
python tools/run_tool/run_tool.py fast_selenium commands
```

## Run

```text
python tools/run_tool/run_tool.py fast_selenium
```

Read JSON from stdout. For each `needs_llm` item: if `action` is `run`, run `command`; if `ask_user`, ask. Never copy due, status, priority, or estimate into frontmatter.

For capture-only, run `fast_fetch_webpage`. Never use this on moodle hosts.

## Success

- Runner JSON on stdout (no scratch file)
- needs_llm empty or reported
- No due / status / priority / estimate in frontmatter
- Links use real hyphenated class-index paths
