#!/data/data/com.termux/files/usr/bin/sh
# Run once from the normal Termux app, NOT from proot Debian.
# It creates a Termux:Widget background shortcut named ARMY-START.
set -eu

BRANCH="arena/019faeb4-ode-kitai"
RAW="https://raw.githubusercontent.com/nurislamtagirov444-wq/-Ode-KitAi/${BRANCH}"
ARMY_DIR="/sdcard/ARMY"
ROUTER_DIR="$ARMY_DIR/router"
SHORTCUT_DIR="$HOME/.shortcuts/tasks"

command -v proot-distro >/dev/null 2>&1 || {
  echo "proot-distro is missing in Termux."
  exit 1
}
command -v curl >/dev/null 2>&1 || {
  echo "curl is missing in Termux. Run: pkg install curl"
  exit 1
}

mkdir -p "$ROUTER_DIR" "$ARMY_DIR/logs" "$ARMY_DIR/mission" "$ARMY_DIR/projects" "$SHORTCUT_DIR"

curl -fsSL "$RAW/tools/g4f_failover_router.py" -o "$ROUTER_DIR/g4f_failover_router.py"
curl -fsSL "$RAW/tools/g4f_failover_routes.example.json" -o "$ROUTER_DIR/routes.json"
curl -fsSL "$RAW/scripts/army-start-debian.sh" -o "$ARMY_DIR/army-start-debian.sh"
chmod 700 "$ROUTER_DIR/g4f_failover_router.py" "$ARMY_DIR/army-start-debian.sh"

# tmux keeps the three local services alive after the shortcut has returned.
proot-distro login debian -- bash -lc 'apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y tmux curl'

cat > "$SHORTCUT_DIR/ARMY-START" <<'EOF'
#!/data/data/com.termux/files/usr/bin/sh
termux-wake-lock >/dev/null 2>&1 || true
proot-distro login debian -- bash /sdcard/ARMY/army-start-debian.sh
EOF
chmod 700 "$SHORTCUT_DIR/ARMY-START"

cat > "$SHORTCUT_DIR/ARMY-STATUS" <<'EOF'
#!/data/data/com.termux/files/usr/bin/sh
proot-distro login debian -- cat /sdcard/ARMY/logs/army-status.txt
EOF
chmod 700 "$SHORTCUT_DIR/ARMY-STATUS"

cat <<EOF
One-time installation is complete.

Manual Android steps left:
1. Install and open Termux:Widget once.
2. Add its widget to the home screen.
3. Select ARMY-START in the widget.

After that, one tap on ARMY-START starts/checks g4f, the failover router,
and FCC. Status is written to:
  /sdcard/ARMY/logs/army-status.txt
EOF
