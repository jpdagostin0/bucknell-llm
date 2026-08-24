# ls-lint

Repository-local [ls-lint](https://github.com/loeffel-io/ls-lint) binary for enforcing vault directory and filename conventions.

## Install

```powershell
.\tools\ls-lint\install.ps1
```

The installer downloads the pinned Windows release with GitHub CLI and keeps the binary under ignored `bin/`.

## Run

```powershell
.\tools\ls-lint\ls-lint.ps1 --config .ls-lint.yml --workdir .
```

The root `.ls-lint.yml` encodes course folders, week notes, work notes, textbooks, attachments, tools, and skills naming rules.
