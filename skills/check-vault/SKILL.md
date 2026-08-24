---
name: check-vault
description: Checks the coursework vault with PyMarkdown, Flint, and ls-lint without changing files. Use when the user asks to lint, validate, audit, or check vault formatting, frontmatter, filenames, or directory structure.
---

# Check Vault

## Fast path

```powershell
.\tools\fast-check-vault\fast-check-vault.ps1
```

The runner returns structured JSON grouped by linter. It does not modify files. Exit code 1 means a check failed.

Run from the vault root:

```powershell
.\tools\vault-lint\check.ps1
```

## Workflow

1. Install any missing linter with its `tools/<name>/install.ps1` script.
2. Run the combined check once.
3. Group findings by:
   - PyMarkdown: Markdown structure and formatting.
   - Flint: required fields, exact types, enums, patterns, dates, lengths, and forbidden frontmatter.
   - Vault integrity: typed and exact schemas, layout scope, link resolution, ownership, and reciprocal links.
   - Rule tests: failures in negative controls that prove invalid content is rejected.
   - ls-lint: directory and filename conventions.
4. Report paths, rule IDs, and the smallest safe remediation.

Do not modify files in this skill. Treat tool or configuration failures separately from content violations.
