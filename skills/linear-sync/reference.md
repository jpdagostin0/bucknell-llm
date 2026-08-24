---
type: skill-reference
---

# Linear Sync Reference

## Naming

- Issue: `<COURSE CODE> — <Obligation>`
- Homework example: `MATH 245 — Homework 01 — Linear Systems`
- Work note: `<COURSE-CODE> <Item> <slug>.md`
- Cycle: `Week NN`

## Estimates

- `1`: under 1 focused hour
- `2`: 1–2 focused hours
- `3`: 3–5 focused hours
- `5`: 6–10 focused hours
- Decompose anything that would be `8`.

## Kind labels

- `pset`
- `reading`
- `lab`
- `quiz`
- `exam`
- `course project`
- `study`
- `admin`

## Current limitations

- The connected team is still named `JP's Workspace`; it represents Fall 2026 until manually renamed.
- Weekly cycles are not configured, so issue creation must report missing cycle assignment.
- Submitted, Graded, Blocked, Excused, and Missed are not yet configured as workflow statuses.
- The exact label name `project` is reserved by Linear; use `course project`.

## Link examples

Linear issue description:

```markdown
Vault source: `attachments/MATH-245 Homework-01 Linear Systems.pdf`
Week context: `courses/MATH-245-Linear-Algebra-Fall-2026/notes/Week-01.md`
```

Obsidian work-note frontmatter:

```yaml
type: assignment
linear: JPS-5
linear_url: https://linear.app/...
class: "[[courses/MATH-245-Linear-Algebra-Fall-2026/MATH-245]]"
kind: pset
worked:
  - "[[courses/MATH-245-Linear-Algebra-Fall-2026/notes/Week-01]]"
```
