#!/usr/bin/env bash
set -euo pipefail

MODEL="${1:-llama3.2:1b}"

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker не найден. Установи Docker и повтори." >&2
  exit 1
fi

if ! docker compose ps ollama >/dev/null 2>&1; then
  echo "Контейнер Ollama не найден. Запусти: docker compose up -d" >&2
  exit 1
fi

echo "Загружаю модель: ${MODEL}"
docker compose exec ollama ollama pull "${MODEL}"
echo "Готово. Модель доступна в Open WebUI и через Ollama API."
