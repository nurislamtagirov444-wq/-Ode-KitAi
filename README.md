# Ode KitAi: Arena Agent Prompt + Local AI Kit

Публичный репозиторий с готовым промптом для Arena AI Agent Mode и локальным AI-kit: запуск open-source моделей, подключение «модов»/плагинов из GitHub и работа без платных API-лимитов.

> Важно: полностью **бесплатной, облачной, безлимитной и быстрой** среды не бывает. Всегда есть лимит: железо, RAM/VRAM, электричество, правила сервиса или скорость. Самый близкий вариант к «безлимиту» — запускать модель локально на своём ПК/сервере и подключаться к ней с Android через браузер.

## Что уже есть в этом репозитории

- `docker-compose.yml` — локальный запуск Ollama + Open WebUI.
- `docker-compose.gpu.yml` — опциональный GPU-оверрайд для NVIDIA.
- `local_agent.py` — простой локальный агент на Python с плагинами.
- `plugins/` — примеры плагинов: калькулятор, клонирование репозиториев, чтение README.
- `scripts/` — удобные скрипты для загрузки модели и клонирования модификаций.
- `docs/FREE_LIMITLESS_AI_RU.md` — подробная инструкция на русском.
- `docs/ANDROID_RU.md` — как использовать это с Android без лагов.
- `docs/GITHUB_ACCESS_RU.md` — как дать агенту доступ читать GitHub.
- `prompts/arena-agent-mode-strategist-ru.md` — готовый промпт для Arena AI Agent Mode.
- `AGENTS.md` — короткие инструкции для coding agents, которые умеют читать этот файл.

## Как дать агенту доступ читать GitHub

Короткая инструкция лежит здесь:

```text
docs/GITHUB_ACCESS_RU.md
```

Главное правило: публичный репозиторий достаточно отправить ссылкой. Для приватного репозитория используй GitHub-интеграцию Arena или прикрепляй нужные файлы. Не отправляй токены, пароли, cookies и SSH-ключи в чат.

## Промпт для Arena AI Agent Mode

Главный файл для копирования:

```text
PROMPT.md
```

Расширенная версия с пояснениями:

```text
prompts/arena-agent-mode-strategist-ru.md
```

Скопируй промпт в первый запрос Arena или в Custom Instructions, если они доступны. Просто положить промпт в репозиторий обычно недостаточно: агент может не читать его автоматически.

## Быстрый старт: Open WebUI + Ollama

### 1. Установи Docker

Нужен Docker Desktop / Docker Engine с Compose.

### 2. Запусти окружение

```bash
docker compose up -d
```

Открой в браузере:

```text
http://localhost:3000
```

### 3. Скачай модель

Для слабого железа начни с маленькой модели:

```bash
./scripts/pull-model.sh llama3.2:1b
```

Для ПК получше можно попробовать:

```bash
./scripts/pull-model.sh llama3.2:3b
```

### 4. Подключайся с Android

Если ПК и телефон в одной Wi‑Fi сети:

```bash
hostname -I
```

Открой на телефоне:

```text
http://IP_ТВОЕГО_ПК:3000
```

Так телефон не тянет модель сам — он только показывает интерфейс, поэтому Android не должен лагать из-за инференса.

## GPU-вариант

Если есть NVIDIA GPU и установлен NVIDIA Container Toolkit:

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d
```

## Локальный агент с плагинами

Запуск:

```bash
python3 local_agent.py
```

Примеры команд внутри агента:

```text
/help
/calc 2 + 2 * 10
/github_clone https://github.com/open-webui/open-webui.git
/readme mods/open-webui
```

Если вводить обычный текст без `/`, агент отправит вопрос в локальный Ollama API.

## Как добавлять свои плагины

Создай файл в `plugins/`, например `plugins/my_tool.py`:

```python
COMMAND = "my_tool"
HELP = "/my_tool текст — пример своего плагина"


def handle(args: str, context: dict) -> str:
    return f"Ты передал: {args}"
```

Перезапусти `python3 local_agent.py` и команда `/my_tool` появится в `/help`.

## Главное правило безопасности

Клонировать код с GitHub можно, но **не запускай незнакомый код без проверки**. Лучше запускать модификации в Docker-контейнере или отдельной виртуальной среде.

Подробный план смотри в [`docs/FREE_LIMITLESS_AI_RU.md`](docs/FREE_LIMITLESS_AI_RU.md).
