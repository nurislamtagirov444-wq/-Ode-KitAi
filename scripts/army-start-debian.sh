#!/usr/bin/env bash
# Starts the local AI stack inside Debian. Called by the Termux:Widget shortcut.
# It is safe to run repeatedly: existing tmux sessions are kept.
set -eu

ARMY_DIR="/sdcard/ARMY"
ROUTER_DIR="$ARMY_DIR/router"
LOG_DIR="$ARMY_DIR/logs"
STATUS_FILE="$LOG_DIR/army-status.txt"
G4F_BIN="/root/g4f-venv/bin/g4f"
G4F_PYTHON="/root/g4f-venv/bin/python"
FCC_BIN="/root/.local/bin/fcc-server"
ENV_FILE="/root/.fcc/.env"

mkdir -p "$ARMY_DIR" "$ROUTER_DIR" "$LOG_DIR"

if ! command -v tmux >/dev/null 2>&1; then
  echo "tmux is missing. Run the one-time Army installer again." >&2
  exit 1
fi

if [ ! -x "$G4F_BIN" ] || [ ! -x "$G4F_PYTHON" ] || [ ! -x "$FCC_BIN" ]; then
  echo "g4f or FCC is missing. This launcher expects the existing setup." >&2
  exit 1
fi

if [ ! -f "$ROUTER_DIR/g4f_failover_router.py" ] || [ ! -f "$ROUTER_DIR/routes.json" ] || [ ! -f "$ARMY_DIR/army-watchdog-debian.sh" ]; then
  echo "Army files are missing. Run the one-time Army installer again." >&2
  exit 1
fi

# Keep FCC aimed at one stable local address. Empty overrides use MODEL.
python3 - "$ENV_FILE" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
path.parent.mkdir(parents=True, exist_ok=True)
values = {
    "HOST": "127.0.0.1",
    "PORT": "8082",
    "LLAMACPP_BASE_URL": "http://127.0.0.1:1340/v1",
    "MODEL": "llamacpp/default",
    "MODEL_FABLE": "",
    "MODEL_OPUS": "",
    "MODEL_SONNET": "",
    "MODEL_HAIKU": "",
    "FCC_OPEN_BROWSER": "false",
}
lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
seen = set()
out = []
for line in lines:
    key = line.split("=", 1)[0].strip() if "=" in line else ""
    if key in values:
        out.append(f'{key}="{values[key]}"')
        seen.add(key)
    else:
        out.append(line)
for key, value in values.items():
    if key not in seen:
        out.append(f'{key}="{value}"')
path.write_text("\n".join(out).rstrip() + "\n", encoding="utf-8")
PY

start_session() {
  local name="$1"
  local command="$2"
  local health_url="$3"
  local log="$LOG_DIR/${name}.log"

  # Do not collide with an already running service that was started manually.
  if [ -n "$health_url" ] && curl -fsS --max-time 3 "$health_url" >/dev/null 2>&1; then
    return 0
  fi
  if tmux has-session -t "$name" 2>/dev/null; then
    if [ -z "$health_url" ]; then
      return 0
    fi
    tmux kill-session -t "$name" 2>/dev/null || true
  fi
  tmux new-session -d -s "$name" "exec $command >> '$log' 2>&1"
}

start_session "army-g4f" "$G4F_BIN api" "http://127.0.0.1:1337/v1/models"
start_session "army-router" "$G4F_PYTHON $ROUTER_DIR/g4f_failover_router.py --config $ROUTER_DIR/routes.json" "http://127.0.0.1:1340/health"
start_session "army-fcc" "$FCC_BIN" "http://127.0.0.1:8082/health"
start_session "army-watchdog" "bash $ARMY_DIR/army-watchdog-debian.sh" ""

check_url() {
  local name="$1"
  local url="$2"
  if curl -fsS --max-time 5 "$url" >/dev/null 2>&1; then
    printf '%s: OK\n' "$name"
  else
    printf '%s: WAIT_OR_ERROR\n' "$name"
  fi
}

{
  date '+%Y-%m-%d %H:%M:%S'
  echo "Army launcher ran. Existing services were kept; missing ones were started."
  sleep 3
  check_url "g4f" "http://127.0.0.1:1337/v1/models"
  check_url "router" "http://127.0.0.1:1340/health"
  check_url "fcc" "http://127.0.0.1:8082/health"
  echo "Commander: cd /sdcard/ARMY && /root/.local/bin/fcc-claude"
  echo "Logs: $LOG_DIR/army-g4f.log, army-router.log, army-fcc.log"
} > "$STATUS_FILE"
