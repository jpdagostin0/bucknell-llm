---
name: gmail
description: Calls the repository-local Gmail CLI (simplegmail) with MCP-compatible command names. Use instead of Gmail MCP when searching mail, reading threads, or drafting messages.
---

# Gmail

## Fast path

```powershell
.\tools\fast-gmail\fast-gmail.ps1
.\tools\fast-gmail\fast-gmail.ps1 --query "from:sej010 newer_than:14d"
```

The runner lists unread threads from the last seven days. `get`, `send`, `reply`, `draft`, `trash`, and `label` cover the rest of the Gmail workflow.

Prefer `tools/gmail/` over Gmail MCP.

## Setup

1. Confirm `.env.yml` has shared `google.client_id` and `google.client_secret`.
2. Install if `tools/gmail/.venv/Scripts/python.exe` is missing:

   ```powershell
   .\tools\google-auth\install.ps1
   .\tools\gmail\install.ps1
   ```

3. If `ping` reports `needs_auth`, ask the user to run `.\tools\google-auth\google-auth.ps1 login`.

## Invocation

Do not write a new script. Use the committed wrappers.

```powershell
.\tools\run-tool\run-tool.ps1 gmail commands
.\tools\run-tool\run-tool.ps1 gmail ping
.\tools\gmail\gmail.ps1 search_threads --query "is:unread newer_than:7d" --pageSize 10
.\tools\gmail\gmail.ps1 get_thread --threadId THREAD_ID
.\tools\gmail\gmail.ps1 get_message --messageId MESSAGE_ID
```

Commands match Gmail MCP names (`search_threads`, `get_thread`, `get_message`, `list_labels`, `list_drafts`, `create_draft`, `send_message`, `reply`, `label_message`, `trash_message`). `get_thread` and `get_message` take `--threadId` / `--messageId` (or `--id`). Do not send, trash, or relabel mail unless the user asked for that mutation.
