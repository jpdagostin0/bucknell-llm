from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "run-tool"))
from run_tool import dispatch


def main() -> int:
    return dispatch("moodle-dl", sys.argv[1:])


if __name__ == "__main__":
    raise SystemExit(main())
