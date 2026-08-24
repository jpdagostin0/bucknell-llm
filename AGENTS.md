# Fall 2026 Coursework Vault

This repository is the Obsidian half of a single-semester coursework system. Linear owns obligations and mutable state; this vault owns prose, reference material, and understanding. Optimize every change for one student operating one Fall 2026 term.

## Source of truth

- Linear owns due dates, workflow state, priority, estimates, cycle assignment, and coarse grade labels.
- The vault owns syllabi, grading breakdowns, lecture notes, derivations, drafts, study synthesis, and feedback artifacts.
- The LMS or registrar remains authoritative for enrollment, scores, and final grades.
- Never duplicate mutable Linear fields in note frontmatter. A stale copy is worse than no copy.
- Join a work note to Linear with the stable issue key (`linear: FA26-214`) and, when useful, `linear_url`.
- Treat a missing work note as normal. Create notes only when there is prose worth retaining.

## Fixed ontology

- One Linear team represents Fall 2026 and uses weekly cycles named `Week NN`.
- One Linear project represents each enrolled course.
- Project milestones represent syllabus units, midterms, and finals.
- Issues represent atomic obligations; large deliverables use parent issues and sub-issues.
- Linear triage accepts new items with deadlines. `inbox/` accepts content without deadlines.
- Linear comments contain short factual state logs. Subject-matter thinking belongs in the vault.
- Project updates are weekly per-course reviews.

Do not introduce term, degree, daily-note, or per-unit layers. Do not use a Linear project to represent a student “project”; that remains a parent issue.

## Target vault layout

```text
Home.md
inbox/
courses/
  <DEPT>-<NUM>-<Title-Words>-Fall-2026/
    <DEPT>-<NUM>.md
    Syllabus.md
    textbooks/
      <DEPT>-<NUM> <Book-Title> <Edition>.pdf
    notes/
      Week-NN.md
    work/
      <DEPT>-<NUM> <Item> <slug>.md
templates/
attachments/
tools/
  <tool-name>/
skills/
  <skill-name>/
    SKILL.md
```

Keep general-purpose binaries in flat `attachments/` and prefix filenames with the course code. Full-length textbooks are the exception: store them one level below the owning course in `textbooks/`, also with a course-code prefix. Keep the term suffix on course folders so they remain self-describing when archived.

## Where to open notes

Start from `Home.md`. Its course links already use the real paths. Do not invent filenames from spoken course codes.

The catalog `code` is spaced (`MATH 212`). Folders and class-index files always use a hyphen (`MATH-212`). Never open `MATH 212.md`.

| What | Path | Not |
|------|------|-----|
| Term dashboard | `Home.md` | a per-course dashboard |
| Weekly meeting schedule | `classes.md` (vault root only) | `courses/.../classes.md` |
| Class index | `courses/<DEPT>-<NUM>-<Title-Words>-Fall-2026/<DEPT>-<NUM>.md` | `MATH 212.md`, `MATH245.md` |
| Syllabus | `courses/<DEPT>-<NUM>-<Title-Words>-Fall-2026/Syllabus.md` | a class-index filename |
| Week note | `courses/<DEPT>-<NUM>-<Title-Words>-Fall-2026/notes/Week-NN.md` | a per-lecture file |
| Work note | `courses/<DEPT>-<NUM>-<Title-Words>-Fall-2026/work/<DEPT>-<NUM> <Item> <slug>.md` | a class index |

Examples that exist:

```text
courses/MATH-212-Differential-Equations-Fall-2026/MATH-212.md
courses/MATH-245-Linear-Algebra-Fall-2026/MATH-245.md
courses/CSCI-204-Data-Structures-Algorithms-Fall-2026/CSCI-204.md
courses/ECEG-200-Individual-Development-Fall-2026/ECEG-200.md
courses/ECEG-210-Circuits-Signals-Systems-Theory-1-Fall-2026/ECEG-210.md
courses/ECEG-241-Foundations-of-Digital-Systems-Fall-2026/ECEG-241.md
```

`classes.md` is the term meeting grid. Course facts live on the class index. Due dates live in Linear; refresh `Home.md` with `tools/fast-dashboard/` instead of copying them. A missing work note is normal. If a path 404s, glob `courses/<DEPT>-<NUM>-*/<DEPT>-<NUM>.md` rather than substituting a space.

Read a note by line range with `read_file_lines` (also registered as `read-file-lines`):

```powershell
.\tools\run-tool\run-tool.ps1 read_file_lines courses/MATH-212-Differential-Equations-Fall-2026/MATH-212.md 1 35
```

## Organization plan

Implement or maintain the vault in this order:

1. Create the root folders, `Home.md`, and five templates: class index, syllabus, week, assignment, and parent deliverable.
2. For each enrolled course, create the course folder, class index, and `Syllabus.md`; then link the class index from `Home.md`.
3. Record stable syllabus facts in the class index: course code, title, credits, instructor, office hours, meeting pattern, grading breakdown, and unit headings.
4. Link the class index to its Linear project. Keep the Linear project description to a short vault pointer rather than copying vault prose.
5. Decompose each syllabus in Linear into dated milestones and issues. Assign each issue a course, due date, kind label, estimate, and applicable weekly cycle.
6. Create `Week-NN.md` only for weeks with course content. Put individual meetings under dated headings rather than making per-lecture files.
7. Create work notes on demand and link them bidirectionally with their Linear issues.
8. Configure `Home.md` as the term dashboard: class links plus queried due work, exam dates, and weekly estimate totals. Queries must read Linear rather than copied frontmatter.
9. During weekly review, empty `inbox/`, update course health in Linear, re-estimate open work, and explicitly roll, miss, or excuse unfinished issues.

## Current implementation state

As of 2026-08-21:

- The root vault scaffold, `Home.md`, `classes.md`, five templates, `inbox/`, and flat `attachments/` directory exist.
- Obsidian's core Templates plugin uses `templates/`, and new attachments default to `attachments/`.
- Course folders, class indexes, syllabus scaffolds, `notes/`, and `work/` exist for MATH 212, MATH 245, CSCI 204, ECEG 200, ECEG 210, and ECEG 241.
- Each class index links to its corresponding Linear project. The six projects run from 2026-08-24 through 2026-12-18 and contain only a vault pointer.
- The existing Linear team `JP's Workspace` currently represents Fall 2026. It still needs to be renamed to `Fall 2026` manually.
- Linear has a team-scoped `Kind` label group with `pset`, `reading`, `lab`, `quiz`, `exam`, `course project`, `study`, and `admin`. Linear reserves the exact label name `project`, so `course project` is the canonical substitute.
- MATH 212 and MATH 245 have imported instructor syllabi, stable course facts, retained Week 01 materials, and `Week-01.md` syntheses. Other `Syllabus.md` files remain catalog-linked scaffolds.
- No full syllabus milestone or issue import has been performed. MATH 212 and MATH 245 Homework 01 exist as reviewed exceptions; import remaining obligations only after explicit syllabus review.
- Weekly `Week NN` cycles and the `Submitted`, `Graded`, `Blocked`, `Excused`, and `Missed` statuses still require manual Linear configuration.
- The four default Linear onboarding issues remain untouched.
- `tools/moodle-dl/` provides an ignored, repository-local Moodle-DL runtime, and `skills/moodle-dl/` defines the corresponding agent workflow.
- `tools/selenium/` provides an ignored, repository-local `mcp-server-selenium` runtime. `skills/selenium/` and `skills/fetch-webpage/` cover browser automation and non-Moodle page capture.
- `tools/markitdown/` and `skills/markitdown/` provide local PDF extraction; `skills/sync-class/` composes both tools into the standard end-to-end class import.
- `tools/pypdf/` and `skills/get-homework-pages/` extract the smallest cited textbook page range into ignored temporary output.
- `skills/linear-sync/` defines ownership-preserving bidirectional synchronization between Linear obligations and retained Obsidian content.
- Each skill has a `tools/fast-<skill>/` runner that performs the mechanical workflow without an LLM and reports remaining judgment as `needs_llm`.
- PyMarkdown, Flint, and ls-lint are installed through repository-local wrappers. Flint carries the declarative frontmatter policy; `tools/vault-lint/validate_vault.py` enforces typed schemas, exact fields, scope, link resolution, and cross-note invariants that Flint cannot express. Negative controls run with every combined check.
- MATH 212 and MATH 245 each have a course-level `textbooks/` directory linked from the class index and syllabus.
- MATH 212 Homework 01 is Linear issue `JPS-6`; MATH 245 Homework 01 is `JPS-5`. Their Week 01 notes link back to the issues.

## Frontmatter contracts

Use these keys and omit empty optional keys when practical:

```yaml
# Assignment or parent deliverable
type: assignment
linear: FA26-214
linear_url: https://linear.app/...
class: "[[CS-2110]]"
kind: pset
parent: "[[CS-2110 Term-paper]]"
worked:
  - "[[Week-03]]"
```

```yaml
# Weekly course note
type: week
class: "[[CS-2110]]"
week: 3
lectures:
  - 2026-09-14
unit: Unit 2 — Trees & Graphs
```

```yaml
# Class index
type: class
code: CS 2110
title: Data Structures
instructor: Ramirez
credits: 4
meetings: MW 10:10–11:25, Gates 114
linear_project: https://linear.app/...
content: https://drive.google.com/drive/folders/...
```

Syllabus notes use `type: syllabus`, `class`, and `source`. Class indexes may use `content` for a stable external course-content folder. Inbox captures use `type: capture`, `captured`, and optional `class`.

`Home.md` uses `type: dashboard` with `title`; `classes.md` uses `type: schedule` with `term`. These are metadata contracts for the two fixed root views, not additional ontology layers.

An instructor is required after an instructor-provided syllabus has been imported. A catalog-only syllabus scaffold may omit an instructor that has not yet been verified.

Never add `status`, `due`, `priority`, or `estimate` to vault frontmatter.

## Link and naming rules

- Use wikilinks in frontmatter so links survive file moves.
- Class indexes link to the syllabus, all existing week notes, all existing work notes, and the Linear project.
- Class indexes link every retained textbook in the course-level `textbooks/` directory.
- Work notes link to the class index, optional parent, weeks worked, and Linear issue.
- Week notes link to the class index and work notes touched that week.
- Zero-pad week and assignment numbers.
- Prefer spaces in work-note filenames and hyphens in folders, week filenames, and class-index filenames (`MATH-212.md`, never `MATH 212.md`).
- Avoid `#`, `|`, `^`, `[`, `]`, and `:` in filenames.
- Do not assume a note exists for every Linear issue.
- Do not look for `classes.md` inside a course folder.

## Linear operating rules

- Every non-triage issue must have exactly one course project.
- An issue exits triage only after it has a project, due date, and kind label.
- Use weekly cycles for when work is committed; normally select the due week, or an earlier week when work must begin sooner.
- Estimate focused hours with Fibonacci points: `1` under 1 hour, `2` for 1–2, `3` for 3–5, `5` for 6–10. Decompose work that would be `8`.
- Priority means consequence, not effort.
- Normal flow is `Backlog -> Todo -> In Progress -> Submitted -> Graded`; use `Blocked`, `Excused`, and `Missed` explicitly.
- Never reopen an original submission for a resubmission or regrade; create a related issue.
- Use milestones for exam checkpoints and issues/sub-issues for sitting and studying for the exam.

## Integration behavior

When Linear access is available, inspect current data before creating or changing projects, issues, cycles, milestones, labels, or views. Avoid duplicates by matching stable identifiers first and normalized names second. Prefer idempotent operations and report anything that could not be linked.

Prefer `tools/fast-<skill>/` for skill workflows. Prefer the repository-local CLIs in `tools/linear/`, `tools/google-drive/`, `tools/gmail/`, `tools/google-calendar/`, and `tools/gradescope/` for individual API calls over Linear, Drive, Gmail, Calendar, or Gradescope MCP. Invoke them with `tools/run-tool/run-tool.ps1 <tool> ...` or `python tools/run-tool/run_tool.py <tool> ...` under Windows PowerShell or a real `python.exe`. Do not wrap PowerShell cmdlets in `bash -c`, and do not use pyodide or any emulated interpreter. Discover a tool's commands with `<tool> commands` or `--help` (JSON catalog). `google-calendar upcoming --days 14` lists the next two weeks; `list_events` is the explicit time-range form. Do not write a new Python or PowerShell script at the start of a session. Put JSON payloads in `--json-file`. Use MCP only if a local tool is missing, unauthorized, or cannot perform the requested call. Fast runners print JSON. `--apply` writes vault notes, retains files, and creates Linear issues when a project, due date, and kind are available. They still must not copy Linear-owned fields into vault frontmatter, read Moodle or Gradescope secrets, or guess textbook page offsets.

When a class index has a Google Drive `content` URL, inspect that folder with `tools/google-drive/` before importing. Match by course code and file identity, and do not duplicate files already staged by Moodle-DL.

High-value automation should be pursued in this order:

1. Syllabus-to-issue import with explicit review before creation.
2. Cycle assignment from due date.
3. Due-date and weight-based priority escalation.
4. Overdue labeling and the `Slipped` view.
5. Weekly estimate load warnings.
6. Work-note scaffolding prefilled with the Linear join key.
7. LMS links and grade-state synchronization.

Automation must preserve the ownership boundary: it may link systems, but it must not create a second editable copy of mutable state.

## Repository tools and skills

- `tools/` contains project-local wrappers and documentation. Commit the integration code, not virtual environments, credentials, generated downloads, or runtime state.
- Call existing wrappers through `tools/run-tool/` (PowerShell or Python). Copy `tools/tool-template/` only when adding a new CLI, then register it in `tools/run-tool/run_tool.py`.
- Read a local text file by 1-based line numbers with `tools/read-file-lines/` (`read_file_lines` or `read-file-lines`). Do not use it on `.env.yml`.
- Prefer local wrappers over MCP for Linear, Google Drive, Gmail, Google Calendar, Gradescope, and Selenium. Shared Google OAuth, the Linear API key, and Gradescope cookies live in ignored `.env.yml`; the Google refresh token lives in ignored `tools/google-auth/state/`. Never read, print, transmit, or commit those files.
- `skills/` contains project-specific agent workflows. Each skill has a `tools/fast-<skill>/` runner for mechanical steps. For end-to-end Moodle imports, run `tools/fast-sync-class/` first, then read `skills/sync-class/SKILL.md` for remaining `needs_llm` items. For a non-Moodle webpage, run `tools/fast-fetch-webpage/` first, then follow `skills/fetch-webpage/SKILL.md`.
- For any Linear-to-vault or vault-to-Linear reconciliation, run `tools/fast-linear-sync/` first, then follow `skills/linear-sync/SKILL.md`.
- For dated syllabus obligations, run `tools/fast-import-syllabus/` (dry-run, then `--apply` after review). Assign `Week NN` cycles with `tools/fast-assign-cycles/`. Refresh Home.md via `tools/fast-dashboard/` rather than copying due dates into the vault. Run `tools/fast-weekly-review/` for inbox and unfinished work; never auto-set Missed. Scaffold a work note only with `tools/fast-scaffold-work-note/ --linear <key> --apply`.
- Moodle-DL uses the published package in an ignored `tools/moodle-dl/.venv/`; do not clone or vendor the upstream repository.
- If you are given a URL that does not start with moodle, do not attempt to use the moodle tool on it. Moodle-DL is only for hosts whose hostname starts with `moodle` (for example `moodle.bucknell.edu`). Use `tools/selenium/` and `skills/fetch-webpage/` for every other http(s) URL.
- Treat `tools/moodle-dl/state/` as ignored staging. Never read, print, transmit, or commit its configuration, tokens, private tokens, or cookies.
- Selenium uses the published `mcp-server-selenium` package in an ignored `tools/selenium/.venv/`; do not clone or vendor the upstream repository. Drive Helium at `C:\Program Files\imput\Helium\Application\chrome.exe` by default. Chrome profile, screenshots, downloads, and captured pages remain ignored under `tools/selenium/state/` and `tools/selenium/output/`.
- MarkItDown uses the published PDF extra in an ignored `tools/markitdown/.venv/`; raw conversions remain ignored under `tools/markitdown/output/`.
- pypdf uses the published package in an ignored `tools/pypdf/.venv/`; temporary homework-page extractions remain ignored under `tools/pypdf/output/`.
- Gradescope uses the published `gradescopeapi` package in an ignored `tools/gradescope/.venv/`. Authenticate with `gradescope.*` cookies in `.env.yml`; never print those values.
- Run `tools/fast-check-vault/` for a structured vault check, or `tools/vault-lint/check.ps1` for the same suite as console output. Use `tools/fast-fix-vault/` and `tools/fast-clean-vault/` for mechanical repairs, then `skills/fix-vault/SKILL.md` and `skills/clean-vault/SKILL.md` for remaining reviewed findings.
- PyMarkdown may apply only its declared mechanical autofixes. Flint and ls-lint findings require agent review because metadata values and file moves can change vault meaning or links.
- Review Moodle downloads before retention. Prefix retained binary filenames with the course code and place them in flat `attachments/`.
- When homework cites textbook pages, run `tools/fast-get-homework-pages/` first. Verify PDF page labels and never guess a page offset.
- Deadline-bearing Moodle content requires an explicit Linear import review before issue creation.
- Files under `skills/` follow Agent Skill metadata contracts rather than vault-note frontmatter contracts.

## Validation checklist

Before finishing an organizational change, verify:

- Every vault note outside `skills/` has a valid `type`.
- Every course folder follows the path grammar.
- Every retained textbook is in its owning course's `textbooks/` directory and has a course-code-prefixed filename.
- Every linked work note has a Linear issue key.
- No forbidden mutable fields were added to vault frontmatter.
- Wikilinks resolve without ambiguous bare filenames.
- Numbers in filenames are zero-padded.
- Dashboards and queries tolerate missing work notes.
- Deadline-bearing captures are directed to Linear triage, not `inbox/`.

## Decisions still requiring user input

Do not silently settle these design choices:

- End-of-term archive-in-place versus export-and-reset.
- Whether `work/` needs subdivision for unusually large courses.
- Whether empty academic weeks should have placeholder week notes.
- Whether sub-issues ever receive separate notes instead of sections in the parent note.
