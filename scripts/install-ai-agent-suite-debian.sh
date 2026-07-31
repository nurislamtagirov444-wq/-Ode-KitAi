#!/usr/bin/env bash
# Installs terminal coding agents in the existing Debian environment.
set -u
LOG="/sdcard/ARMY/logs/agent-suite-install.log"
mkdir -p /sdcard/ARMY/logs
: > "$LOG"

install_npm() {
  package="$1"
  printf 'Installing %s ...\n' "$package" | tee -a "$LOG"
  npm install -g "$package" >> "$LOG" 2>&1 && printf 'OK: %s\n' "$package" | tee -a "$LOG" || printf 'FAILED: %s\n' "$package" | tee -a "$LOG"
}

install_npm "@anthropic-ai/claude-code"
install_npm "@openai/codex"
install_npm "opencode-ai"
install_npm "@charmland/crush"
install_npm "@mariozechner/pi-coding-agent"
install_npm "@guizmo-ai/zai-cli"

if [ -x /root/g4f-venv/bin/python ]; then
  printf 'Installing aider-chat ...\n' | tee -a "$LOG"
  /root/g4f-venv/bin/python -m pip install -U aider-chat >> "$LOG" 2>&1 && echo 'OK: aider-chat' | tee -a "$LOG" || echo 'FAILED: aider-chat' | tee -a "$LOG"
else
  echo 'SKIPPED: aider-chat (g4f Python not found)' | tee -a "$LOG"
fi

echo '' | tee -a "$LOG"
echo 'Installed command check:' | tee -a "$LOG"
for command in claude codex opencode crush pi zai aider; do
  if command -v "$command" >/dev/null 2>&1; then
    printf '%s: %s\n' "$command" "$(command -v "$command")" | tee -a "$LOG"
  else
    printf '%s: NOT FOUND\n' "$command" | tee -a "$LOG"
  fi
done

echo "Log: $LOG" | tee -a "$LOG"
