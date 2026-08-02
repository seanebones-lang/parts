#!/usr/bin/env bash
# One-command dealership demo: parrts ingest + FastAPI :8000 + Next.js :3000
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "== Parts demo_up =="
echo "Root: $ROOT"

if [[ ! -d .venv ]]; then
  echo "Creating .venv..."
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate

echo "Installing Python deps (core+api)..."
pip install -q -e ".[dev,api]"
if [[ -f backend/requirements.txt ]]; then
  pip install -q -r backend/requirements.txt || true
fi

echo "Building demo inventory index..."
python -m parrts ingest --force

echo "Seeding DMS + reindexing RAG from OEM/DMS catalog..."
python -m parrts dms seed --reindex || python -m parrts dms seed
# If seed without reindex flag path, force reindex
python -m parrts dms reindex || true

echo "Seeding email desk (auto-answer + G/Y/R)..."
python -m parrts email seed --clear || true

mkdir -p .parrts/logs
export AUTH_MODE="${AUTH_MODE:-demo}"
export ENVIRONMENT="${ENVIRONMENT:-development}"
export DEBUG="${DEBUG:-true}"
export PYTHONPATH="${ROOT}/backend:${ROOT}/src${PYTHONPATH:+:$PYTHONPATH}"
export NEXT_PUBLIC_API_URL="${NEXT_PUBLIC_API_URL:-http://127.0.0.1:8000}"

# Kill stale listeners if any (best-effort)
if command -v lsof >/dev/null 2>&1; then
  for port in 8000 3000; do
    pids=$(lsof -ti tcp:"$port" -sTCP:LISTEN 2>/dev/null || true)
    if [[ -n "${pids}" ]]; then
      echo "Freeing port $port (pids: $pids)"
      kill $pids 2>/dev/null || true
      sleep 1
    fi
  done
fi

echo "Starting API on :8000..."
(
  cd "$ROOT"
  # uvicorn needs main:app on PYTHONPATH (backend)
  nohup uvicorn main:app --host 127.0.0.1 --port 8000 --app-dir backend \
    >.parrts/logs/api.log 2>&1 &
  echo $! >.parrts/api.pid
)

echo "Waiting for /health..."
for i in $(seq 1 40); do
  if curl -fsS "http://127.0.0.1:8000/health" >/dev/null 2>&1; then
    echo "API healthy."
    break
  fi
  if [[ "$i" -eq 40 ]]; then
    echo "API failed to become healthy. Tail:"
    tail -40 .parrts/logs/api.log || true
    exit 1
  fi
  sleep 0.5
done

if [[ ! -d frontend/node_modules ]]; then
  echo "npm ci (frontend)..."
  (cd frontend && npm ci)
fi

echo "Starting frontend on :3000..."
(
  cd "$ROOT/frontend"
  nohup npm run dev -- -p 3000 -H 127.0.0.1 \
    >"$ROOT/.parrts/logs/fe.log" 2>&1 &
  echo $! >"$ROOT/.parrts/fe.pid"
)

echo "Waiting for frontend..."
for i in $(seq 1 60); do
  if curl -fsS "http://127.0.0.1:3000" >/dev/null 2>&1; then
    echo "Frontend up."
    break
  fi
  if [[ "$i" -eq 60 ]]; then
    echo "Frontend slow/fail. Tail:"
    tail -40 "$ROOT/.parrts/logs/fe.log" || true
    # still print URLs — user may wait
  fi
  sleep 0.5
done

cat <<EOF

============================================================
  DEALERSHIP DEMO READY
============================================================
  Parts Search UI : http://127.0.0.1:3000/parts
  Home            : http://127.0.0.1:3000/
  API health      : http://127.0.0.1:8000/health
  API docs        : http://127.0.0.1:8000/docs
  Demo scenarios  : http://127.0.0.1:8000/demo/scenarios

  Smoke test      : ./scripts/demo_smoke.sh
  Stop            : ./scripts/demo_down.sh
  Pitch           : docs/DEALERSHIP_PITCH.md
============================================================
EOF
