#!/usr/bin/env bash
set -euo pipefail

URL="${1:-}"
TARGET="${2:-}"

if [[ -z "${URL}" ]]; then
  echo "Использование: ./scripts/clone-mod.sh <git-url> [target-name]" >&2
  echo "Пример: ./scripts/clone-mod.sh https://github.com/open-webui/open-webui.git" >&2
  exit 1
fi

mkdir -p mods

if [[ -z "${TARGET}" ]]; then
  TARGET="$(basename "${URL}" .git)"
fi

DEST="mods/${TARGET}"

if [[ -e "${DEST}" ]]; then
  echo "Папка уже существует: ${DEST}" >&2
  exit 1
fi

echo "Клонирую ${URL} -> ${DEST}"
git clone --depth 1 "${URL}" "${DEST}"

echo "Готово. Проверь README и код перед запуском: ${DEST}"
