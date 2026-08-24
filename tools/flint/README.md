# Flint

Repository-local [Flint](https://github.com/hay-kot/flint) binary for validating vault frontmatter.

## Install

```powershell
.\tools\flint\install.ps1
```

The installer downloads the pinned Windows release with GitHub CLI and keeps the binary under ignored `bin/`.

## Run

```powershell
.\tools\flint\flint.ps1 --config .flint.yml
```

The root `.flint.yml` applies path-specific required fields, exact note types, enums, URL and wikilink patterns, date formats, text bounds, and Linear ownership restrictions.

Flint 0.0.6 has two upstream behaviors handled by `tools/vault-lint/check.ps1`:

- Only the final path in a multi-path content block is checked, so every block in `.flint.yml` contains exactly one path.
- Reported rule errors still return exit code zero, so the combined wrapper detects Flint's error records in its output.

The rule tests verify both safeguards with an intentionally invalid course index.
