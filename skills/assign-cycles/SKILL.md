---
name: assign-cycles
description: Assigns Linear issues to weekly Week NN cycles from dueDate. Use when mapping coursework due dates onto Fall 2026 weekly cycles, or when Linear issues are missing cycle assignment.
---

# Assign Cycles

## Fast path

Dry-run by default. `--apply` sets only `cycleId` via Linear `save_issue --json-file`. It does not change titles, descriptions, or labels, and it never copies cycle or due date into vault frontmatter.

```powershell
.\tools\fast-assign-cycles\fast-assign-cycles.ps1
.\tools\fast-assign-cycles\fast-assign-cycles.ps1 --class "MATH 245"
.\tools\fast-assign-cycles\fast-assign-cycles.ps1 --class "MATH 245" --apply
```

Week number is `((dueDate - 2026-08-24).days // 7) + 1`, clamped to 1–16. Cycles are matched by name (`Week 01` or `Week 1`, case-insensitive). Issues already on the correct cycle are skipped.

## Workflow

1. Run the fast path without `--apply` and inspect `assignments` and `needs_llm`.
2. If `needs_llm` includes `cycles_unconfigured`, stop. Do not invent Linear cycles. Configure weekly `Week NN` cycles on the Fall 2026 team, then rerun.
3. Issues without `dueDate` stay unassigned. Report `missing_due_date`; do not guess a week.
4. After review, rerun with `--apply` so the runner writes `cycleId` only.
5. Re-run the dry path; remaining work should be `skip` or explicit `needs_llm` items.

Use the rest of this skill only for remaining `needs_llm` items such as unconfigured cycles, missing due dates, and unmatched week names.
