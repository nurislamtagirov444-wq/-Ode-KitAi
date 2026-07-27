"""Пути, чтение .env и загрузка JSON-конфигов.

Никаких внешних зависимостей: .env читается вручную, конфиги в JSON,
потому что json есть в стандартной библиотеке, а PyYAML — нет.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE_DIR / "config"
PLUGIN_DIR = BASE_DIR / "plugins"
MODS_DIR = BASE_DIR / "mods"
STATE_DIR = BASE_DIR / ".kitai_state"

PROVIDERS_FILE = CONFIG_DIR / "providers.json"
STRATEGY_FILE = CONFIG_DIR / "strategy.json"
MODS_REGISTRY_FILE = CONFIG_DIR / "mods-registry.json"
MODS_STATE_FILE = STATE_DIR / "mods.json"
USAGE_STATE_FILE = STATE_DIR / "usage.json"
ENV_FILE = BASE_DIR / ".env"

# Ключи, которые нельзя печатать в логах целиком.
SECRET_HINTS = ("KEY", "TOKEN", "SECRET", "PASSWORD")


def is_secret_name(name: str) -> bool:
    upper = name.upper()
    return any(hint in upper for hint in SECRET_HINTS)


def mask_secret(value: Optional[str]) -> str:
    """Показать, что ключ есть, но не показать сам ключ."""
    if not value:
        return "не задан"
    value = value.strip()
    if len(value) <= 8:
        return "задан (короткий)"
    return f"задан ({value[:4]}...{value[-2:]}, длина {len(value)})"


def parse_env_text(text: str) -> Dict[str, str]:
    """Минимальный парсер .env: KEY=VALUE, # комментарии, кавычки."""
    result: Dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            continue
        name, _, value = line.partition("=")
        name = name.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        if name:
            result[name] = value
    return result


def load_env(env_file: Path = ENV_FILE, *, override: bool = False) -> Dict[str, str]:
    """Подгрузить .env в os.environ. Существующие переменные не затираем."""
    if not env_file.exists():
        return {}
    values = parse_env_text(env_file.read_text(encoding="utf-8", errors="replace"))
    for name, value in values.items():
        if override or name not in os.environ:
            os.environ[name] = value
    return values


def load_json(path: Path) -> Any:
    if not path.exists():
        raise FileNotFoundError(f"Файл конфигурации не найден: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Битый JSON в {path}: {exc}") from exc


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def load_json_or_default(path: Path, default: Any) -> Any:
    try:
        return load_json(path)
    except (FileNotFoundError, ValueError):
        return default


def ensure_dirs() -> None:
    for directory in (CONFIG_DIR, PLUGIN_DIR, MODS_DIR, STATE_DIR):
        directory.mkdir(parents=True, exist_ok=True)
