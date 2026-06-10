#!/usr/bin/env bash
# Start the Lucid web app, reachable over Tailscale.
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -d venv ]; then
  echo "Creating virtualenv..."
  python3 -m venv venv
fi
source venv/bin/activate
pip install -q -r requirements.txt

HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8042}"
echo "Starting on http://${HOST}:${PORT}"
echo "Over Tailscale, open this on your phone: http://$(tailscale ip -4 2>/dev/null | head -1):${PORT}"
exec uvicorn app.main:app --host "$HOST" --port "$PORT"
