#!/usr/bin/env bash
# Start RedactQC in development mode (backend + frontend dev server)
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_PORT=8000
FRONTEND_PORT=5173

cleanup() {
    echo ""
    echo "Shutting down..."
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null || true
    wait $BACKEND_PID $FRONTEND_PID 2>/dev/null || true
    echo "Stopped."
}
trap cleanup EXIT INT TERM

# Activate venv
source "$PROJECT_DIR/.venv/bin/activate"

# Initialize DB + start backend (runs from project root for module imports)
echo "Starting backend on http://127.0.0.1:$BACKEND_PORT"
python -m backend.api &
BACKEND_PID=$!

# Wait for backend to be ready
for i in $(seq 1 30); do
    if curl -s -o /dev/null http://127.0.0.1:$BACKEND_PORT/api/stats 2>/dev/null; then
        break
    fi
    sleep 0.5
done

# Start frontend dev server (must cd into frontend/ so Vite finds index.html)
echo "Starting frontend on http://localhost:$FRONTEND_PORT"
cd "$PROJECT_DIR/frontend"
npx vite --port $FRONTEND_PORT &
FRONTEND_PID=$!
cd "$PROJECT_DIR"

echo ""
echo "RedactQC running:"
echo "  Dashboard: http://localhost:$FRONTEND_PORT"
echo "  API:       http://127.0.0.1:$BACKEND_PORT"
echo ""
echo "Press Ctrl+C to stop."

wait $BACKEND_PID $FRONTEND_PID 2>/dev/null || true
