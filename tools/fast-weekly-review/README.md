---
type: tool
---

# Fast Weekly Review

Produces a JSON weekly-review report: inbox classification, open Linear issues missing a cycle, estimate load by `Week NN` cycle, and unfinished issues that still need an explicit roll / miss / excuse decision.

JSON in, JSON out. The default command is `run`. Default is dry-run. The runner never changes Linear statuses, never sets Missed, never reopens submissions, and never creates issues from inbox files. `--apply` does not mutate Linear; inbox files are listed and classified only.

```powershell
.\tools\fast-weekly-review\fast-weekly-review.ps1
.\tools\fast-weekly-review\fast-weekly-review.ps1 --week 1
.\tools\fast-weekly-review\fast-weekly-review.ps1 --class "MATH 212" --week 1
.\tools\fast-weekly-review\fast-weekly-review.ps1 --apply
```
