# Vault Lint

Runs the repository-local Markdown, frontmatter, and filename linters as one vault-aware suite.

## Check

```powershell
.\tools\vault-lint\check.ps1
```

This runs:

- PyMarkdown for Markdown structure and formatting.
- Flint for frontmatter rules.
- `validate_vault.py` for typed schemas, exact allowed fields, scope, resolved path-qualified wikilinks, course ownership, required structure, naming safety, and reciprocal links.
- Negative rule tests that prove malformed metadata and links are rejected.
- ls-lint for directory and filename patterns.

## Mechanical Markdown fixes

```powershell
.\tools\vault-lint\autofix.ps1
```

PyMarkdown only applies formatting fixes it declares unambiguous. Flint and ls-lint findings require review because frontmatter values and file moves affect vault meaning and links.

## Direct integrity check

```powershell
.\tools\pymarkdown\.venv\Scripts\python.exe .\tools\vault-lint\validate_vault.py .
```

The integrity layer covers invariants that Flint 0.0.6 cannot express, while Flint remains the primary declarative frontmatter policy.
