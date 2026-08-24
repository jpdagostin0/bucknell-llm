---
name: linear-sync
description: Synchronizes coursework bidirectionally between Linear and the Obsidian vault while preserving field ownership. Use when creating obligations from course content, linking Linear issues to notes, reconciling existing links, or refreshing coursework state across both systems.
---

# Linear Sync

## Fast path

Inspect joins and ownership invariants without copying Linear-owned fields into the vault:

```powershell
.\tools\fast-linear-sync\fast-linear-sync.ps1
.\tools\fast-linear-sync\fast-linear-sync.ps1 --class "MATH 245" --apply
```

`--apply` only fills missing `linear_url` values and strips forbidden mutable frontmatter. Create new issues with `fast-sync-class --apply` or `fast-linear save`. Use this skill for remaining `needs_llm` items such as broken joins and missing-note decisions.

Read `AGENTS.md` before every synchronization. Bidirectional means exchanging stable identifiers, pointers, and explicitly owned content; it does not mean mirroring every field.

## Ownership

- Linear owns due dates, workflow state, priority, estimates, cycles, project assignment, and grade-state labels.
- Obsidian owns syllabi, lecture notes, derivations, drafts, synthesis, and feedback artifacts.
- Stable joins cross the boundary: Linear issue key, Linear URL, course project, vault path, and source links.

## Preflight

1. Inspect the current Linear team, projects, labels, statuses, cycles, and matching issues before mutation.
2. Match existing objects by stable ID or issue key first, then normalized title only as a fallback.
3. Resolve the owning course from the class index and Linear project.
4. Stop for user review when a source import would create multiple syllabus-derived issues or milestones.

## Linear to Obsidian

1. Fetch the issue by key.
2. If a linked work note exists, verify these stable fields:
   - `linear`
   - `linear_url`
   - `class`
   - optional `parent`
   - `worked`
3. Do not copy `status`, `due`, `priority`, `estimate`, or cycle into vault frontmatter or prose dashboards.
4. Update path-qualified links from the class index and touched week notes.
5. Treat a missing work note as normal. Create one only when there is prose worth retaining.

## Obsidian to Linear

1. Read stable issue joins from work-note frontmatter or an explicit course-source pointer.
2. Fetch the current issue before updating it.
3. Push only Linear-owned changes explicitly requested by the user or extracted from an authoritative syllabus/LMS source.
4. Keep Linear descriptions concise:
   - Atomic obligation or acceptance criteria
   - Stable vault source or work-note path
   - Essential submission channel
5. Put short factual progress logs in Linear comments; retain reasoning and subject-matter work in Obsidian.
6. For a new non-triage issue, require exactly one course project, a due date, and one `Kind` label. Add an estimate and applicable `Week NN` cycle when available.

## Reconciliation

1. Compare stable joins and ownership invariants, not duplicated mutable values.
2. If a forbidden mutable field exists in vault frontmatter, remove it only when authorized and report the correction; never push it back to Linear.
3. If a Linear issue points to a missing note, leave it missing unless retained prose justifies a note.
4. If a note points to a missing or inaccessible issue, report the broken join and do not create a replacement silently.
5. Never reopen an original submission for a resubmission or regrade; create a related issue.

## Validation

- Every synchronized issue has one course project, a due date, and one kind label before leaving triage.
- Every existing work note has a valid Linear key and path-qualified class link.
- Linear descriptions point to the correct vault artifact.
- Vault notes contain no forbidden mutable frontmatter.
- Re-running the sync creates no duplicate issues, comments, notes, or links.

Read [reference.md](reference.md) for naming, estimates, and current workspace limitations.
