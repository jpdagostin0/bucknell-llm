---
name: gradescope
description: >-
  Calls the repository-local Gradescope CLI (gradescopeapi) using cookies from
  ignored .env.yml. Use when listing Gradescope courses or assignments, checking
  deadlines, or uploading a submission the user explicitly requested.
---

# Gradescope

## Fast path

```powershell
.\tools\fast-gradescope\fast-gradescope.ps1
.\tools\fast-gradescope\fast-gradescope.ps1 --class "MATH 212"
.\tools\fast-gradescope\fast-gradescope.ps1 assignments --class "MATH 212"
```

The runner is read-only by default. It lists courses (and assignments when a class or course id is given) without opening `.env.yml`. Remaining Linear import judgment is under `needs_llm`.

Prefer `tools/gradescope/` over any Gradescope MCP or a session script.

## Safety

- Never read, print, summarize, transmit, or commit `.env.yml` or Gradescope cookie values.
- Never ask the user to paste Gradescope cookies or a school password into chat.
- Do not upload submissions, edit due dates, or change extensions unless the user asked for that mutation.
- Do not copy Gradescope due dates, grades, or status into vault frontmatter. Linear owns those fields.
- Deadline-bearing assignments require an explicit Linear import review before issue creation.

## Setup

1. Confirm ignored `.env.yml` has a `gradescope` mapping with `_gradescope_session` and any companion cookies such as `remember_me` and `signed_token`.
2. Install if `tools/gradescope/.venv/Scripts/python.exe` is missing:

   ```powershell
   .\tools\gradescope\install.ps1
   ```

3. If `ping` reports unauthorized cookies, ask the user to refresh the Gradescope cookies in `.env.yml` from a logged-in browser session.

## Invocation

Do not write a new script. Use the committed wrappers.

```powershell
.\tools\run-tool\run-tool.ps1 gradescope commands
.\tools\run-tool\run-tool.ps1 gradescope ping
.\tools\gradescope\gradescope.ps1 get_courses
.\tools\gradescope\gradescope.ps1 get_assignments --courseId 123456
```

`upload_assignment` requires `--courseId`, `--assignmentId`, and local `--files`. Put file arrays in `--json-file`.
