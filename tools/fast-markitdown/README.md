---
type: tool
---

# Fast MarkItDown

Converts a trusted local PDF to ignored Markdown and strips repeated page-number artifacts. Note rewriting remains an LLM step.

JSON in, JSON out. The default command is `run`. Items the runner will not guess are listed under `needs_llm`.

```powershell
.\tools\fast-markitdown\fast-markitdown.ps1 --input ".\attachments\MATH-245 Syllabus Fall 2026.pdf" --class "MATH 245"
```
