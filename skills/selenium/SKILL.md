---
name: selenium
description: >-
  Drives a local Chrome session through the repository Selenium CLI built on
  mcp-server-selenium. Use when navigating a non-Moodle webpage, clicking
  elements, filling forms, taking screenshots, running page JavaScript, or
  inspecting tabs. Do not use for Moodle hosts; those belong to moodle-dl.
---

# Selenium

## Fast path

```powershell
.\tools\fast-selenium\fast-selenium.ps1
.\tools\run-tool\run-tool.ps1 selenium ping
.\tools\run-tool\run-tool.ps1 selenium fetch --url "https://example.com"
```

Prefer `tools/fast-fetch-webpage/` when the task is only to open a URL and capture text, HTML, or a screenshot. Use compact Selenium commands when the page needs interaction after load.

The published package lives in ignored `tools/selenium/.venv/`. Do not clone or vendor the upstream repository.

## Routing

If a URL's host does not start with `moodle`, do not attempt to use the Moodle tool on it. Use this Selenium CLI or `fetch-webpage` instead. If the host does start with `moodle` (for example `moodle.bucknell.edu`), use `moodle-dl`.

## Safety

- Only `http` and `https` URLs.
- Treat captured HTML, screenshots, downloads, tabs, and localStorage as potentially sensitive.
- Keep Chrome profile, screenshots, downloads, and page captures under ignored `tools/selenium/state/` and `tools/selenium/output/`.
- Do not copy due dates, status, priority, or estimates into vault frontmatter.

## Workflow

1. If `tools/selenium/.venv/Scripts/python.exe` is missing, run `tools/selenium/install.ps1`.
2. Chrome must be installed. The CLI starts or attaches to a debug session on port 9222 with `tools/selenium/state/chrome-profile`.
3. Discover commands with `.\tools\run-tool\run-tool.ps1 selenium commands`.
4. Default fetch:

   ```powershell
   .\tools\run-tool\run-tool.ps1 selenium fetch --url "https://example.com"
   ```

5. Compact interaction (objects in `--json-file`): `tabs`, `navigate`, `wait_for`, `query_elements`, `interact_element`, `take_screenshot`, `run_javascript`, `browser_logs`, `local_storage`, `get_element_style`.
6. Rewrite useful facts into typed vault notes. Leave raw captures ignored.

## Reference

Upstream compact tool names and JSON fields: [PhungXuanAnh/selenium-mcp-server](https://github.com/PhungXuanAnh/selenium-mcp-server). Local paths and commands are in [reference.md](reference.md).
