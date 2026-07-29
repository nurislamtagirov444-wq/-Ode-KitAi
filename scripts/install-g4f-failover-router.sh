#!/usr/bin/env sh
# Installs the locally hosted g4f failover router files for the Termux Debian setup.
# It does not read keys, modify FCC settings, or start/stop existing servers.
set -eu

BRANCH="arena/019faeb4-ode-kitai"
RAW_BASE="https://raw.githubusercontent.com/nurislamtagirov444-wq/-Ode-KitAi/${BRANCH}"
ROUTER_DIR="${ROUTER_DIR:-/sdcard/ARMY/router}"
PYTHON_BIN="${G4F_PYTHON:-/root/g4f-venv/bin/python}"

if [ ! -x "$PYTHON_BIN" ]; then
  echo "g4f Python was not found at: $PYTHON_BIN"
  echo "Start from Debian where /root/g4f-venv exists, or set G4F_PYTHON."
  exit 1
fi

mkdir -p "$ROUTER_DIR"
curl -fsSL "$RAW_BASE/tools/g4f_failover_router.py" -o "$ROUTER_DIR/g4f_failover_router.py"
curl -fsSL "$RAW_BASE/tools/g4f_failover_routes.example.json" -o "$ROUTER_DIR/routes.json"
chmod 700 "$ROUTER_DIR/g4f_failover_router.py"

if ! "$PYTHON_BIN" -c 'import fastapi, httpx, uvicorn' 2>/dev/null; then
  echo "Router files were installed, but FastAPI/httpx/uvicorn are missing in g4f-venv."
  echo "Run: $PYTHON_BIN -m pip install -U fastapi httpx uvicorn"
  exit 1
fi

cat <<EOF
Installed:
  $ROUTER_DIR/g4f_failover_router.py
  $ROUTER_DIR/routes.json

Start it in its own Debian terminal:
  $PYTHON_BIN $ROUTER_DIR/g4f_failover_router.py --config $ROUTER_DIR/routes.json

Then check from another Debian terminal:
  curl -s http://127.0.0.1:1340/health
EOF
