---
type: tool
invoke: false
---

# Tool Template

Copy this directory when adding a repository CLI. Never write a one-off session script.

1. Copy `tools/tool_template/` to `tools/<name>/`.
2. Rename `example_tool.py` to snake_case `<name>.py`.
3. Replace `CHANGEME` markers.
4. A tool named `<name>` with `tools/<name>/<name>.py` and `type: tool` is auto-registered. Register unusual launchers in `tools/run_tool/run_tool.py`.
5. Add `skills/<name>/SKILL.md` if agents should auto-select the workflow.
6. Run `python tools/run_tool/run_tool.py fast_index_repo --apply`. Never hand-edit `tools/README.md`, `skills/README.md`, or generated `AGENTS.md` / `Home.md` regions.

Always use flags. Never invent `--json` when flags work. Nested JSON only when the CLI requires it.

```text
python tools/run_tool/run_tool.py example_tool commands
python tools/run_tool/run_tool.py example_tool ping
```
