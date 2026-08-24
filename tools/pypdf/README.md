---
type: tool
---

# pypdf

Repository-local page extraction wrapper for [pypdf](https://github.com/py-pdf/pypdf), pinned to `6.16.1`.

## Install

```powershell
.\tools\pypdf\install.ps1
```

The installer uses `uv` and does not clone or vendor the upstream repository.

## Inspect page labels

```powershell
.\tools\pypdf\extract-pages.ps1 ".\course-textbook.pdf" --list-labels
```

## Extract printed textbook pages

```powershell
.\tools\pypdf\extract-pages.ps1 `
  ".\course-textbook.pdf" `
  ".\tools\pypdf\output\homework-pages.pdf" `
  --printed-pages "5-6"
```

Use `--pages "12-13"` for one-based physical PDF pages when printed labels are missing or ambiguous. `--find-section "1.1"` prints printed labels whose page text contains that section heading.

The tool refuses to overwrite existing output. Temporary extractions belong in ignored `output/`; retain an extraction only when it is useful beyond the immediate homework session.
