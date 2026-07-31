#!/usr/bin/env bash
# Run inside the existing Debian proot. The API key is read silently and is never printed.
set -euo pipefail

BASE="https://tooken.club/v1"
ARMY="/sdcard/ARMY"
DIR="$ARMY/tooken"
PYTHON="/root/g4f-venv/bin/python"
SECRET_DIR="/root/.config/army"
SECRET_FILE="$SECRET_DIR/tooken.env"
FCC_ENV="/root/.fcc/.env"

[ -x "$PYTHON" ] || { echo "g4f Python is missing: $PYTHON"; exit 1; }
mkdir -p "$DIR" "$SECRET_DIR" "$ARMY/projects" "$ARMY/mission"
chmod 700 "$SECRET_DIR"

printf 'New Tooken API key (input is hidden): '
read -r -s TOOKEN_API_KEY
printf '\n'
[ -n "$TOOKEN_API_KEY" ] || { echo "Key was empty."; exit 1; }

umask 077
printf 'export TOOKEN_API_KEY=%q\nexport TOOKEN_BASE_URL=%q\n' "$TOOKEN_API_KEY" "$BASE" > "$SECRET_FILE"
unset TOOKEN_API_KEY
chmod 600 "$SECRET_FILE"

"$PYTHON" -m pip install -q -U httpx fastapi uvicorn

MODEL=$(
  set -a; . "$SECRET_FILE"; set +a
  curl -fsS -H "Authorization: Bearer $TOOKEN_API_KEY" "$BASE/models" |
  "$PYTHON" -c '
import json, sys
items=json.load(sys.stdin).get("data", [])
ids=[str(x.get("id", "")) for x in items if isinstance(x, dict)]
exact=[x for x in ids if x.lower() == "gpt-5"]
if exact: print(exact[0]); raise SystemExit
matches=[x for x in ids if x.lower().startswith("gpt-5")]
if matches: print(sorted(matches)[0]); raise SystemExit
print("", end="")
'
)

if [ -z "$MODEL" ]; then
  echo "No GPT-5 model was returned by this key. Available GPT IDs:"
  set -a; . "$SECRET_FILE"; set +a
  curl -fsS -H "Authorization: Bearer $TOOKEN_API_KEY" "$BASE/models" |
  "$PYTHON" -c 'import json,sys; print("\n".join(str(x.get("id")) for x in json.load(sys.stdin).get("data",[]) if "gpt" in str(x.get("id","")).lower()))'
  exit 1
fi

python3 - "$FCC_ENV" "$MODEL" <<'PY'
from pathlib import Path
import sys
path, model = Path(sys.argv[1]), sys.argv[2]
path.parent.mkdir(parents=True, exist_ok=True)
values = {
  "HOST": "127.0.0.1", "PORT": "8082", "FCC_OPEN_BROWSER": "false",
  "LLAMACPP_BASE_URL": "http://127.0.0.1:1341/v1", "MODEL": f"llamacpp/{model}",
  "MODEL_FABLE": "", "MODEL_OPUS": "", "MODEL_SONNET": "", "MODEL_HAIKU": "",
}
lines = path.read_text().splitlines() if path.exists() else []
out=[]; seen=set()
for line in lines:
  key=line.split("=",1)[0].strip() if "=" in line else ""
  if key in values: out.append(f'{key}="{values[key]}"'); seen.add(key)
  else: out.append(line)
for key, value in values.items():
  if key not in seen: out.append(f'{key}="{value}"')
path.write_text("\n".join(out).rstrip()+"\n")
PY

for session in army-fcc tooken-proxy; do tmux kill-session -t "$session" 2>/dev/null || true; done
pkill -f 'fcc-server' 2>/dev/null || true
pkill -f 'tooken_proxy.py' 2>/dev/null || true

tmux new-session -d -s tooken-proxy "set -a; . '$SECRET_FILE'; exec '$PYTHON' '$DIR/tooken_proxy.py' >> '$ARMY/logs/tooken-proxy.log' 2>&1"
sleep 2
curl -fsS http://127.0.0.1:1341/health >/dev/null || { tail -30 "$ARMY/logs/tooken-proxy.log"; exit 1; }
tmux new-session -d -s army-fcc "exec /root/.local/bin/fcc-server >> '$ARMY/logs/army-fcc.log' 2>&1"

echo "GPT-5 route configured: $MODEL"
echo "Proxy: http://127.0.0.1:1341/v1"
echo "Start commander: cd /sdcard/ARMY && /root/.local/bin/fcc-claude"
