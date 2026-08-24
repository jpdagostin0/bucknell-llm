---
type: tool
---

# Google Drive

Repository-local [PyDrive2](https://github.com/iterative/PyDrive2) wrapper with an MCP-compatible JSON CLI. Shares Google OAuth secrets with Gmail and Calendar via `.env.yml`.

## Install

```powershell
.\tools\google-auth\install.ps1
.\tools\google-drive\install.ps1
```

Fill `.env.yml`, then run `.\tools\google-auth\google-auth.ps1 login`.

## Commands

Command names match Drive MCP tools. Pass MCP-style camelCase or snake_case arguments as `--json` or flags.

```powershell
.\tools\google-drive\google-drive.ps1 commands
.\tools\google-drive\google-drive.ps1 ping
.\tools\google-drive\google-drive.ps1 search_files --query "title contains 'MATH-212'"
.\tools\google-drive\google-drive.ps1 get_file_metadata --fileId FILE_ID
```
