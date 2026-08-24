---
type: tool
---

# Fast Linear

Linear preflight plus `issues`, `save`, and `comment` for class-filtered lists and mutations.

JSON in, JSON out. The default command is `run`. Items the runner will not guess are listed under `needs_llm`.

```powershell
.\tools\fast-linear\fast-linear.ps1
.\tools\fast-linear\fast-linear.ps1 issues --class "MATH 212"
.\tools\fast-linear\fast-linear.ps1 save --class "MATH 212" --title "MATH 212 — Homework 02" --dueDate 2026-09-04
```
