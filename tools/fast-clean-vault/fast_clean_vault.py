from __future__ import annotations

from typing import Any

from fast_common import autofix_markdown, run_cli, run_vault_checks
from vault_apply import (
    qualify_unique_wikilinks,
    repair_class_index_links,
    repair_forbidden_frontmatter,
)


def run(_: dict[str, Any]) -> dict[str, Any]:
    first = run_vault_checks()
    if first["ok"]:
        return {"ok": True, "clean": True, "checks": first, "needs_llm": []}
    autofix = autofix_markdown()
    repaired = {
        "forbidden_frontmatter": repair_forbidden_frontmatter(),
        "class_index_links": repair_class_index_links(),
        "qualified_wikilinks": qualify_unique_wikilinks(),
    }
    second = run_vault_checks()
    return {
        "ok": second["ok"],
        "clean": second["ok"],
        "first": {"failed": first["failed"]},
        "autofix": autofix,
        "repaired": repaired,
        "second": second,
        "needs_llm": second["needs_llm"],
    }


def main() -> int:
    return run_cli("fast-clean-vault", {"run": run})


if __name__ == "__main__":
    raise SystemExit(main())
