#!/data/data/com.termux/files/usr/bin/sh
set -eu
BRANCH="arena/019faeb4-ode-kitai"
URL="https://raw.githubusercontent.com/nurislamtagirov444-wq/-Ode-KitAi/${BRANCH}/scripts/setup-tooken-claude-direct.sh"
mkdir -p /sdcard/ARMY/tooken
curl -fsSL "$URL" -o /sdcard/ARMY/tooken/setup-tooken-claude-direct.sh
chmod 700 /sdcard/ARMY/tooken/setup-tooken-claude-direct.sh
proot-distro login debian -- bash /sdcard/ARMY/tooken/setup-tooken-claude-direct.sh
