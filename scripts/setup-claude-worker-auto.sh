#!/usr/bin/env bash
# Creates a non-root Claude Code worker with unattended permissions limited by Unix access.
set -euo pipefail

USER_NAME="worker"
HOME_DIR="/home/$USER_NAME"
SECRET_FILE="/root/.config/army/tooken.env"
MODEL="claude-sonnet-5"
SHARED_WORKSPACE="/sdcard/ARMY/worker-projects"

[ -f "$SECRET_FILE" ] || { echo "Missing local Tooken key file: $SECRET_FILE"; exit 1; }
set -a
. "$SECRET_FILE"
set +a
[ -n "${TOOKEN_API_KEY:-}" ] || { echo "TOOKEN_API_KEY is empty."; exit 1; }

if ! id "$USER_NAME" >/dev/null 2>&1; then
  useradd -m -s /bin/bash "$USER_NAME"
fi

if ! command -v claude >/dev/null 2>&1; then
  npm install -g @anthropic-ai/claude-code
fi

mkdir -p "$SHARED_WORKSPACE" "$HOME_DIR/.claude" "$HOME_DIR/bin"
# The worker can fully manage only this shared project directory.
chmod 777 "$SHARED_WORKSPACE"
ln -sfn "$SHARED_WORKSPACE" "$HOME_DIR/army"

TOOKEN_API_KEY="$TOOKEN_API_KEY" python3 - "$HOME_DIR/.claude/settings.json" "$MODEL" <<'PY'
import json, os, sys
from pathlib import Path
path, model = Path(sys.argv[1]), sys.argv[2]
data = {
  "model": model,
  "env": {
    "ANTHROPIC_BASE_URL": "https://tooken.club",
    "ANTHROPIC_AUTH_TOKEN": os.environ["TOOKEN_API_KEY"]
  }
}
path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
PY

cat > "$HOME_DIR/bin/claude-auto" <<'EOF'
#!/usr/bin/env bash
cd "$HOME/army"
exec claude --model claude-sonnet-5 --dangerously-skip-permissions "$@"
EOF
chmod 700 "$HOME_DIR/bin/claude-auto"
chown -R "$USER_NAME:$USER_NAME" "$HOME_DIR"
chmod 700 "$HOME_DIR/.claude"
chmod 600 "$HOME_DIR/.claude/settings.json"

cat > /usr/local/bin/claude-worker <<EOF
#!/usr/bin/env bash
exec su - $USER_NAME -s /bin/bash -c '$HOME_DIR/bin/claude-auto'
EOF
chmod 755 /usr/local/bin/claude-worker

echo "Worker is ready. Start automatic Claude Sonnet 5 with: claude-worker"
echo "Its writable workspace is visible in Android Files: $SHARED_WORKSPACE"
