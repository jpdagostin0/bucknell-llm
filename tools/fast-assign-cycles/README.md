---
type: tool
---

# Fast Assign Cycles

Maps each Linear issue `dueDate` to weekly cycle `Week NN` from term start Monday 2026-08-24. Dry-run by default. `--apply` writes only `cycleId` through `save_issue --json-file`.

JSON in, JSON out. The default command is `run`. Items the runner will not guess are listed under `needs_llm`.

```powershell
.\tools\fast-assign-cycles\fast-assign-cycles.ps1
.\tools\fast-assign-cycles\fast-assign-cycles.ps1 --class "MATH 245"
.\tools\fast-assign-cycles\fast-assign-cycles.ps1 --class "MATH 245" --apply
```
