---
type: tool
---

# Fast Google Calendar

Lists upcoming events for the next 14 days. `create`, `update`, `delete`, and `respond` cover calendar mutations. The Calendar CLI also accepts `upcoming` directly:

```powershell
.\tools\run-tool\run-tool.ps1 google-calendar upcoming --days 14
```

JSON in, JSON out. The default command is `run`. Items the runner will not guess are listed under `needs_llm`.

```powershell
.\tools\fast-google-calendar\fast-google-calendar.ps1
.\tools\fast-google-calendar\fast-google-calendar.ps1 --days 7
```
