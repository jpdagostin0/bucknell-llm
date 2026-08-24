---
name: import-syllabus
description: >-
  Proposes and creates Linear issues from dated obligations in a course
  Syllabus.md. Use when importing a syllabus into Linear, turning exam or
  homework dates into issues, or reviewing syllabus-derived deadlines.
---

# Import Syllabus

## Fast path

Dry-run first. The runner reads `Syllabus.md` and already-extracted retained attachment text only. It does not invent due dates or write Linear-owned fields into vault frontmatter.

```powershell
.\tools\fast-import-syllabus\fast-import-syllabus.ps1
.\tools\fast-import-syllabus\fast-import-syllabus.ps1 --class "MATH 212"
.\tools\fast-import-syllabus\fast-import-syllabus.ps1 --class "MATH 212" --apply
```

`--apply` creates issues through the Linear CLI when a course project, due date, and one Kind label are available. Existing issues are matched by normalized title before create. Use the rest of this skill only for remaining `needs_llm` items.

## Remaining `needs_llm`

- `no_dated_obligations`: the syllabus (and optional attachment text) has no dated homework, lab, quiz, reading, or exam lines. If it says deadlines live in Linear, leave dates there; do not copy them into the vault.
- `missing_due`: an obligation-like line has no parseable date. Do not guess. Ask for an authoritative date or skip.
- `missing_kind`: a dated line does not map to `pset`, `reading`, `lab`, `quiz`, or `exam`. Do not use the label name `project`; use `course project` only after explicit review.
- `attachment_text_unavailable`: the retained syllabus file is binary and has no existing MarkItDown output. Convert it with `skills/markitdown/SKILL.md` only when dated obligations are expected in that file.
- `pending_create`: Linear is missing team, project, due date, or Kind label. Complete those fields before leaving triage.
- `linear_unavailable` / `missing_syllabus`: repair access or the course folder, then rerun.

Prefix Linear titles with `(tentative)` when the source marks an exam as tentative. Follow `skills/linear-sync/SKILL.md` after creates if work-note joins are needed. Missing work notes are normal.
