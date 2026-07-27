# Ode KitAi: Arena Agent Prompt + Local AI Kit

Публичный репозиторий с готовым промптом для Arena AI Agent Mode и локальным AI-kit: запуск open-source моделей, подключение «модов»/плагинов из GitHub и работа без платных API-лимитов.

> Важно: полностью **бесплатной, облачной, безлимитной и быстрой** среды не бывает. Всегда есть лимит: железо, RAM/VRAM, электричество, правила сервиса или скорость. Самый близкий вариант к «безлимиту» — связка бесплатного облака и локальной модели: пока есть суточный лимит, работает быстрое облако, а когда он кончился, запрос автоматически уходит на локальную модель.

## Быстрый старт за три команды

```bash
python3 kitai_cli.py setup     # пошаговая инструкция под твою систему
python3 kitai_cli.py doctor    # проверить, что реально работает
python3 kitai_cli.py ask "привет"
```

Зависимостей нет: только стандартная библиотека Python 3.9+. Никакого `pip install`.

Полная инструкция для новичка: [`docs/QUICKSTART_RU.md`](docs/QUICKSTART_RU.md)

## Три вещи, которые делает этот набор

### 1. Бесплатный доступ к моделям

Пять способов в одном каталоге `config/providers.json`, все лимиты взяты из официальной документации:

| Провайдер | Тип | Лимит бесплатного уровня | Карта |
|---|---|---|---|
| Ollama | локально | нет лимита запросов, упирается в железо | не нужна |
| Groq | облако | 30 запросов/мин, до 14 400/сутки на `llama-3.1-8b-instant` | не нужна |
| Google AI Studio | облако | меняется, смотри [rate-limit](https://aistudio.google.com/rate-limit) | не нужна |
| GitHub Models | облако | ~10 запросов/мин, ~50/сутки (public preview) | не нужна |
| OpenRouter | облако | 20/мин и 50/сутки на моделях `:free` | не нужна |

Ключи хранятся только в `.env` (он в `.gitignore`) и никогда не печатаются целиком:

```bash
python3 kitai_cli.py key set GROQ_API_KEY   # ввод скрыт
python3 kitai_cli.py key list               # показывает маску, не значение
```

### 2. Загрузка модификаций агенту

```bash
python3 kitai_cli.py mods list
python3 kitai_cli.py mods install web-fetch      # /web URL — чтение сайтов
python3 kitai_cli.py mods install notes          # /note — заметки
python3 kitai_cli.py mods install strategy-tools # /strategy — профили из чата
```

Правило безопасности: **скачать не значит запустить**. Моды-репозитории клонируются
в `mods/` и никогда не выполняются автоматически. Разрешены только HTTPS и только
хосты `github.com`, `gitlab.com`, `codeberg.org`.

### 3. Настройка стратегии

Стратегия — порядок провайдеров и поведение при отказе. Если пришёл `429`
(лимит кончился), запрос автоматически уходит следующему в цепочке.

```bash
python3 kitai_cli.py strategy            # список профилей
python3 kitai_cli.py strategy use fast_free
python3 kitai_cli.py strategy plan       # кто сработает первым и почему
```

| Профиль | Цепочка |
|---|---|
| `balanced` (по умолчанию) | groq → gemini → github → openrouter → ollama |
| `fast_free` | groq → groq 70B → gemini → ollama |
| `private_local` | только ollama, наружу ничего не уходит |
| `deep_research` | gemini → groq 70B → github → mistral |
| `android` | groq → gemini lite → openrouter |

Все облачные профили заканчиваются локальной моделью — она не кончается.

## Что уже есть в этом репозитории

- `kitai_cli.py` — единая точка входа: setup, doctor, ask, key, mods, strategy.
- `kitai/` — ядро: провайдеры, роутер стратегии, менеджер модов, встроенные моды.
- `config/providers.json` — каталог бесплатных провайдеров с реальными лимитами.
- `config/strategy.json` — профили стратегии и формат ответов.
- `config/mods-registry.json` — реестр модификаций агента.
- `tests/` — 37 тестов, запуск `python3 -m unittest discover -s tests -v`.
- `docker-compose.yml` — локальный запуск Ollama + Open WebUI.
- `docker-compose.gpu.yml` — опциональный GPU-оверрайд для NVIDIA.
- `local_agent.py` — простой локальный агент на Python с плагинами.
- `plugins/` — примеры плагинов: калькулятор, клонирование репозиториев, чтение README.
- `scripts/` — удобные скрипты для загрузки модели и клонирования модификаций.
- `docs/QUICKSTART_RU.md` — быстрый старт с нуля по шагам.
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

## Проверка перед изменениями

```bash
python3 -m unittest discover -s tests -v   # 37 тестов
python3 -m py_compile kitai_cli.py kitai/*.py plugins/*.py
```

## Главное правило безопасности

Клонировать код с GitHub можно, но **не запускай незнакомый код без проверки**. Лучше запускать модификации в Docker-контейнере или отдельной виртуальной среде.

Что этот набор не делает:

- не создаёт мультиаккаунты и не обходит лимиты провайдеров;
- не запускает скачанный чужой код автоматически;
- не печатает ключи целиком — только маску вида `gsk_...ab`;
- не даёт моду `web-fetch` ходить по локальной сети и служебным адресам.

Подробный план смотри в [`docs/QUICKSTART_RU.md`](docs/QUICKSTART_RU.md) и [`docs/FREE_LIMITLESS_AI_RU.md`](docs/FREE_LIMITLESS_AI_RU.md).
