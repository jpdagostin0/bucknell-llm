---
name: fix-vault
description: Fixes vault lint findings from PyMarkdown, Flint, and ls-lint while preserving Obsidian links and Linear ownership boundaries. Use when the user asks to fix Markdown style, frontmatter contracts, filenames, directories, or reported vault lint failures.
---

# Fix Vault

## Fast path

```powershell
.\tools\fast-fix-vault\fast-fix-vault.ps1
```

The runner applies unambiguous PyMarkdown autofixes, strips forbidden Linear frontmatter, restores missing class-index links, qualifies unique bare wikilinks, and rechecks.

## Workflow

1. Run `.\tools\vault-lint\check.ps1` and retain the baseline findings.
2. Run `.\tools\vault-lint\autofix.ps1` for unambiguous PyMarkdown formatting fixes.
3. Re-run the combined check.
4. Resolve remaining findings manually:
   - Fix Markdown structure without changing prose meaning.
   - Add or correct stable frontmatter according to `AGENTS.md`.
   - Treat exact-schema and link-integrity failures as content errors; do not bypass `validate_vault.py`.
   - Never add `status`, `due`, `priority`, or `estimate` to vault frontmatter.
   - Before renaming or moving a file, search for every wikilink and update affected references.
   - Preserve zero-padding, path-qualified wikilinks, course prefixes, and term-suffixed course folders.
   - Do not apply vault-note frontmatter rules to files under `skills/`.
5. Run the combined check until it passes or a finding requires a user decision.
6. Summarize mechanical fixes, reviewed fixes, and unresolved decisions.

Do not weaken a rule solely to hide a legitimate violation. Change configuration only when the rule conflicts with an intentional vault convention, and add or update a negative rule test for every configuration-level fix.
