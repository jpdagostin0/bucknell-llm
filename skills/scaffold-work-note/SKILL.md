---
name: scaffold-work-note
description: Scaffolds an opt-in Obsidian work note from a Linear issue key without copying due dates or workflow state. Use when the user asks to create a work note for an issue such as JPS-5.
---

# Scaffold Work Note

## Fast path

```powershell
.\tools\fast-scaffold-work-note\fast-scaffold-work-note.ps1 --linear JPS-5
.\tools\fast-scaffold-work-note\fast-scaffold-work-note.ps1 --id JPS-5
.\tools\fast-scaffold-work-note\fast-scaffold-work-note.ps1 --linear JPS-5 --apply
.\tools\fast-scaffold-work-note\fast-scaffold-work-note.ps1 --linear JPS-5 --apply --overwrite
```

Run the fast runner first. Dry-run is the default. Write a note only when the user asked or `--apply` is explicit. A missing work note is normal; do not scaffold every issue.

## Workflow

1. Fetch the issue with `run_json_tool("linear", ["get_issue", "--id", key])` via the fast runner.
2. Resolve the course from the issue project against class-index `linear_project` URLs and names (`project_id_for` / `issues_for_course`).
3. Map the Linear Kind label onto the vault kind (`pset` stays `pset`; `course project` is allowed).
4. If a work note for that key already exists, return `{planned: false, path}` and leave it. Overwrite only with `--overwrite`.
5. Keep frontmatter to `type`, `linear`, `linear_url`, `class`, `kind`, and optional `parent` / `worked`. Never copy `status`, `due`, `priority`, or `estimate`.
6. Keep the body from `scaffold_work_note`, or follow `templates/Assignment.md` headings (Prompt, Working Notes, References, Feedback) if customizing prose.
7. After `--apply`, the runner may call `apply_class_index_links` so the class index lists the new work note.

## Boundaries

- Linear owns due dates, state, priority, estimates, and cycles.
- Create notes only when retained prose is wanted.
- Do not invent a course or kind, and do not overwrite without an explicit flag.
