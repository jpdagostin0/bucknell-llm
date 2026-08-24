---
type: tool
---

# Fast Gradescope

Read-only course listing by default. `assignments` and `upload` cover due-date inspection and an explicit submission.

JSON in, JSON out. The default command is `run`. Items the runner will not guess are listed under `needs_llm`.

```powershell
.\tools\fast-gradescope\fast-gradescope.ps1
.\tools\fast-gradescope\fast-gradescope.ps1 --class "MATH 212"
.\tools\fast-gradescope\fast-gradescope.ps1 assignments --courseId 123456
```
