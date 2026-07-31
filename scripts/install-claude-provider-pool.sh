#!/data/data/com.termux/files/usr/bin/sh
set -eu
BRANCH="arena/019faeb4-ode-kitai"
RAW="https://raw.githubusercontent.com/nurislamtagirov444-wq/-Ode-KitAi/${BRANCH}"
mkdir -p /sdcard/ARMY/setup
curl -fsSL "$RAW/tools/claude_provider_pool.py" -o /sdcard/ARMY/setup/claude_provider_pool.py
curl -fsSL "$RAW/scripts/setup-claude-provider-pool.sh" -o /sdcard/ARMY/setup/setup-claude-provider-pool.sh
chmod 700 /sdcard/ARMY/setup/claude_provider_pool.py /sdcard/ARMY/setup/setup-claude-provider-pool.sh
proot-distro login debian -- bash /sdcard/ARMY/setup/setup-claude-provider-pool.sh
