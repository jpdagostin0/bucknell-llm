---
type: tool
---

# Tool Template

Copy this directory when adding a repository CLI. Do not write a one-off session script.

1. Copy `tools/tool-template/` to `tools/<name>/`.
2. Rename `example-tool.ps1` and `example_tool.py` to the new kebab-case / snake_case names.
3. Replace `CHANGEME` markers in those files.
4. Register the tool in `tools/run-tool/run_tool.py`.
5. Add `skills/<name>/SKILL.md` if agents should auto-select the workflow.

## Contract

- PowerShell wrapper: kebab-case, forwards `@args`, sets `PYTHONPATH` if needed.
- Python CLI: snake_case, prints JSON, accepts `--json`, `--json-file`, and `--flag` arguments.
- Installer: `install.ps1` using `uv` for Python tools.
- Secrets stay in ignored `.env.yml`. Never print them.
- Prefer `--json-file` for arrays so PowerShell cannot eat `[...]`.

## Smoke test

```powershell
.\tools\tool-template\example-tool.ps1 ping
python .\tools\tool-template\example_tool.py ping
.\tools\run-tool\run-tool.ps1 example-tool ping
```
