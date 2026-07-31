#!/usr/bin/env bash
# Parrts modern demo launcher — hybrid RAG core + optional Streamlit UI
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

echo "Parrts hybrid RAG demo"
echo "======================"
echo "Root: $ROOT"

if [ ! -f "pyproject.toml" ] || [ ! -d "src/parrts" ]; then
  echo "Error: run from repo root (need pyproject.toml + src/parrts)"
  exit 1
fi

PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV_DIR="${VENV_DIR:-.venv}"

if [ ! -d "$VENV_DIR" ]; then
  echo "Creating $VENV_DIR..."
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

echo "Installing parrts (dev+api) + streamlit..."
pip install -q -e ".[dev,api]" streamlit httpx

export PARRTS_ROOT="$ROOT"
export PARRTS_EMBEDDER="${PARRTS_EMBEDDER:-hash}"
export PYTHONPATH="${ROOT}/src:${ROOT}/backend:${PYTHONPATH:-}"

echo "Building/loading index..."
python -m parrts ingest

echo ""
echo "Smoke query..."
python -m parrts query "brake pads for 2019 Honda Civic" --no-llm | head -c 800 || true
echo ""
echo ""

API_PORT="${API_PORT:-8080}"
DASH_PORT="${DASH_PORT:-8501}"
MODE="${1:-both}"  # api | ui | both | backend

cleanup() {
  echo ""
  echo "Shutting down..."
  [ -n "${API_PID:-}" ] && kill "$API_PID" 2>/dev/null || true
  [ -n "${UI_PID:-}" ] && kill "$UI_PID" 2>/dev/null || true
  [ -n "${BE_PID:-}" ] && kill "$BE_PID" 2>/dev/null || true
  exit 0
}
trap cleanup SIGINT SIGTERM

start_parrts_api() {
  echo "Starting parrts API on :$API_PORT ..."
  uvicorn parrts.api:app --host 0.0.0.0 --port "$API_PORT" --app-dir src &
  API_PID=$!
}

start_backend() {
  echo "Starting enterprise backend on :8000 (parrts /query included)..."
  (
    cd backend
    PYTHONPATH="${ROOT}/src:${ROOT}/backend" uvicorn main:app --host 0.0.0.0 --port 8000
  ) &
  BE_PID=$!
}

start_ui() {
  echo "Starting Streamlit dashboard on :$DASH_PORT ..."
  streamlit run src/parrts/ui_streamlit.py \
    --server.port "$DASH_PORT" \
    --server.headless true \
    --browser.gatherUsageStats false &
  UI_PID=$!
}

case "$MODE" in
  api)
    start_parrts_api
    ;;
  backend)
    start_backend
    ;;
  ui)
    start_ui
    ;;
  both|*)
    start_parrts_api
    sleep 1
    start_ui
    ;;
esac

echo ""
echo "Live:"
[ -n "${API_PID:-}" ] && echo "  Parrts API  http://127.0.0.1:${API_PORT}/docs  (PID $API_PID)"
[ -n "${BE_PID:-}" ] && echo "  Backend     http://127.0.0.1:8000/docs       (PID $BE_PID)"
[ -n "${UI_PID:-}" ] && echo "  Dashboard   http://127.0.0.1:${DASH_PORT}/   (PID $UI_PID)"
echo ""
echo "Try: curl -s 'http://127.0.0.1:${API_PORT}/query?text=brake+pads+civic' | python -m json.tool | head"
echo "Modes: ./start_demo.sh [both|api|ui|backend]"
echo "Ctrl+C to stop"
wait
