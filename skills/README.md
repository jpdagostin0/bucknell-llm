---
type: skill-index
---

# Repository Skills

Project-specific agent workflows live in one directory per skill. Each skill has a matching `tools/fast-<skill>/` runner that performs the mechanical steps and returns remaining judgment as `needs_llm`. Call CLIs through `tools/run-tool/` instead of writing a session script.

- [Run Tool](run-tool/SKILL.md) — invoke every repository CLI from Python or PowerShell without a new script.

- [Moodle-DL](moodle-dl/SKILL.md) — download and review Moodle course content safely. Fast: `tools/fast-moodle-dl/`.
- [Selenium](selenium/SKILL.md) — drive a local Chrome session for non-Moodle sites. Fast: `tools/fast-selenium/`.
- [Fetch Webpage](fetch-webpage/SKILL.md) — capture HTML, text, and screenshots from a non-Moodle URL. Fast: `tools/fast-fetch-webpage/`.
- [MarkItDown](markitdown/SKILL.md) — convert trusted local PDFs to temporary Markdown. Fast: `tools/fast-markitdown/`.
- [Get Homework Pages](get-homework-pages/SKILL.md) — extract cited textbook pages for an assignment. Fast: `tools/fast-get-homework-pages/`.
- [Linear](linear/SKILL.md) — call the local Linear CLI instead of Linear MCP. Fast: `tools/fast-linear/`.
- [Linear Sync](linear-sync/SKILL.md) — reconcile obligations and retained prose across Linear and Obsidian. Fast: `tools/fast-linear-sync/`.
- [Import Syllabus](import-syllabus/SKILL.md) — propose Linear issues from dated syllabus lines. Fast: `tools/fast-import-syllabus/`.
- [Assign Cycles](assign-cycles/SKILL.md) — assign Week NN cycles from due dates. Fast: `tools/fast-assign-cycles/`.
- [Dashboard](dashboard/SKILL.md) — read live Linear due work, exams, and weekly load. Fast: `tools/fast-dashboard/`.
- [Weekly Review](weekly-review/SKILL.md) — classify inbox and unfinished work without mutating Linear. Fast: `tools/fast-weekly-review/`.
- [Scaffold Work Note](scaffold-work-note/SKILL.md) — create an assignment note from a Linear key. Fast: `tools/fast-scaffold-work-note/`.
- [Google Drive](google-drive/SKILL.md) — call the local Drive CLI instead of Drive MCP. Fast: `tools/fast-google-drive/`.
- [Gmail](gmail/SKILL.md) — call the local Gmail CLI instead of Gmail MCP. Fast: `tools/fast-gmail/`.
- [Google Calendar](google-calendar/SKILL.md) — call the local Calendar CLI instead of Calendar MCP. Fast: `tools/fast-google-calendar/`.
- [Gradescope](gradescope/SKILL.md) — list Gradescope courses and assignments with cookies from `.env.yml`. Fast: `tools/fast-gradescope/`.
- [Sync Class](sync-class/SKILL.md) — synchronize Moodle content into the standard course-note structure. Fast: `tools/fast-sync-class/`.
- [Check Vault](check-vault/SKILL.md) — report Markdown, frontmatter, and naming violations without edits. Fast: `tools/fast-check-vault/`.
- [Fix Vault](fix-vault/SKILL.md) — repair reported violations while preserving links and ownership boundaries. Fast: `tools/fast-fix-vault/`.
- [Clean Vault](clean-vault/SKILL.md) — run the complete check-and-fix cycle. Fast: `tools/fast-clean-vault/`.
