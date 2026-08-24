---
type: tool
---

# Fast Import Syllabus

Reads each course `Syllabus.md` (and already-extracted retained attachment text when present), proposes Linear issues for dated obligations, and with `--apply` creates or matches them. Default is dry-run.

JSON in, JSON out. The default command is `run`. Items the runner will not guess are listed under `needs_llm`.

```powershell
.\tools\fast-import-syllabus\fast-import-syllabus.ps1
.\tools\fast-import-syllabus\fast-import-syllabus.ps1 --class "MATH 212"
.\tools\fast-import-syllabus\fast-import-syllabus.ps1 --class "MATH 212" --apply
```
