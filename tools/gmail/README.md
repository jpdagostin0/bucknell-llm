---
type: tool
---

# Gmail

Repository-local [simplegmail](https://github.com/jeremyephron/simplegmail) wrapper with an MCP-compatible JSON CLI. Shares Google OAuth secrets with Drive and Calendar via `.env.yml`.

## Install

```powershell
.\tools\google-auth\install.ps1
.\tools\gmail\install.ps1
```

Fill `.env.yml`, then run `.\tools\google-auth\google-auth.ps1 login`.

## Commands

```powershell
.\tools\gmail\gmail.ps1 commands
.\tools\gmail\gmail.ps1 ping
.\tools\gmail\gmail.ps1 search_threads --query "is:unread newer_than:7d" --pageSize 10
.\tools\gmail\gmail.ps1 list_labels
```

Do not send, reply, trash, or label mail unless the user asked for that mutation.
