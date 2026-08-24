---
name: weekly-review
description: >-
  Produces a Fall 2026 weekly review of the Obsidian inbox and Linear
  obligations. Use when the user asks for weekly review, inbox emptying,
  cycle load, unfinished work, or roll/miss/excuse decisions.
---

# Weekly Review

## Fast path

Inspect inbox and Linear without changing workflow state:

```powershell
.\tools\fast-weekly-review\fast-weekly-review.ps1
.\tools\fast-weekly-review\fast-weekly-review.ps1 --week 1
.\tools\fast-weekly-review\fast-weekly-review.ps1 --class "MATH 212" --week 1
```

`--week` selects the cycle to treat as current. Without it, the runner uses the Fall 2026 term week for today (dates before `2026-08-24` clamp to week 1). `--class` limits Linear inspection to one enrolled course.

`--apply` does not change Linear statuses, estimates, cycles, or issues. Inbox `*.md` files are listed and classified as deadline-bearing versus capture. Do not invent Linear issues from inbox files.

Read `AGENTS.md` before acting on `needs_llm` items.

## Ownership

- Linear owns due dates, workflow state, priority, estimates, cycles, and grade-state labels.
- The vault owns inbox captures without deadlines, notes, and subject-matter thinking.
- Deadline-bearing captures belong in Linear triage, not `inbox/`.
- Never copy `status`, `due`, `priority`, or `estimate` into vault frontmatter.

## Workflow

1. Run the fast runner and read `inbox`, `issues_without_cycle`, `weekly_load`, `unfinished`, and `needs_llm`.
2. Empty `inbox/`:
   - Ordinary `type: capture` notes without deadlines stay as captures until the user files or discards them.
   - Deadline-bearing files are `needs_llm` for Linear triage. Do not create issues unless the user reviews and supplies a course, due date, and kind.
3. If `cycles_unconfigured` appears, stop guessing cycle assignment. Weekly `Week NN` cycles still require Linear configuration.
4. Assign open issues that lack a cycle only when the user confirms the week.
5. Use `weekly_load` estimate sums to warn about overloaded weeks. Re-estimate in Linear, not in vault frontmatter.
6. For each `unfinished` issue, ask the user to **roll**, **miss**, or **excuse**. Do not set Missed automatically. Do not reopen an original submission; a resubmission or regrade is a related issue.

## Validation

- Linear was not mutated by the runner.
- Inbox files were classified, not turned into guessed issues.
- Unfinished items remain `needs_llm` until the user chooses roll, miss, or excuse.
- Vault notes still contain no Linear-owned mutable fields.
