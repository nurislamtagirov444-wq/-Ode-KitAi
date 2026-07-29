# Автопереключатель g4f-мостов для FCC

## Зачем

`g4f api` может отдавать много моделей, но конкретный провайдер в любой момент может зависнуть или вернуть 5xx. Этот небольшой локальный прокси ставится между FCC и g4f:

```text
FCC -> http://127.0.0.1:1340/v1 -> failover router -> g4f :1337 -> провайдеры
```

Для одного запроса он перебирает мосты в заданном порядке. Если мост вернул HTTP-ошибку или не ответил за `request_timeout_seconds`, берётся следующий.

Ограничение: после того как потоковый ответ уже начал приходить, безопасно переключить его на другой мост невозможно. Переключение работает до начала ответа.

## Модели и мосты

Начальный файл `tools/g4f_failover_routes.example.json` построен на текущем списке `g4f-working`:

- `WeWordle / gpt-4o`;
- `WeWordle / gpt-4`;
- `Yqcloud / gpt-4`;
- `HuggingSpace / command-a`;
- `AnyProvider` — последний запасной маршрут.

Список меняется ежедневно. Перед добавлением нового моста смотри актуальный файл:

```bash
curl -sL https://raw.githubusercontent.com/maruf009sultan/g4f-working/refs/heads/main/working/working_results.txt
```

Строка формата `Provider|Model|text` может стать одной записью вида:

```json
{ "provider": "Provider", "model": "Model" }
```

в списке маршрутов нужной модели.

## Запуск на Debian в Termux

Скопируй скрипт и пример конфигурации в одну папку на телефоне. Внутри Debian, где уже работает g4f, выполни:

```bash
mkdir -p /sdcard/ARMY/router
cp g4f_failover_router.py /sdcard/ARMY/router/
cp g4f_failover_routes.example.json /sdcard/ARMY/router/routes.json
```

Запусти его отдельной Termux-сессией, не останавливая `g4f api` и `fcc-server`:

```bash
proot-distro login debian
/root/g4f-venv/bin/python /sdcard/ARMY/router/g4f_failover_router.py --config /sdcard/ARMY/router/routes.json
```

Ожидаемый адрес — `http://127.0.0.1:1340`.

Проверка:

```bash
curl -s http://127.0.0.1:1340/health
```

## Настройка FCC

В FCC Admin UI (`http://127.0.0.1:8082/admin`):

1. **Providers** -> `llama.cpp Base URL`:

   ```text
   http://127.0.0.1:1340/v1
   ```

2. **Model Config** -> `Default Model`:

   ```text
   llamacpp/gpt-4o
   ```

3. Оставь `Fable Override`, `Opus Override`, `Sonnet Override` и `Haiku Override` равными `None`.
4. Нажми `Apply`, затем `Validate`.
5. Перезапусти только `fcc-claude`; окна g4f, FCC и роутера не останавливай.

## Безопасность и диагностика

- Прокси не пишет в лог текст запросов и не требует ключей.
- Не добавляй мосты, которые не показаны в свежем `working_results.txt`.
- Если все варианты провалились, FCC получит понятную ошибку с именами безуспешных мостов.
- Не отправляй пароли, токены, личные данные или финансовые данные через публичные/бесплатные мосты.
