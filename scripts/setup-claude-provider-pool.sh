#!/usr/bin/env bash
# Wires the non-root Claude worker to the root-owned local provider pool.
set -euo pipefail

POOL_FILE=""
for candidate in /mnt/sdcard/ARMY/providers/claude.providers /sdcard/ARMY/providers/claude.providers; do
  if [ -f "$candidate" ]; then POOL_FILE="$candidate"; break; fi
done
POOL_SCRIPT=""
for candidate in /mnt/sdcard/ARMY/setup/claude_provider_pool.py /sdcard/ARMY/setup/claude_provider_pool.py; do
  if [ -f "$candidate" ]; then POOL_SCRIPT="$candidate"; break; fi
done
PYTHON="/root/g4f-venv/bin/python"
WORKER_SETTINGS="/home/worker/.claude/settings.json"
LOG_DIR="/root/army-logs"

[ -f "$POOL_FILE" ] || { echo "Missing: $POOL_FILE"; exit 1; }
[ -f "$POOL_SCRIPT" ] || { echo "Missing: $POOL_SCRIPT"; exit 1; }
[ -x "$PYTHON" ] || { echo "Missing Python: $PYTHON"; exit 1; }
id worker >/dev/null 2>&1 || { echo "Run the Claude worker setup first."; exit 1; }

# Require at least one real non-comment provider line.
if ! grep -Eq '^[[:space:]]*[^#|]+[[:space:]]*\|[[:space:]]*https?://[^|]+\|[[:space:]]*[^#|]+([[:space:]]*\|[[:space:]]*[^#|]+)?[[:space:]]*$' "$POOL_FILE"; then
  echo "claude.providers has no valid KEY | URL | PROVIDER | MODEL line."
  exit 1
fi

"$PYTHON" -m pip install -q -U httpx fastapi uvicorn
mkdir -p "$LOG_DIR"

python3 - "$WORKER_SETTINGS" <<'PY'
import json, sys
from pathlib import Path
path=Path(sys.argv[1])
data=json.loads(path.read_text()) if path.exists() else {}
data["model"]="claude-sonnet-5"
env=data.setdefault("env", {})
env["ANTHROPIC_BASE_URL"]="http://127.0.0.1:1342"
env["ANTHROPIC_AUTH_TOKEN"]="local-provider-pool"
path.write_text(json.dumps(data, ensure_ascii=False, indent=2)+"\n")
PY
chown worker:worker "$WORKER_SETTINGS"
chmod 600 "$WORKER_SETTINGS"

pkill -f '[c]laude_provider_pool.py' 2>/dev/null || true
nohup env CLAUDE_PROVIDER_FILE="$POOL_FILE" "$PYTHON" "$POOL_SCRIPT" > "$LOG_DIR/claude-provider-pool.log" 2>&1 &
sleep 2
curl -fsS http://127.0.0.1:1342/health
printf '\nClaude worker now uses the local pool. Start: claude-worker\n'
