#!/data/data/com.termux/files/usr/bin/sh
set -eu
BRANCH="arena/019faeb4-ode-kitai"
URL="https://raw.githubusercontent.com/nurislamtagirov444-wq/-Ode-KitAi/${BRANCH}/scripts/setup-claude-worker-auto.sh"
mkdir -p /sdcard/ARMY/setup
curl -fsSL "$URL" -o /sdcard/ARMY/setup/setup-claude-worker-auto.sh
chmod 700 /sdcard/ARMY/setup/setup-claude-worker-auto.sh
proot-distro login debian -- bash /sdcard/ARMY/setup/setup-claude-worker-auto.sh
