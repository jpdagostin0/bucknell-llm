---
type: skill-reference
---

# Moodle-DL Reference

Upstream: [C0D3D3V/Moodle-DL](https://github.com/C0D3D3V/Moodle-DL)

The local installer uses `uv` to install the published release `2.3.13` in an isolated Python 3.12 environment. It does not clone or vendor the upstream repository.

## Commands

Run commands from the vault root:

```powershell
# Install or repair
.\tools\moodle-dl\install.ps1

# Show upstream options
.\tools\moodle-dl\moodle-dl.ps1 --help

# First-time SSO setup
.\tools\moodle-dl\moodle-dl.ps1 --init --sso

# Refresh an expired token
.\tools\moodle-dl\moodle-dl.ps1 --new-token --sso

# Change course and download settings
.\tools\moodle-dl\moodle-dl.ps1 --config

# Download new or changed content
.\tools\moodle-dl\moodle-dl.ps1
```

## Local paths

- `.venv/`: ignored `uv` virtual environment.
- `state/config.json`: ignored configuration containing the Moodle token.
- `state/`: ignored raw download and runtime staging area.
- `attachments/`: reviewed, retained binary references only.

## Troubleshooting

- If `uv` is unavailable in PowerShell, install or expose `uv` on `PATH`, then rerun the installer.
- If login uses Shibboleth or another browser-based flow, include `--sso`.
- If the token is rejected, use `--new-token --sso`; do not expose the token while diagnosing.
- If the Moodle mobile API is disabled by the institution, Moodle-DL cannot connect through its supported API.
