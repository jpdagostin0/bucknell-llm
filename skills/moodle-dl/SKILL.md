---
name: moodle-dl
description: Downloads and reviews Moodle course resources with the repository-local Moodle-DL tool. Use when the user mentions Moodle, LMS synchronization, course downloads, lecture files, assignment discovery, or refreshing course materials.
---

# Moodle-DL

## Fast path

```powershell
.\tools\fast-moodle-dl\fast-moodle-dl.ps1
.\tools\fast-moodle-dl\fast-moodle-dl.ps1 --class "MATH 245" --skip-download
```

The runner installs Moodle-DL if needed, syncs staging, and inventories course files without opening credential files. Classification and retention still follow the workflow below, or `skills/sync-class/SKILL.md` for the full import.

Use `tools/moodle-dl/` to stage Moodle content without weakening the vault–Linear ownership boundary.

## Routing

If you are given a URL that does not start with moodle, do not attempt to use the moodle tool on it. Moodle-DL is only for hosts whose hostname starts with `moodle`. Use `skills/fetch-webpage/SKILL.md` and `tools/selenium/` for every other http(s) URL.

## Safety rules

- Never read, print, summarize, transmit, or commit `tools/moodle-dl/state/config.json`, Moodle tokens, private tokens, or cookies.
- Never ask the user to paste Moodle credentials or tokens into chat.
- Initialization is interactive. Ask the user to run it in their own terminal.
- Treat everything under `tools/moodle-dl/state/` as ignored staging data, not retained vault content.
- Do not automatically turn Moodle assignments into Linear issues. Prepare an explicit review first.

## Workflow

1. Check whether `tools/moodle-dl/.venv/Scripts/moodle-dl.exe` exists.
2. If missing, run `tools/moodle-dl/install.ps1`.
3. If `state/config.json` is missing, tell the user to run:

   ```powershell
   .\tools\moodle-dl\moodle-dl.ps1 --init --sso
   ```

   Stop until initialization is complete.

4. Run a sync:

   ```powershell
   .\tools\moodle-dl\moodle-dl.ps1
   ```

5. Review newly downloaded filenames and metadata without opening credential files.
6. Classify results:
   - Reference material worth retaining: copy to flat `attachments/` with a course-code prefix, then link it from the relevant course note.
   - Full-length textbook: copy to the owning course's `textbooks/` directory with a course-code prefix.
   - Prose or explanations: synthesize into the relevant syllabus, week, or work note.
   - Deadline-bearing obligations: draft a Linear import for explicit user review.
   - Ephemeral or duplicate LMS material: leave in staging.
7. Report what was downloaded, retained, skipped, or awaiting review.

## Integration rules

- Match courses by stable course code before normalized title.
- Preserve original files in staging; do not silently overwrite retained attachments.
- Never add `status`, `due`, `priority`, or `estimate` to vault frontmatter.
- Create work notes only when there is prose worth retaining.
- Follow the syllabus-to-issue review requirement in `AGENTS.md`.

## Reference

Read [reference.md](reference.md) for commands, paths, and troubleshooting.
