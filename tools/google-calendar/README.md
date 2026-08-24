---
type: tool
---

# Google Calendar

Repository-local [gcsa](https://github.com/kuzmoyev/google-calendar-simple-api) wrapper with an MCP-compatible JSON CLI. Shares Google OAuth secrets with Drive and Gmail via `.env.yml`.

## Install

```powershell
.\tools\google-auth\install.ps1
.\tools\google-calendar\install.ps1
```

Fill `.env.yml`, then run `.\tools\google-auth\google-auth.ps1 login`. Set `google.email` to the calendar account if it is not the OAuth default.

## Commands

```powershell
.\tools\google-calendar\google-calendar.ps1 commands
.\tools\google-calendar\google-calendar.ps1 ping
.\tools\google-calendar\google-calendar.ps1 list_calendars
.\tools\google-calendar\google-calendar.ps1 upcoming --days 14
.\tools\google-calendar\google-calendar.ps1 list_events --timeMin 2026-08-22T00:00:00-04:00
```

`upcoming` lists events from now through `--days` (default 14). `list_events` is the same lookup with explicit `--timeMin` / `--timeMax`. `--help` and `commands` print the JSON command catalog.
