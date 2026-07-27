# Android-only AI-сайт без участия ПК

Это самый прямой вариант под требование: не скачивать модель и не использовать ПК.

## Схема

```text
Android-браузер
        ↓
GitHub Pages site
        ↓
Puter.js или Pollinations
        ↓
ответ AI
```

ПК не нужен. Docker не нужен. Ollama не нужен. Локальная модель не нужна.

## Где сайт

Статический сайт лежит в файле:

```text
docs/index.html
```

Когда GitHub Pages включён из папки `docs`, сайт должен открываться по адресу вида:

```text
https://nurislamtagirov444-wq.github.io/-Ode-KitAi/
```

## Как включить GitHub Pages с Android

1. Открой репозиторий на GitHub в браузере:

```text
https://github.com/nurislamtagirov444-wq/-Ode-KitAi
```

2. Открой `Settings`.
3. Найди раздел `Pages`.
4. В `Build and deployment` выбери:

```text
Source: Deploy from a branch
Branch: arena/019fa3e3-ode-kitai
Folder: /docs
```

5. Нажми `Save`.
6. Подожди 1–3 минуты.
7. Открой сайт:

```text
https://nurislamtagirov444-wq.github.io/-Ode-KitAi/
```

Если GitHub не даёт выбрать ветку `arena/019fa3e3-ode-kitai`, сначала смёрджи Pull Request в `main`, потом выбери:

```text
Branch: main
Folder: /docs
```

## Как пользоваться

1. Открой сайт на Android.
2. Оставь провайдера:

```text
Puter.js — без ПК
```

3. Нажми `Отправить` с любым вопросом.
4. Если появится окно Puter — войди или зарегистрируйся.
5. Если Puter не работает — выбери:

```text
Pollinations — запасной режим
```

## Что важно понимать

100–200 GB — это трафик. AI-провайдеры обычно ограничивают не гигабайты, а:

- запросы;
- токены;
- скорость;
- контекст;
- fair-use;
- доступные модели.

Поэтому в сайте два режима: основной Puter.js и запасной Pollinations. При желании можно позже добавить другие browser-only провайдеры.

## Безопасность

Не вводи в чат:

- пароли;
- токены;
- cookies;
- SSH-ключи;
- коды 2FA;
- данные карты;
- паспортные данные.
