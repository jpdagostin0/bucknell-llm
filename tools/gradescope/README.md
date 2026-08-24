---
type: tool
---

# Gradescope

Repository-local wrapper for the unofficial [gradescopeapi](https://github.com/nyuoss/gradescope-api) library, pinned to `gradescopeapi==1.8.1`. Authenticates with browser cookies from ignored `.env.yml` so school SSO passwords never enter the vault tools.

## Install

```powershell
.\tools\gradescope\install.ps1
```

The installer uses `uv` and does not clone or vendor the upstream repository.

## Secrets

Keep cookies under `gradescope` in `.env.yml`. Typical keys:

```yaml
gradescope:
  _gradescope_session: ...
  remember_me: ...
  signed_token: ...
```

Never read, print, transmit, or commit that file. Agents must call this CLI instead of opening `.env.yml`.

## Commands

```powershell
.\tools\gradescope\gradescope.ps1 commands
.\tools\gradescope\gradescope.ps1 ping
.\tools\gradescope\gradescope.ps1 get_courses
.\tools\gradescope\gradescope.ps1 get_assignments --courseId 123456
```

`upload_assignment` and `get_course_users` are mutations or staff-only. Do not run them unless the user asked.
