---
type: tool
---

# Google Auth

Shared OAuth helper for the Drive, Gmail, and Calendar CLIs. Secrets live in the ignored vault-root `.env.yml`; the refresh token is stored under ignored `state/`.

## Install

```powershell
.\tools\google-auth\install.ps1
```

## Login

Fill `google.client_id` and `google.client_secret` in `.env.yml`, then:

```powershell
.\tools\google-auth\google-auth.ps1 login
```

One desktop OAuth client is shared across Drive, Gmail, and Calendar. The login command requests all three APIs in a single consent screen.

## Commands

JSON in, JSON out. Command names match the local wrappers' `ping` / `commands` surface.

```powershell
.\tools\google-auth\google-auth.ps1 commands
.\tools\google-auth\google-auth.ps1 ping
```
