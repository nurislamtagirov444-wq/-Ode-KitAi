#!/data/data/com.termux/files/usr/bin/sh
# One-time installer. Run this in normal Termux, not inside Debian.
set -eu

BRANCH="arena/019faeb4-ode-kitai"
RAW="https://raw.githubusercontent.com/nurislamtagirov444-wq/-Ode-KitAi/${BRANCH}"
ARMY_DIR="/sdcard/ARMY"
ROUTER_DIR="$ARMY_DIR/router"

command -v proot-distro >/dev/null 2>&1 || { echo "proot-distro is missing."; exit 1; }
command -v curl >/dev/null 2>&1 || { echo "curl is missing. Run: pkg install curl"; exit 1; }

mkdir -p "$ROUTER_DIR" "$ARMY_DIR/logs" "$ARMY_DIR/mission" "$ARMY_DIR/projects"
curl -fsSL "$RAW/tools/g4f_failover_router.py" -o "$ROUTER_DIR/g4f_failover_router.py"
curl -fsSL "$RAW/tools/g4f_failover_routes.example.json" -o "$ROUTER_DIR/routes.json"
curl -fsSL "$RAW/scripts/army-start-debian.sh" -o "$ARMY_DIR/army-start-debian.sh"
curl -fsSL "$RAW/scripts/army-watchdog-debian.sh" -o "$ARMY_DIR/army-watchdog-debian.sh"
chmod 700 "$ROUTER_DIR/g4f_failover_router.py" "$ARMY_DIR/army-start-debian.sh" "$ARMY_DIR/army-watchdog-debian.sh"

proot-distro login debian -- bash -lc 'apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y tmux curl'

cat > "$PREFIX/bin/army-up" <<'EOF'
#!/data/data/com.termux/files/usr/bin/sh
termux-wake-lock >/dev/null 2>&1 || true
proot-distro login debian -- bash /sdcard/ARMY/army-start-debian.sh
cat /sdcard/ARMY/logs/army-status.txt
EOF
chmod 700 "$PREFIX/bin/army-up"

cat > "$PREFIX/bin/army-commander" <<'EOF'
#!/data/data/com.termux/files/usr/bin/sh
proot-distro login debian -- bash -lc 'cd /sdcard/ARMY && /root/.local/bin/fcc-claude'
EOF
chmod 700 "$PREFIX/bin/army-commander"

echo "Installation complete. Starting the army now..."
"$PREFIX/bin/army"
echo ""
echo "Later use: army-up"
echo "Commander use: army-commander"
