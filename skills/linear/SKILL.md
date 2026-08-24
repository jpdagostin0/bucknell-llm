---
name: linear
description: Calls the repository-local Linear CLI (@linear/sdk) with MCP-compatible command names. Use instead of Linear MCP when inspecting teams, projects, issues, cycles, or comments. For vault-to-Linear ownership rules, also follow linear-sync.
---

# Linear

## Fast path

```powershell
.\tools\fast-linear\fast-linear.ps1
.\tools\fast-linear\fast-linear.ps1 issues --class "MATH 212"
```

The runner is read-only preflight by default. `issues`, `save`, and `comment` cover class-filtered lists and Linear mutations.

Prefer `tools/linear/` over Linear MCP. Read `skills/linear-sync/SKILL.md` before creating or updating coursework issues.

## Setup

1. Confirm `.env.yml` has `linear.api_key`.
2. Install if `tools/linear/node_modules/@linear/sdk` is missing:

   ```powershell
   .\tools\linear\install.ps1
   ```

## Invocation

Do not write a new script. Use the committed wrappers and `--json-file` for arrays.

```powershell
.\tools\run-tool\run-tool.ps1 linear commands
.\tools\run-tool\run-tool.ps1 linear ping
.\tools\run-tool\run-tool.ps1 linear list_issues --limit 10 --team JPS
.\tools\linear\linear.ps1 get_issue --id JPS-5
python tools/linear/linear.py ping
```

Commands match Linear MCP names used by this vault (`list_teams`, `list_projects`, `list_issues`, `get_issue`, `save_issue`, `list_cycles`, `list_milestones`, `list_comments`). Inspect current data before mutation. Never copy `status`, `due`, `priority`, or `estimate` into vault frontmatter.
