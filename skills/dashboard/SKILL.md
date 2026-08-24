---
name: dashboard
description: Reads Linear for Fall 2026 due work, exam-kind issues, and weekly estimate totals. Use when refreshing Home.md views, answering what is due, or computing weekly load. Never copy those Linear fields into vault notes.
---

# Dashboard

## Fast path

```powershell
.\tools\fast-dashboard\fast-dashboard.ps1
.\tools\fast-dashboard\fast-dashboard.ps1 markdown
.\tools\fast-dashboard\fast-dashboard.ps1 --class "MATH 212"
```

```text
python tools/fast-dashboard/fast_dashboard.py
python tools/fast-dashboard/fast_dashboard.py markdown
```

The runner returns `{due_work, exams, weekly_load, needs_llm}`. `run` is JSON. `markdown` prints tables on stdout. It does not write the vault.

## Ownership

Linear owns due dates, workflow state, priority, estimates, and cycles. `Home.md` stays a pointer: course wikilinks plus these commands. Do not paste a frozen due-date table into `Home.md` or any note YAML.

## Workflow

1. Run `tools/fast-dashboard/` before answering what is due this week.
2. Use `--class` when the user named one course.
3. Treat `exams` as open issues with the `exam` kind label. Other open work is `due_work`, sorted by `dueDate`.
4. Read `weekly_load` for Fibonacci estimate totals. Cycle name `Week NN` wins; otherwise the week is computed from `dueDate` against term start 2026-08-24.
5. Closed statuses (`Done`, `Canceled`, `Graded`, `Missed`, `Excused`, and Linear `completed`/`canceled` types) are already filtered.
6. Present the live snapshot in chat. Resolve `needs_llm` items such as missing due dates, estimates, kind labels, or unconfigured cycles. Do not copy those values into vault frontmatter.
