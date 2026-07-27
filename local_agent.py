#!/usr/bin/env python3
"""
Мини-агент для локальной модели Ollama + простая система плагинов.

Обычный текст отправляется в локальную модель.
Команды вида /calc, /github_clone, /readme обрабатываются плагинами из ./plugins.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Callable

BASE_DIR = Path(__file__).resolve().parent
PLUGIN_DIR = BASE_DIR / "plugins"
MODS_DIR = BASE_DIR / "mods"

DEFAULT_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2:1b")
DEFAULT_OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")


@dataclass(frozen=True)
class Plugin:
    command: str
    help: str
    handle: Callable[[str, dict], str]


def load_module(path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Не могу загрузить плагин: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_plugins() -> dict[str, Plugin]:
    plugins: dict[str, Plugin] = {}
    PLUGIN_DIR.mkdir(exist_ok=True)

    for path in sorted(PLUGIN_DIR.glob("*.py")):
        if path.name.startswith("_"):
            continue
        try:
            module = load_module(path)
            command = getattr(module, "COMMAND")
            help_text = getattr(module, "HELP", f"/{command} — без описания")
            handle = getattr(module, "handle")
        except Exception as exc:  # noqa: BLE001 - показываем ошибку плагина пользователю
            print(f"[plugin:{path.name}] ошибка загрузки: {exc}", file=sys.stderr)
            continue

        if not isinstance(command, str) or not command:
            print(f"[plugin:{path.name}] COMMAND должен быть непустой строкой", file=sys.stderr)
            continue
        if not callable(handle):
            print(f"[plugin:{path.name}] handle должен быть функцией", file=sys.stderr)
            continue

        plugins[command] = Plugin(command=command, help=str(help_text), handle=handle)

    return plugins


def ask_ollama(prompt: str, *, model: str, ollama_url: str) -> str:
    url = ollama_url.rstrip("/") + "/api/chat"
    payload = {
        "model": model,
        "stream": False,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Ты локальный помощник. Отвечай кратко, практично и по-русски. "
                    "Если не уверен, предложи безопасный способ проверки."
                ),
            },
            {"role": "user", "content": prompt},
        ],
    }
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=180) as response:  # noqa: S310 - локальный URL
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        return (
            "Не могу подключиться к Ollama. Проверь, что окружение запущено:\n"
            "  docker compose up -d\n"
            f"Техническая ошибка: {exc}"
        )

    message = data.get("message", {})
    content = message.get("content")
    if isinstance(content, str) and content.strip():
        return content.strip()
    return f"Ollama вернул неожиданный ответ: {data}"


def print_help(plugins: dict[str, Plugin], *, model: str, ollama_url: str) -> None:
    print("\nКоманды:")
    print("  /help — показать помощь")
    print("  /exit — выйти")
    for plugin in plugins.values():
        print(f"  {plugin.help}")
    print("\nОбычный текст без / отправляется в локальную модель Ollama.")
    print(f"Модель: {model}")
    print(f"Ollama URL: {ollama_url}\n")


def main() -> int:
    model = DEFAULT_MODEL
    ollama_url = DEFAULT_OLLAMA_URL
    MODS_DIR.mkdir(exist_ok=True)

    plugins = load_plugins()
    context = {
        "base_dir": BASE_DIR,
        "mods_dir": MODS_DIR,
        "model": model,
        "ollama_url": ollama_url,
    }

    print("Ode KitAi local agent")
    print("Напиши /help для списка команд, /exit для выхода.")

    while True:
        try:
            user_input = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nВыход.")
            return 0

        if not user_input:
            continue
        if user_input in {"/exit", "/quit"}:
            print("Выход.")
            return 0
        if user_input == "/help":
            print_help(plugins, model=model, ollama_url=ollama_url)
            continue

        if user_input.startswith("/"):
            command_line = user_input[1:]
            command, _, args = command_line.partition(" ")
            plugin = plugins.get(command)
            if plugin is None:
                print(f"Неизвестная команда: /{command}. Напиши /help.")
                continue
            try:
                result = plugin.handle(args.strip(), context)
            except Exception as exc:  # noqa: BLE001 - CLI должен не падать от плагина
                result = f"Ошибка плагина /{command}: {exc}"
            print(result)
            continue

        print(ask_ollama(user_input, model=model, ollama_url=ollama_url))


if __name__ == "__main__":
    raise SystemExit(main())
