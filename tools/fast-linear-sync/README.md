---
type: tool
---

# Fast Linear Sync

Inspects Linear and work-note joins, reports broken keys and triage gaps, and with `--apply` fills missing `linear_url` values or strips forbidden mutable frontmatter.

JSON in, JSON out. The default command is `run`. Items the runner will not guess are listed under `needs_llm`.

```powershell
.\tools\fast-linear-sync\fast-linear-sync.ps1
.\tools\fast-linear-sync\fast-linear-sync.ps1 --class "MATH 245" --apply
```
