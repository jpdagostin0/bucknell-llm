---
type: tool
---

# Fast Dashboard

Reads Linear for enrolled courses and prints due work, exam-kind issues, and weekly estimate totals. It does not write Linear-owned fields into vault notes.

JSON in, JSON out. The default command is `run`. Use `markdown` for a human-readable table on stdout. Items the runner will not guess are listed under `needs_llm`.

```powershell
.\tools\fast-dashboard\fast-dashboard.ps1
.\tools\fast-dashboard\fast-dashboard.ps1 markdown
.\tools\fast-dashboard\fast-dashboard.ps1 --class "MATH 212"
```

```text
python tools/fast-dashboard/fast_dashboard.py
python tools/fast-dashboard/fast_dashboard.py markdown
python tools/fast-dashboard/fast_dashboard.py --class "MATH 212"
```
