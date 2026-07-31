#!/data/data/com.termux/files/usr/bin/sh
set -eu
BRANCH="arena/019faeb4-ode-kitai"
RAW="https://raw.githubusercontent.com/nurislamtagirov444-wq/-Ode-KitAi/${BRANCH}"
mkdir -p /sdcard/ARMY/setup
curl -fsSL "$RAW/tools/select_claude_provider.py" -o /sdcard/ARMY/setup/select_claude_provider.py
chmod 700 /sdcard/ARMY/setup/select_claude_provider.py
proot-distro login debian -- bash -lc '
  /root/g4f-venv/bin/python -m pip install -q -U httpx
  pkill -f "[c]laude_provider_pool.py" 2>/dev/null || true
  pkill -f "[f]cc-server" 2>/dev/null || true
  cat > /usr/local/bin/claude-select <<"EOF"
#!/usr/bin/env bash
set -e
/root/g4f-venv/bin/python /sdcard/ARMY/setup/select_claude_provider.py
chown worker:worker /home/worker/.claude/settings.json
exec su - worker -s /bin/bash -c "/home/worker/bin/claude-auto"
EOF
  chmod 755 /usr/local/bin/claude-select
  echo "No-server mode ready. Start with: claude-select"
'
