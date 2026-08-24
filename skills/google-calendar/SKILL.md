---
name: google-calendar
description: Calls the repository-local Google Calendar CLI (gcsa) with MCP-compatible command names. Use instead of Calendar MCP when listing calendars, reading events, or creating events.
---

# Google Calendar

## Fast path

```powershell
.\tools\fast-google-calendar\fast-google-calendar.ps1
.\tools\fast-google-calendar\fast-google-calendar.ps1 --days 7
.\tools\run-tool\run-tool.ps1 google-calendar upcoming --days 14
```

The runner lists upcoming events. `create`, `update`, `delete`, and `respond` cover calendar mutations. `google-calendar upcoming` is the same lookup on the Calendar CLI; do not invent other command names. Discover commands with `google-calendar commands` or `--help`.

Prefer `tools/google-calendar/` over Calendar MCP.

## Setup

1. Confirm `.env.yml` has shared `google.client_id`, `google.client_secret`, and `google.email`.
2. Install if `tools/google-calendar/.venv/Scripts/python.exe` is missing:

   ```powershell
   .\tools\google-auth\install.ps1
   .\tools\google-calendar\install.ps1
   ```

3. If `ping` reports `needs_auth`, ask the user to run `.\tools\google-auth\google-auth.ps1 login`.

## Invocation

Do not write a new script. Use the committed wrappers.

```powershell
.\tools\run-tool\run-tool.ps1 google-calendar commands
.\tools\run-tool\run-tool.ps1 google-calendar ping
.\tools\run-tool\run-tool.ps1 google-calendar upcoming --days 14
.\tools\google-calendar\google-calendar.ps1 list_events --timeMin 2026-08-22T00:00:00-04:00
```

Commands match Calendar MCP names plus `upcoming` (`list_calendars`, `upcoming`, `list_events`, `get_event`, `create_event`, `update_event`, `delete_event`, `search_events`, `suggest_time`, `respond_to_event`). Do not create, update, or delete events unless the user asked for that mutation.
