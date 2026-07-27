# Ode KitAi: Arena Agent Prompt + Local AI Kit

Публичный репозиторий с готовым промптом для Arena AI Agent Mode и AI-сайтом: no-download режим через удалённые free-tier провайдеры, опциональный локальный Ollama, GitHub-моды и плагины.

> Важно: если не хочешь скачивать модель, используй no-download провайдеры в сайте: Pollinations, Puter.js, OpenRouter/Groq через свои ключи или свой OpenAI-compatible endpoint. Абсолютный безлимит не обещается: у удалённых AI обычно есть лимиты по запросам, токенам, скорости, аккаунту и правилам сервиса.

## Что уже есть в этом репозитории

- `docker-compose.yml` — запуск AI-сайта, Ollama и Open WebUI.
- `docker-compose.gpu.yml` — опциональный GPU-оверрайд для NVIDIA, если всё-таки нужен локальный Ollama.
- `web/` — готовый AI-сайт с no-download провайдерами, чатом, настройками и каталогом GitHub-модов.
- `local_agent.py` — простой локальный агент на Python с плагинами.
- `plugins/` — примеры плагинов: калькулятор, клонирование репозиториев, чтение README.
- `scripts/` — удобные скрипты для запуска сайта, загрузки модели и клонирования модификаций.
- `docs/NO_DOWNLOAD_FREE_AI_RU.md` — как пользоваться AI без скачивания модели.
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

## Быстрый старт без скачивания модели

### 1. Запусти сайт

Если есть Python:

```bash
./scripts/start-ai-site.sh
```

Или через Docker:

```bash
docker compose up -d ai-site
```

### 2. Открой сайт

```text
http://localhost:7860
```

### 3. Выбери no-download провайдера

В правой панели сайта по умолчанию выбран:

```text
No-download: Puter.js в браузере
```

Модель скачивать не нужно. Нужен только интернет. Puter.js может попросить вход в Puter.

Если Puter.js не подходит, попробуй:

```text
No-download: Pollinations
```

### 4. Опционально: OpenRouter/Groq

Если у тебя есть API key, не отправляй его в чат. Задай его локально в терминале перед запуском сайта:

```bash
OPENROUTER_API_KEY="твой_ключ" ./scripts/start-ai-site.sh
```

Или:

```bash
GROQ_API_KEY="твой_ключ" ./scripts/start-ai-site.sh
```

### 5. Подключайся с Android

Если ПК и телефон в одной Wi‑Fi сети:

```bash
hostname -I
```

Открой свой AI-сайт на телефоне:

```text
http://IP_ТВОЕГО_ПК:7860
```

Или Open WebUI:

```text
http://IP_ТВОЕГО_ПК:3000
```

Так телефон не тянет модель сам — он только показывает интерфейс. В no-download режиме модель вообще не скачивается на твой ПК: запрос уходит к выбранному удалённому провайдеру.

## Опционально: локальный Ollama

Если когда-нибудь захочешь локальный режим без удалённых провайдеров:

```bash
docker compose --profile local up -d ollama open-webui
./scripts/pull-model.sh llama3.2:1b
```

Open WebUI будет доступен:

```text
http://localhost:3000
```

## GPU-вариант

Если есть NVIDIA GPU и установлен NVIDIA Container Toolkit:

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d
```

## Свой AI-сайт

Файлы сайта лежат в папке:

```text
web/
```

Запуск без Docker. Ollama не обязателен, если выбран Pollinations или Puter.js:

```bash
./scripts/start-ai-site.sh
```

Открыть:

```text
http://localhost:7860
```

Внутри сайта есть:

- чат через no-download провайдеры или локальный Ollama;
- выбор провайдера: Pollinations, Puter.js, OpenRouter, Groq, свой OpenAI-compatible API, Ollama;
- настройки модели, temperature, context, длины ответа;
- системный промпт;
- готовые режимы: стратег, GitHub-аудитор, Android без лагов, AI без скачивания модели;
- каталог GitHub-модов с командами клонирования.

Подробно: [`web/README_RU.md`](web/README_RU.md).

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
