---
name: read-file-lines
description: >-
  Reads a text file by 1-based line numbers through the repository CLI.
  Use when opening a vault note, syllabus, class index, or any local text
  file by path and optional start/end lines.
---

# Read File Lines

Do not guess spaced class-index names. Resolve the path from `Home.md` or `AGENTS.md`, then read lines with this CLI.

```powershell
.\tools\run-tool\run-tool.ps1 read_file_lines <path> [start] [end]
.\tools\run-tool\run-tool.ps1 read_file_lines courses/MATH-212-Differential-Equations-Fall-2026/MATH-212.md 1 35
```

```text
python tools/read-file-lines/read_file_lines.py <path> [start] [end]
```

`start` and `end` are 1-based and inclusive. Omit `end` to read the rest of the file. JSON `data.text` is the slice; `data.lines` is numbered. Never point this tool at `.env.yml`.
