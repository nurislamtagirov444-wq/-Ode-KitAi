#!/data/data/com.termux/files/usr/bin/sh
# Run in normal Termux. It downloads no credentials and then starts a local hidden-key setup.
set -eu
BRANCH="arena/019faeb4-ode-kitai"
RAW="https://raw.githubusercontent.com/nurislamtagirov444-wq/-Ode-KitAi/${BRANCH}"
DIR="/sdcard/ARMY/tooken"
mkdir -p "$DIR" /sdcard/ARMY/logs /sdcard/ARMY/projects /sdcard/ARMY/mission
curl -fsSL "$RAW/tools/tooken_proxy.py" -o "$DIR/tooken_proxy.py"
curl -fsSL "$RAW/scripts/setup-tooken-gpt5-debian.sh" -o "$DIR/setup-tooken-gpt5-debian.sh"
chmod 700 "$DIR/tooken_proxy.py" "$DIR/setup-tooken-gpt5-debian.sh"
proot-distro login debian -- bash "$DIR/setup-tooken-gpt5-debian.sh"
