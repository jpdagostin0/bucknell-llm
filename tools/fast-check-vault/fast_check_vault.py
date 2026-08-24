from __future__ import annotations

from typing import Any

from fast_common import run_cli, run_vault_checks


def run(_: dict[str, Any]) -> dict[str, Any]:
    return run_vault_checks()


def main() -> int:
    return run_cli("fast-check-vault", {"run": run})


if __name__ == "__main__":
    raise SystemExit(main())
