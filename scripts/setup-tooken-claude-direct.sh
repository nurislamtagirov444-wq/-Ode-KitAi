#!/usr/bin/env bash
# Configures the official Claude Code CLI for Tooken's Anthropic-compatible gateway.
set -euo pipefail

SECRET_FILE="/root/.config/army/tooken.env"
SETTINGS_DIR="/root/.claude"
SETTINGS_FILE="$SETTINGS_DIR/settings.json"
MODEL="claude-sonnet-5"

[ -f "$SECRET_FILE" ] || { echo "No local Tooken key file found: $SECRET_FILE"; exit 1; }
set -a
. "$SECRET_FILE"
set +a
[ -n "${TOOKEN_API_KEY:-}" ] || { echo "TOOKEN_API_KEY is empty."; exit 1; }

if ! command -v claude >/dev/null 2>&1; then
  echo "Installing Claude Code CLI..."
  npm install -g @anthropic-ai/claude-code
fi

mkdir -p "$SETTINGS_DIR"
chmod 700 "$SETTINGS_DIR"
[ ! -f "$SETTINGS_FILE" ] || cp "$SETTINGS_FILE" "$SETTINGS_FILE.bak"

TOOKEN_API_KEY="$TOOKEN_API_KEY" python3 - "$SETTINGS_FILE" "$MODEL" <<'PY'
import json, os, sys
from pathlib import Path

path, model = Path(sys.argv[1]), sys.argv[2]
try:
    data = json.loads(path.read_text()) if path.exists() else {}
except json.JSONDecodeError:
    data = {}
env = data.setdefault("env", {})
env["ANTHROPIC_BASE_URL"] = "https://tooken.club"
env["ANTHROPIC_AUTH_TOKEN"] = os.environ["TOOKEN_API_KEY"]
data["model"] = model
path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
PY
chmod 600 "$SETTINGS_FILE"

echo "Direct Tooken Claude Code is configured: $MODEL"
echo "Start it with: cd /sdcard/ARMY && claude --model $MODEL"
echo "The key is stored only in $SETTINGS_FILE (mode 600)."
