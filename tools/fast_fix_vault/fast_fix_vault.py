from __future__ import annotations

from typing import Any

from fast_common import autofix_markdown, run_cli, run_vault_checks
from vault_apply import (
    qualify_unique_wikilinks,
    repair_class_index_links,
    repair_forbidden_frontmatter,
)


def run(_: dict[str, Any]) -> dict[str, Any]:
    baseline = run_vault_checks()
    if baseline["ok"]:
        return {
            "ok": True,
            "baseline": baseline,
            "autofix": {"skipped": True},
            "needs_llm": [],
        }
    autofix = autofix_markdown()
    repaired = {
        "forbidden_frontmatter": repair_forbidden_frontmatter(),
        "class_index_links": repair_class_index_links(),
        "qualified_wikilinks": qualify_unique_wikilinks(),
    }
    after = run_vault_checks()
    return {
        "ok": after["ok"],
        "baseline_failed": baseline["failed"],
        "autofix": autofix,
        "repaired": repaired,
        "after": after,
        "needs_llm": after["needs_llm"],
    }


def main() -> int:
    return run_cli("fast_fix_vault", {"run": run})


if __name__ == "__main__":
    raise SystemExit(main())
