---
type: tool
---

# Selenium

Repository-local wrapper for the published [`mcp-server-selenium`](https://github.com/PhungXuanAnh/selenium-mcp-server) package, pinned to `0.1.8`. Agents call this CLI through `tools/run-tool/` instead of Selenium MCP.

The installer uses `uv` to create an isolated Python 3.12 environment under `.venv/` and installs `mcp-server-selenium==0.1.8` with `mcp[cli]<2` (MCP 2.0 removed `FastMCP`, which this package still imports). It does not clone or vendor the upstream Git repository.

## Install

```powershell
.\tools\selenium\install.ps1
```

## Commands

```powershell
.\tools\selenium\selenium.ps1 commands
.\tools\selenium\selenium.ps1 ping
.\tools\selenium\selenium.ps1 fetch --url "https://example.com"
.\tools\selenium\selenium.ps1 navigate --url "https://example.com" --wait_until complete
.\tools\selenium\selenium.ps1 tabs --action list
.\tools\selenium\selenium.ps1 stop
```

`fetch` writes ignored HTML, text, and an optional screenshot. Compact MCP names (`wait_for`, `query_elements`, `interact_element`, `take_screenshot`, `run_javascript`, `browser_logs`, `local_storage`, `get_element_style`) accept the same JSON fields as the upstream compact profile. Put objects in `--json-file`.

## Routing

Moodle-DL is only for Moodle hosts whose hostname starts with `moodle` (for example `moodle.bucknell.edu`). If a URL's host does not start with `moodle`, do not use the Moodle tool on it. `fetch` refuses Moodle URLs.
