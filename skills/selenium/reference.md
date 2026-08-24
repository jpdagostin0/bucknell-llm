---
type: skill-reference
---

# Selenium Reference

Upstream: [PhungXuanAnh/selenium-mcp-server](https://github.com/PhungXuanAnh/selenium-mcp-server), published as `mcp-server-selenium==0.1.8`.

## Commands

```powershell
.\tools\selenium\install.ps1
.\tools\selenium\selenium.ps1 commands
.\tools\selenium\selenium.ps1 ping
.\tools\selenium\selenium.ps1 fetch --url "https://example.com"
.\tools\selenium\selenium.ps1 navigate --url "https://example.com" --wait_until complete
.\tools\selenium\selenium.ps1 tabs --action list
.\tools\selenium\selenium.ps1 stop
```

Put selector objects and other JSON mappings in `--json-file`.

## Local paths

- `.venv/`: ignored `uv` environment.
- `state/chrome-profile`: ignored Chrome user data directory.
- `output/pages/`: ignored HTML and text captures.
- `output/screenshots/`: ignored PNG captures.
- `output/downloads/`: ignored Chrome downloads.

## Compact workflow

`tabs(list)` -> `navigate` -> `wait_for` -> `query_elements` -> `interact_element` -> `take_screenshot`
