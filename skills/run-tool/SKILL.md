---
name: run-tool
description: >-
  Invokes repository CLIs through tools/run-tool instead of writing a new
  Python or PowerShell script. Use at the start of a session and whenever
  Linear, Gmail, Drive, Calendar, Gradescope, Moodle, Selenium, MarkItDown, pypdf, Flint,
  ls-lint, PyMarkdown, vault lint, or a fast-* runner is needed.
---

# Run Tool

Do not write a session-local `.py` or `.ps1` to call Linear, Google, Gradescope, Moodle, or vault linters. Use the committed wrappers.

## Dispatcher

```powershell
.\tools\run-tool\run-tool.ps1 commands
.\tools\run-tool\run-tool.ps1 linear ping
.\tools\run-tool\run-tool.ps1 linear save_issue --json-file .\payload.json
.\tools\run-tool\run-tool.ps1 google-drive search_files --query "title contains 'ECEG-210'"
.\tools\run-tool\run-tool.ps1 fast-linear --class "MATH 212"
```

```text
python tools/run-tool/run_tool.py commands
python tools/run-tool/run_tool.py gmail ping
```

Put JSON arrays and objects in `--json-file`. PowerShell treats `'["uuid"]'` as an array expression.

This vault runs on Windows PowerShell. Invoke tools with the wrappers below. Do not wrap PowerShell cmdlets in `bash -c`. Do not use pyodide, Pyodide, or any emulated Python; `run_tool.py` must run under a real `python.exe` so it can spawn subprocesses.

Discover commands from JSON, not argparse prose:

```powershell
.\tools\run-tool\run-tool.ps1 commands
.\tools\run-tool\run-tool.ps1 google-calendar commands
.\tools\run-tool\run-tool.ps1 google-calendar upcoming --days 14
.\tools\run-tool\run-tool.ps1 gmail get_thread --threadId THREAD_ID
.\tools\run-tool\run-tool.ps1 gmail get_message --messageId MESSAGE_ID
.\tools\run-tool\run-tool.ps1 read_file_lines courses/MATH-212-Differential-Equations-Fall-2026/MATH-212.md 1 35
```

```text
python tools/run-tool/run_tool.py google-calendar --help
python tools/run-tool/run_tool.py google-calendar upcoming --days 14
```

## Per-tool wrappers

| Tool | PowerShell | Python |
|------|------------|--------|
| linear | `.\tools\linear\linear.ps1` | `python tools/linear/linear.py` |
| gmail | `.\tools\gmail\gmail.ps1` | `.\tools\gmail\.venv\Scripts\python.exe tools/gmail/gmail.py` |
| google-drive | `.\tools\google-drive\google-drive.ps1` | Drive venv + `google_drive.py` |
| google-calendar | `.\tools\google-calendar\google-calendar.ps1` | Calendar venv + `google_calendar.py` |
| google-auth | `.\tools\google-auth\google-auth.ps1` | Auth venv + `google_auth.py` |
| moodle-dl | `.\tools\moodle-dl\moodle-dl.ps1` | `python tools/moodle-dl/moodle_dl.py` |
| selenium | `.\tools\selenium\selenium.ps1` | selenium venv + `selenium_cli.py` |
| markitdown | `.\tools\markitdown\markitdown.ps1` | `python tools/markitdown/markitdown.py` |
| pypdf | `.\tools\pypdf\extract-pages.ps1` | pypdf venv + `extract_pages.py` |
| flint | `.\tools\flint\flint.ps1` | `python tools/flint/flint.py` |
| ls-lint | `.\tools\ls-lint\ls-lint.ps1` | `python tools/ls-lint/ls_lint.py` |
| pymarkdown | `.\tools\pymarkdown\pymarkdown.ps1` | `python tools/pymarkdown/pymarkdown.py` |
| vault-lint | `.\tools\vault-lint\check.ps1` | `validate_vault.py` via run-tool `vault-lint` |
| gradescope | `.\tools\gradescope\gradescope.ps1` | gradescope venv + `gradescope.py` |
| read_file_lines | `.\tools\read-file-lines\read-file-lines.ps1` | `python tools/read-file-lines/read_file_lines.py` |
| fast-* | `.\tools\fast-<name>\fast-<name>.ps1` | matching `fast_*.py` |

Prefer `tools/fast-<skill>/` for skill workflows. Prefer these CLIs over MCP. Never read `.env.yml` or Moodle state.

New CLIs start from `tools/tool-template/`. Workflow judgment remains in `skills/<name>/SKILL.md`.
