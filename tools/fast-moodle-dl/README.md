---
type: tool
---

# Fast Moodle-DL

Installs Moodle-DL if needed, syncs staging, and inventories course files without opening credential files.

JSON in, JSON out. The default command is `run`. Items the runner will not guess are listed under `needs_llm`.

```powershell
.\tools\fast-moodle-dl\fast-moodle-dl.ps1
.\tools\fast-moodle-dl\fast-moodle-dl.ps1 --class "MATH 245" --skip-download
```
