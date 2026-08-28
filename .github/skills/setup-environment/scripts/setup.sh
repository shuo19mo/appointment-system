#!/usr/bin/env bash
set -euo pipefail

FORCE=0; RUN=0; VERIFY=1; TESTS=0
for arg in "$@"; do
  case "$arg" in
    --force) FORCE=1 ;;
    --run) RUN=1 ;;
    --no-verify) VERIFY=0 ;;
    --test) TESTS=1 ;;
    *) echo "Unknown flag: $arg" >&2; exit 2 ;;
  esac
done

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/../../../.." >/dev/null && pwd)"
cd "$PROJECT_ROOT"

find_python() {
  local candidate version major minor
  for candidate in python3.13 python3.12 python3.11 python3; do
    command -v "$candidate" >/dev/null 2>&1 || continue
    version="$($candidate -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
    major="${version%%.*}"; minor="${version##*.}"
    if [ "$major" = 3 ] && [ "$minor" -ge 11 ]; then
      printf '%s|%s' "$candidate" "$version"; return 0
    fi
  done
  return 1
}

PY_PICK="$(find_python || true)"
if [ -z "$PY_PICK" ]; then
  echo "Python 3.11+ is required." >&2; exit 1
fi
PYTHON_BIN="${PY_PICK%%|*}"; PY_VER="${PY_PICK##*|}"
echo "[OK] Python $PY_VER ($PYTHON_BIN)"

if [ "$FORCE" -eq 1 ] && [ -d .venv ]; then
  rm -rf .venv
fi
if [ -x .venv/bin/python ]; then
  VENV_MINOR="$(.venv/bin/python -c 'import sys; print(sys.version_info.minor)' 2>/dev/null || echo 0)"
  VENV_MAJOR="$(.venv/bin/python -c 'import sys; print(sys.version_info.major)' 2>/dev/null || echo 0)"
  if [ "$VENV_MAJOR" != 3 ] || [ "$VENV_MINOR" -lt 11 ]; then rm -rf .venv; fi
fi
if [ ! -x .venv/bin/python ]; then
  "$PYTHON_BIN" -m venv .venv
fi
VENV_PY="$PROJECT_ROOT/.venv/bin/python"

"$VENV_PY" -m pip install --upgrade pip --quiet
"$VENV_PY" -m pip install -r requirements.txt
if [ "$TESTS" -eq 1 ]; then "$VENV_PY" -m pip install -r requirements-dev.txt; fi

if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created .env. Set DEEPSEEK_API_KEY before verification." >&2
fi
mkdir -p data

if [ "$VERIFY" -eq 1 ]; then "$VENV_PY" "$SCRIPT_DIR/verify_env.py"; fi
if [ "$TESTS" -eq 1 ]; then
  "$VENV_PY" -m pytest -q
  "$VENV_PY" -m compileall -q agents api config db services web app.py
fi

echo "[OK] Education scheduling environment is ready."
echo "Activate: source .venv/bin/activate"
if [ "$RUN" -eq 1 ]; then
  exec "$VENV_PY" -m uvicorn app:app --host 127.0.0.1 --port 8001 --reload
fi
