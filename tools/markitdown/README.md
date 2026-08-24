---
type: tool
---

# MarkItDown

Repository-local wrapper for [Microsoft MarkItDown](https://github.com/microsoft/markitdown), pinned to `markitdown[pdf,docx]==0.1.7`.

## Install

```powershell
.\tools\markitdown\install.ps1
```

The installer uses `uv` to create an ignored Python 3.12 environment under `.venv/`. It installs the published package and does not clone or vendor the upstream repository.

## Convert a PDF

```powershell
.\tools\markitdown\markitdown.ps1 ".\input.pdf" -o ".\tools\markitdown\output\document.md"
```

Raw conversions belong in ignored `output/`. Review and rewrite them into the appropriate typed Obsidian note; do not copy converter output directly into the vault without normalization.

## Security

- Convert only known local PDF and DOCX course files.
- Do not pass untrusted URLs or arbitrary paths.
- MarkItDown runs with the current process's file access.
