---
type: tool
---

# Read File Lines

Print a 1-based inclusive line range from a text file as JSON. No virtualenv.

```powershell
.\tools\run-tool\run-tool.ps1 read_file_lines courses/MATH-212-Differential-Equations-Fall-2026/MATH-212.md 1 35
.\tools\read-file-lines\read-file-lines.ps1 --path Home.md --start 1 --end 20
```

```text
python tools/read-file-lines/read_file_lines.py <path> [start] [end]
```

Omit `end` to read through the last line. Refuses `.env.yml` and tool state directories.
