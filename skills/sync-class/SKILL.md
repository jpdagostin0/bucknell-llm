---
name: sync-class
description: Synchronizes a Fall 2026 class end to end from Moodle into the standard Obsidian course structure, using Moodle-DL for staging and MarkItDown for PDF extraction. Use when the user asks to sync, refresh, or import a class or its LMS content.
---

# Sync Class

## Fast path

Run the mechanical workflow first. Without `--apply` it downloads Moodle content, inventories staging, classifies files, converts PDFs, hash-compares retained copies, and plans week notes, syllabus merges, Drive downloads, homework-page extracts, and Linear issues. `--apply` performs those writes when the inputs are unambiguous.

```powershell
.\tools\fast-sync-class\fast-sync-class.ps1 --class "MATH 212"
.\tools\fast-sync-class\fast-sync-class.ps1 --class "MATH 212" --apply
```

`--apply` copies new files, updates week notes, merges scaffold syllabi, refreshes class-index links, extracts homework pages, downloads Drive PDFs that are not in Moodle, and creates Linear issues when a project, due date, and kind are available. `--overwrite` replaces a retained file whose hash changed. Use the rest of this skill only for remaining `needs_llm` items.

Read and follow `skills/moodle-dl/SKILL.md` and `skills/markitdown/SKILL.md` before starting.

## Workflow

1. Resolve the requested class by stable course code using [reference.md](reference.md). Confirm its Moodle staging directory and vault course folder.
2. If the class index has a Google Drive `content` URL and Drive MCP is available, inspect that folder by stable ID and note files not already present in Moodle staging.
3. Run the repository-local Moodle sync:

   ```powershell
   .\tools\moodle-dl\moodle-dl.ps1
   ```

4. Inventory only the matched course directory under `tools/moodle-dl/state/`. Never inspect Moodle credential or cookie files.
5. Classify each new or changed item:
   - Instructor syllabus or durable binary reference → retain in flat `attachments/` with a course-code prefix.
   - Full-length textbook → retain in the owning course's `textbooks/` directory with a course-code prefix.
   - PDF with prose or structured course content → convert to ignored Markdown with `skills/markitdown/SKILL.md`.
   - Week-specific lecture, reading, or worksheet material → synthesize into `notes/Week-NN.md`.
   - Assignment or deadline-bearing item → retain the source when useful and prepare a Linear import review.
   - Assignment citing textbook pages → use `skills/get-homework-pages/SKILL.md` to prepare the smallest useful temporary extraction.
   - Generic, duplicate, or ephemeral resource → leave in staging.
6. Normalize converted content:
   - Remove extraction artifacts and repeated headers or footers.
   - Preserve meaningful headings, lists, links, tables, and equations.
   - Merge stable syllabus facts into `Syllabus.md`.
   - Add instructor, office hours, and meeting facts to the class index.
   - Create a weekly note only when course content exists.
7. Link every retained attachment and created note from the relevant class index, syllabus, or week note using path-qualified wikilinks.
8. `--apply` is the explicit import approval for Linear issues that already have a course project, due date, and kind label. Report anything missing those fields under `needs_llm` or `pending_create`. Follow `skills/linear-sync/SKILL.md` for join repair. Linear remains the source of truth for due dates, state, priority, estimates, and cycles. Never copy those fields into vault frontmatter.
9. Validate:
   - Every vault note outside `skills/` has a valid `type`.
   - No forbidden mutable fields appear in vault frontmatter.
   - General retained binary filenames are flat and course-prefixed; textbooks are course-level and course-prefixed.
   - Links resolve without ambiguous bare filenames.
   - Raw Moodle and MarkItDown state remains ignored.
10. Report downloaded, retained, synthesized, skipped, and review-pending items.

## Idempotency

- Match courses by code before title.
- Compare file hashes before copying attachments.
- Never overwrite a changed retained attachment silently.
- Update existing typed notes instead of creating duplicate notes.
- Do not create a work note without a stable Linear issue key.
