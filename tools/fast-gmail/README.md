---
type: tool
---

# Fast Gmail

Read-only unread-thread search by default. `get`, `send`, `reply`, `draft`, `trash`, and `label` cover the rest of the Gmail workflow.

JSON in, JSON out. The default command is `run`. Items the runner will not guess are listed under `needs_llm`.

```powershell
.\tools\fast-gmail\fast-gmail.ps1
.\tools\fast-gmail\fast-gmail.ps1 --query "from:sej010 newer_than:14d"
```
