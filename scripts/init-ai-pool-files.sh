#!/usr/bin/env bash
# Creates private provider-list files. No key is read, copied, or sent anywhere.
set -euo pipefail

# Shared storage so the files are editable in the Android file manager.
# Do not place them in Git or share screenshots containing real keys.
DIR="/sdcard/ARMY/providers"
mkdir -p "$DIR"

make_file() {
  file="$1"
  title="$2"
  protocol="$3"
  cat > "$DIR/$file.providers" <<EOF
# $title
# Protocol expected by this agent: $protocol
# One active provider per line, exactly in this order:
# KEY | URL | PROVIDER
# Example only -- replace all three fields yourself:
# your_key_here | https://gateway.example | provider_name
EOF
  chmod 600 "$DIR/$file.providers"
}

make_file "claude" "Claude Code" "Anthropic Messages"
make_file "opencode" "OpenCode" "OpenAI-compatible or Anthropic adapter"
make_file "goose" "Goose CLI" "OpenAI-compatible or Anthropic-compatible"
make_file "crush" "Crush CLI" "OpenAI-compatible or Anthropic-compatible"
make_file "pi" "Pi Coding Agent" "OpenAI-compatible or Anthropic Messages"
make_file "aider" "Aider" "OpenAI-compatible"
make_file "codex" "Codex CLI" "OpenAI Responses or Chat Completions"
make_file "glm" "GLM terminal agent" "Z.ai / OpenAI-compatible"

cat <<EOF
Provider files editable through Android Files were created in:
  $DIR

Files:
  claude.providers  opencode.providers  goose.providers  crush.providers
  pi.providers      aider.providers     codex.providers  glm.providers

Do not commit this folder to Git and do not send its contents to chat.
EOF
