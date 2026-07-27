#!/usr/bin/env bash
set -euo pipefail

HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-7860}"
OLLAMA_URL="${OLLAMA_URL:-http://localhost:11434}"

export OLLAMA_URL

echo "Запускаю Ode KitAi сайт"
echo "URL на этом устройстве: http://localhost:${PORT}"
echo "Для Android в той же Wi-Fi сети открой: http://IP_ПК:${PORT}"
echo "Ollama URL: ${OLLAMA_URL}"

python3 web/server.py --host "${HOST}" --port "${PORT}"
