---
type: tool
---

# Fast Sync Class

Mechanical Moodle-to-vault class sync: download, inventory, classify, convert PDFs, hash-compare retained files, update week notes, merge scaffold syllabi, refresh class-index links, extract homework pages, download Drive-only PDFs, and create Linear issues when `--apply` has a project, due date, and kind.

JSON in, JSON out. The default command is `run`. Items the runner will not guess are listed under `needs_llm`.

```powershell
.\tools\fast-sync-class\fast-sync-class.ps1 --class "MATH 212"
.\tools\fast-sync-class\fast-sync-class.ps1 --class "MATH 212" --apply
```
