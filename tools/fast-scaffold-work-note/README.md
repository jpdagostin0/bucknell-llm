---
type: tool
---

# Fast Scaffold Work Note

Plans or writes an opt-in work note from a Linear issue key. Dry-run is the default. `--apply` creates the note through `scaffold_work_note`. Existing notes are left alone unless `--overwrite` is passed.

JSON in, JSON out. The default command is `run`. Items the runner will not guess are listed under `needs_llm`. Missing work notes are normal in this vault; run this tool only when the user asked for a note.

```powershell
.\tools\fast-scaffold-work-note\fast-scaffold-work-note.ps1 --linear JPS-5
.\tools\fast-scaffold-work-note\fast-scaffold-work-note.ps1 --id JPS-5
.\tools\fast-scaffold-work-note\fast-scaffold-work-note.ps1 --linear JPS-5 --apply
.\tools\fast-scaffold-work-note\fast-scaffold-work-note.ps1 --linear JPS-5 --apply --overwrite
```
