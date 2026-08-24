---
type: tool
---

# Fast Get Homework Pages

Resolves the course textbook, extracts cited printed pages when the range is unique, and never guesses a page offset.

JSON in, JSON out. The default command is `run`. Items the runner will not guess are listed under `needs_llm`.

```powershell
.\tools\fast-get-homework-pages\fast-get-homework-pages.ps1 --class "MATH 212" --homework ".\attachments\MATH-212 Homework-01 Section-1-1.pdf"
```
