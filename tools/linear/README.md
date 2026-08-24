---
type: tool
---

# Linear

Repository-local [@linear/sdk](https://github.com/linear/linear) wrapper with an MCP-compatible JSON CLI. The personal API key lives in ignored `.env.yml`.

## Install

```powershell
.\tools\linear\install.ps1
```

Fill `linear.api_key` in `.env.yml` before calling mutating or authenticated commands.

## Commands

Command names match Linear MCP tools used by this vault. Inspect current data before creating or changing issues.

```powershell
.\tools\linear\linear.ps1 commands
.\tools\linear\linear.ps1 ping
.\tools\linear\linear.ps1 list_teams
.\tools\linear\linear.ps1 list_issues --limit 10 --team JPS
.\tools\linear\linear.ps1 get_issue --id JPS-5
```

Keep due dates, status, priority, and estimates in Linear. Vault notes join issues with `linear` and `linear_url` only.
