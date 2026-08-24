---
name: google-drive
description: Calls the repository-local Google Drive CLI (PyDrive2) with MCP-compatible command names. Use instead of Drive MCP when inspecting course folders, downloading files, or searching Drive content.
---

# Google Drive

## Fast path

```powershell
.\tools\fast-google-drive\fast-google-drive.ps1 --class "MATH 245"
```

The runner lists a class `content` folder or recent files. `download --fileId ... --class ... --apply` retains a Drive file in `attachments/`.

Prefer `tools/google-drive/` over Drive MCP.

## Setup

1. Confirm `.env.yml` has shared `google.client_id` and `google.client_secret`.
2. Install if `tools/google-drive/.venv/Scripts/python.exe` is missing:

   ```powershell
   .\tools\google-auth\install.ps1
   .\tools\google-drive\install.ps1
   ```

3. If `ping` reports `needs_auth`, ask the user to run `.\tools\google-auth\google-auth.ps1 login`.

## Invocation

Do not write a new script. Use the committed wrappers. Put JSON in `--json-file`.

```powershell
.\tools\run-tool\run-tool.ps1 google-drive commands
.\tools\run-tool\run-tool.ps1 google-drive ping
.\tools\google-drive\google-drive.ps1 search_files --query "title contains 'MATH-212'"
```

Commands match Drive MCP names (`search_files`, `get_file_metadata`, `read_file_content`, `download_file_content`, `create_file`, `copy_file`, `update_file`, `share_file`, `trash_file`, `list_recent_files`, `get_file_permissions`). Pass camelCase or snake_case arguments as flags or `--json`.

Review downloaded files before retaining them. Prefix retained binaries with the course code and put them in `attachments/` or the course `textbooks/` directory.
