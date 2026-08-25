# Bash/Git Bash entry point for the repository CLI dispatcher.
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
root="$(cd "$here/../.." && pwd)"
py="$root/tools/pymarkdown/.venv/Scripts/python.exe"
if [[ ! -f "$py" ]]; then
  if command -v python.exe >/dev/null 2>&1; then
    py="$(command -v python.exe)"
  elif command -v python >/dev/null 2>&1; then
    py="$(command -v python)"
  else
    echo "Python is required. Run python tools/pymarkdown/install.py first." >&2
    exit 1
  fi
fi
exec "$py" "$here/run_tool.py" "$@"
