#!/usr/bin/env bash
# Stop demo processes started by demo_up.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

stop_pidfile() {
  local f="$1"
  if [[ -f "$f" ]]; then
    local pid
    pid=$(cat "$f" 2>/dev/null || true)
    if [[ -n "${pid}" ]] && kill -0 "$pid" 2>/dev/null; then
      echo "Stopping pid $pid ($f)"
      kill "$pid" 2>/dev/null || true
      sleep 0.5
      kill -9 "$pid" 2>/dev/null || true
    fi
    rm -f "$f"
  fi
}

stop_pidfile .parrts/api.pid
stop_pidfile .parrts/fe.pid

if command -v lsof >/dev/null 2>&1; then
  for port in 8000 3000; do
    pids=$(lsof -ti tcp:"$port" -sTCP:LISTEN 2>/dev/null || true)
    if [[ -n "${pids}" ]]; then
      echo "Killing listeners on $port: $pids"
      kill $pids 2>/dev/null || true
    fi
  done
fi

echo "Demo stopped."
