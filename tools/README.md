---
type: tool-index
---

# Repository Tools

Project-local utilities live here. Keep source wrappers and documentation in Git; keep environments, credentials, generated downloads, and runtime state ignored.

- [Run Tool](run-tool/README.md) — session dispatcher for every CLI. Prefer this over writing a new script.
- [Tool Template](tool-template/README.md) — Python and PowerShell skeleton for a new CLI.

- [Moodle-DL](moodle-dl/README.md) — stage Moodle course content for review.
- [Selenium](selenium/README.md) — local Chrome session for non-Moodle webpages.
- [MarkItDown](markitdown/README.md) — convert trusted local PDFs to temporary Markdown.
- [pypdf](pypdf/README.md) — extract selected homework pages from local textbooks.
- [PyMarkdown](pymarkdown/README.md) — lint and mechanically format Markdown.
- [Flint](flint/README.md) — validate path-specific frontmatter contracts.
- [ls-lint](ls-lint/README.md) — enforce directory and filename conventions.
- [Vault Lint](vault-lint/README.md) — run the three vault linters as one suite.
- [Google Auth](google-auth/README.md) — shared Google OAuth for Drive, Gmail, and Calendar.
- [Google Drive](google-drive/README.md) — MCP-compatible Drive CLI on PyDrive2.
- [Gmail](gmail/README.md) — MCP-compatible Gmail CLI on simplegmail.
- [Google Calendar](google-calendar/README.md) — MCP-compatible Calendar CLI on gcsa.
- [Linear](linear/README.md) — MCP-compatible Linear CLI on @linear/sdk.
- [Gradescope](gradescope/README.md) — unofficial gradescopeapi CLI using cookies from `.env.yml`.
- [Fast Common](fast-common/README.md) — shared library for skill runners.
- [Fast Sync Class](fast-sync-class/README.md) — mechanical Moodle-to-vault class sync.
- [Fast Moodle-DL](fast-moodle-dl/README.md) — Moodle download and inventory without credential access.
- [Fast Selenium](fast-selenium/README.md) — install and ping the Selenium CLI.
- [Fast Fetch Webpage](fast-fetch-webpage/README.md) — capture a non-Moodle URL as ignored HTML, text, and screenshot.
- [Fast MarkItDown](fast-markitdown/README.md) — trusted local PDF conversion with artifact stripping.
- [Fast Get Homework Pages](fast-get-homework-pages/README.md) — unique printed-page extraction.
- [Fast Check Vault](fast-check-vault/README.md) — structured vault lint report.
- [Fast Fix Vault](fast-fix-vault/README.md) — PyMarkdown autofix plus recheck.
- [Fast Clean Vault](fast-clean-vault/README.md) — one check-and-fix cycle.
- [Fast Linear Sync](fast-linear-sync/README.md) — Linear/vault join inspection.
- [Fast Import Syllabus](fast-import-syllabus/README.md) — propose Linear issues from dated syllabus lines.
- [Fast Assign Cycles](fast-assign-cycles/README.md) — map issue due dates to Week NN cycles.
- [Fast Dashboard](fast-dashboard/README.md) — live Linear due work, exams, and weekly load.
- [Fast Weekly Review](fast-weekly-review/README.md) — inbox plus unfinished work; never auto-sets Missed.
- [Fast Scaffold Work Note](fast-scaffold-work-note/README.md) — opt-in work note from a Linear issue key.
- [Fast Linear](fast-linear/README.md) — read-only Linear preflight.
- [Fast Gmail](fast-gmail/README.md) — read-only unread-thread search.
- [Fast Google Drive](fast-google-drive/README.md) — class content-folder listing.
- [Fast Google Calendar](fast-google-calendar/README.md) — upcoming-event listing.
- [Fast Gradescope](fast-gradescope/README.md) — Gradescope course and assignment listing.

Google Drive, Gmail, and Calendar share `google.*` secrets in ignored `.env.yml`. Linear reads `linear.api_key` from the same file. Gradescope reads `gradescope.*` cookies from the same file. Each MCP-compatible CLI accepts MCP tool names plus `--json` or `--flag` arguments and prints JSON. Each `fast-*` runner encodes a skill workflow, prints JSON, and lists remaining judgment under `needs_llm`.
