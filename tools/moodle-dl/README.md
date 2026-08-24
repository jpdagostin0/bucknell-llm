---
type: tool
---

# Moodle-DL

Repository-local wrapper for [C0D3D3V/Moodle-DL](https://github.com/C0D3D3V/Moodle-DL), pinned to release `2.3.13`.

## Install

From the vault root:

```powershell
.\tools\moodle-dl\install.ps1
```

The installer uses `uv` to create an isolated Python 3.12 environment under `.venv/` and installs the published `moodle-dl==2.3.13` package. It does not clone or vendor the upstream Git repository.

## Initialize

Moodle-DL stores its token and configuration in the ignored `state/` directory. Run the interactive setup yourself so credentials never enter chat or command logs:

```powershell
.\tools\moodle-dl\moodle-dl.ps1 --init --sso
```

Omit `--sso` only when the Moodle instance uses a normal Moodle login.

## Sync

```powershell
.\tools\moodle-dl\moodle-dl.ps1
```

Subsequent runs download only new or changed Moodle content. Raw downloads remain staging material in `state/`; they are not automatically part of the Obsidian vault.

## Vault boundary

- Never commit or display `state/config.json`, tokens, private tokens, or cookies.
- Review downloaded material before retaining it.
- Copy retained binary references into the flat `attachments/` directory and prefix filenames with the course code.
- Keep prose and synthesis in course notes.
- Send discovered deadlines and obligations to Linear rather than copying mutable fields into note frontmatter.
