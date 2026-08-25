from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


def vault_root() -> Path:
    return Path(__file__).resolve().parents[2]


def main() -> int:
    root = vault_root()
    tool_root = Path(__file__).resolve().parent
    python = root / "tools" / "pymarkdown" / ".venv" / "Scripts" / "python.exe"
    flint = root / "tools" / "flint" / "bin" / "flint.exe"
    ls_lint = root / "tools" / "ls_lint" / "bin" / "ls-lint-windows-amd64.exe"
    validator = tool_root / "validate_vault.py"
    validator_tests = tool_root / "test_validate_vault.py"
    required = [python, flint, ls_lint, validator, validator_tests]
    for executable in required:
        if not executable.exists():
            print(
                f"Missing linter executable: {executable}. "
                "Run the corresponding tools/<name>/install.py script.",
                file=sys.stderr,
            )
            return 1

    failed: list[str] = []

    print("PyMarkdown")
    pymarkdown_result = subprocess.run(
        [
            str(python),
            "-m",
            "pymarkdown",
            "--config",
            str(root / ".pymarkdown.yml"),
            "scan",
            "--recurse",
            "--respect-gitignore",
            ".",
        ],
        cwd=root,
        check=False,
    )
    if pymarkdown_result.returncode != 0:
        failed.append("PyMarkdown")

    print("Flint")
    flint_result = subprocess.run(
        [str(flint), "--config", str(root / ".flint.yml"), "--color=false", "."],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    flint_output = (flint_result.stdout or "") + (flint_result.stderr or "")
    if flint_output:
        print(flint_output, end="" if flint_output.endswith("\n") else "\n")
    if flint_result.returncode != 0 or re.search(
        r"(?m)^\s+\d+:\d+\s+error\s+", flint_output
    ):
        failed.append("Flint")

    print("Vault integrity")
    validator_result = subprocess.run(
        [str(python), str(validator), "."],
        cwd=root,
        check=False,
    )
    if validator_result.returncode != 0:
        failed.append("Vault integrity")

    print("Rule tests")
    tests_result = subprocess.run(
        [str(python), str(validator_tests)],
        cwd=root,
        check=False,
    )
    if tests_result.returncode != 0:
        failed.append("Rule tests")

    print("ls_lint")
    ls_result = subprocess.run(
        [str(ls_lint), "--config", str(root / ".ls_lint.yml"), "--workdir", "."],
        cwd=root,
        check=False,
    )
    if ls_result.returncode != 0:
        failed.append("ls_lint")

    if failed:
        print("Vault checks failed: " + ", ".join(failed), file=sys.stderr)
        return 1

    print("All vault checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
