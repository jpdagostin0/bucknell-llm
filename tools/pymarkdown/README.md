# PyMarkdown

Repository-local [PyMarkdown](https://github.com/jackdewinter/pymarkdown) installation for checking and mechanically formatting Markdown.

## Install

```powershell
.\tools\pymarkdown\install.ps1
```

The installer uses `uv` and keeps the environment under ignored `.venv/`.

## Run

```powershell
.\tools\pymarkdown\pymarkdown.ps1 --config .pymarkdown.yml scan --recurse --respect-gitignore .
.\tools\pymarkdown\pymarkdown.ps1 --config .pymarkdown.yml fix --recurse --respect-gitignore .
```

The root `.pymarkdown.yml` enables Obsidian-compatible frontmatter and Markdown extensions.
