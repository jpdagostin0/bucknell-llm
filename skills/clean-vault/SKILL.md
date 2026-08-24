---
name: clean-vault
description: Runs a complete check-and-fix cycle across Markdown, frontmatter, filenames, and directories using PyMarkdown, Flint, and ls-lint. Use when the user asks to clean, normalize, or fully lint and repair the coursework vault.
---

# Clean Vault

## Fast path

```powershell
.\tools\fast-clean-vault\fast-clean-vault.ps1
```

The runner performs one check-and-fix cycle and reports whether the vault is clean. Use this skill only for remaining reviewed repairs.

1. Read and follow `skills/check-vault/SKILL.md`.
2. If every check passes, report that the vault is clean and stop.
3. Read and follow `skills/fix-vault/SKILL.md`.
4. Run `.\tools\vault-lint\check.ps1` once more.
5. Finish only when all checks pass or a required user decision is documented.

Keep the scope limited to reported lint findings. Do not reorganize valid content or settle the unresolved design choices in `AGENTS.md`.
