# Ode KitAi Web

Это простой сайт для AI без обязательного скачивания модели. Он работает с несколькими режимами:

- `Pollinations` — no-download режим через интернет, без локальной модели;
- `Puter.js` — no-download режим прямо в браузере, может попросить вход в Puter;
- `OpenRouter` — no-download режим через `OPENROUTER_API_KEY` в env сервера;
- `Groq` — no-download режим через `GROQ_API_KEY` в env сервера;
- `Custom OpenAI-compatible` — любой совместимый endpoint;
- `Ollama` — опциональный локальный режим, если сам захочешь скачать модель.

По умолчанию включён `Puter.js`, поэтому Ollama и скачанная модель не обязательны. Если Puter.js не подходит, можно переключиться на `Pollinations`.

## Быстрый запуск без Docker

Из корня репозитория:

```bash
./scripts/start-ai-site.sh
```

Открыть на ПК:

```text
http://localhost:7860
```

Открыть на Android в той же Wi‑Fi сети:

```text
http://IP_ПК:7860
```

## Быстрый запуск через Docker

```bash
docker compose up -d ai-site
```

Открыть сайт:

```text
http://localhost:7860
```

## Если нужен OpenRouter или Groq

Не вставляй API key в чат. Задавай его локально в терминале:

```bash
OPENROUTER_API_KEY="твой_ключ" ./scripts/start-ai-site.sh
```

Или:

```bash
GROQ_API_KEY="твой_ключ" ./scripts/start-ai-site.sh
```

Потом в интерфейсе выбери нужного провайдера.

## Если нужен свой OpenAI-compatible endpoint

```bash
OPENAI_COMPATIBLE_BASE_URL="https://example.com/v1" \
OPENAI_COMPATIBLE_API_KEY="твой_ключ_если_нужен" \
./scripts/start-ai-site.sh
```

В интерфейсе выбери:

```text
No-download: свой OpenAI-compatible API
```

## Если всё-таки нужен локальный Ollama

Это опционально. Только если сам захочешь локальный режим:

```bash
docker compose --profile local up -d ollama
./scripts/pull-model.sh llama3.2:1b
```

Потом в сайте выбери:

```text
Local: Ollama
```

## Настройки модели

В интерфейсе можно менять:

- провайдера;
- модель;
- temperature;
- размер контекста;
- максимум ответа;
- системный промпт.

Для no-download режима модель вводится как ID провайдера, а не как файл для скачивания.

## GitHub-моды

Сайт содержит каталог `web/config/mods.json`. Он показывает полезные open-source проекты и команды клонирования. Сайт не запускает чужой код автоматически.

Чтобы добавить мод в каталог, добавь объект в `web/config/mods.json`:

```json
{
  "name": "Название",
  "category": "webui",
  "repo": "https://github.com/user/repo",
  "description": "Что делает проект",
  "tags": ["tag1", "tag2"],
  "risk": "Что проверить перед запуском"
}
```

## Про 100–200 GB

AI-сервисы обычно считают лимиты не в гигабайтах, а в:

- токенах;
- запросах в минуту/день;
- размере контекста;
- времени GPU;
- кредитах аккаунта;
- правилах fair-use.

100–200 GB трафика не равно 100–200 GB AI-вычислений. Поэтому сайт сделан с несколькими провайдерами: если один упёрся в лимит, можно переключиться на другой легальный вариант.

## Безопасность

- Не открывай сайт в интернет без авторизации и HTTPS.
- Для доступа с телефона из другой сети лучше используй Tailscale или ZeroTier.
- Не вставляй токены, пароли, cookies и приватные ключи в чат.
- Не запускай неизвестные GitHub-проекты без чтения README и проверки зависимостей.
