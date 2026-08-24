---
type: tool
---

# Fast Fetch Webpage

Opens a non-Moodle http(s) URL in the local Selenium Chrome session, then writes ignored HTML, text, and an optional screenshot. Remaining note rewriting is `needs_llm`.

```powershell
.\tools\fast-fetch-webpage\fast-fetch-webpage.ps1 --url "https://example.com"
```

If the URL host starts with `moodle`, this runner refuses and Moodle-DL must be used instead.
