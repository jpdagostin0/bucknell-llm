---
type: tool
---

# Fast Common

Shared library for `fast-*` skill runners. It is not invoked directly. Each `tools/fast-<skill>/` wrapper puts this directory on `PYTHONPATH` and uses the PyMarkdown virtual environment, which already provides PyYAML.

The library encodes course resolution, Moodle inventory without opening credential files, classification, hash comparison, PDF conversion, page and section citation extraction, week/syllabus/class-index writes, Linear issue creation, and vault-check orchestration. Interactive auth and true ambiguities stay in `needs_llm` or `needs_user`.
