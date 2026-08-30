#!/usr/bin/env bash
# Start the PromptDNA backend and frontend for local development.
# Usage:  ./scripts/dev.sh
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ -x "$root/backend/.venv/Scripts/python.exe" ]]; then
  py="$root/backend/.venv/Scripts/python.exe"   # Windows venv layout
else
  py="$root/backend/.venv/bin/python"           # POSIX venv layout
fi

( cd "$root/backend" && "$py" -m uvicorn app.main:app --reload --port 8000 ) &
backend_pid=$!

( cd "$root/frontend" && npm run dev ) &
frontend_pid=$!

trap 'kill "$backend_pid" "$frontend_pid" 2>/dev/null || true' INT TERM EXIT

echo "backend  pid $backend_pid  -> http://localhost:8000/health"
echo "frontend pid $frontend_pid -> http://localhost:3000"
wait
