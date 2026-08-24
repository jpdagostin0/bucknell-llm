---
type: tool
---

# Run Tool

Session entry point for every repository CLI. Agents should call this instead of writing a new Python or PowerShell script.

```powershell
.\tools\run-tool\run-tool.ps1 commands
.\tools\run-tool\run-tool.ps1 linear ping
.\tools\run-tool\run-tool.ps1 linear save_issue --json-file .\payload.json
.\tools\run-tool\run-tool.ps1 google-drive search_files --query "title contains 'ECEG-210'"
```

```text
python tools/run-tool/run_tool.py commands
python tools/run-tool/run_tool.py gmail ping
```

JSON arrays and objects must travel through `--json-file`. Do not pass `--labelIds '["uuid"]'` on a PowerShell command line.

This vault runs on Windows PowerShell. Use `.\tools\run-tool\run-tool.ps1` or a real `python.exe`. Do not wrap PowerShell cmdlets in `bash -c`. Do not use pyodide or an emulated interpreter.

Discover a tool's commands with JSON:

```powershell
.\tools\run-tool\run-tool.ps1 google-calendar commands
.\tools\run-tool\run-tool.ps1 google-calendar upcoming --days 14
.\tools\run-tool\run-tool.ps1 read_file_lines <path> [start] [end]
```

Each tool also has a same-directory launcher (`tools/linear/linear.py`, `tools/gmail/gmail.ps1`, and so on). Those call the same programs this dispatcher uses.

To add a new CLI, copy `tools/tool-template/` and register the tool in `run_tool.py`.
