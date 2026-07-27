# Ода KitAi 🌸

**Аниме визуальная новелла для Android.** Школьнику Аято поручили выключить учебную нейросеть,
которая научилась писать стихи. У неё девять дней. У тебя — одно слово.

> «Ода — это когда ты называешь вещь по имени, и она перестаёт быть одинокой.»

## 📥 Скачать APK

**→ [Скачать OdaKitAi-v1.0.apk (2.6 МБ)](https://github.com/nurislamtagirov444-wq/-Ode-KitAi/raw/arena/019fa405-ode-kitai/release/OdaKitAi-v1.0.apk)**

Готовый подписанный APK лежит в папке [`release/`](release/).

Установка: скачай `.apk` на телефон → разреши «Установка из неизвестных источников» → открой файл.

## ✨ Что внутри

- 68 сцен, 196 сюжетных маршрутов, **4 концовки** (A «Перезагрузка», B «Ода KitAi», C «Человеческое», D «Призрак сети»)
- 3 персонажа: Кит (ИИ), Юки (староста), Аято (игрок)
- Полностью на русском, озвучка текста печатной машинкой
- Режимы **AUTO** и **SKIP**, журнал диалогов (LOG), галерея концовок
- Автосохранение и «Продолжить»
- Работает **оффлайн**, без рекламы, без единого разрешения Android

## 📱 Требования

Android 5.0+ (minSdk 21), ~4 МБ.

## 🛠 Технически

| | |
|---|---|
| Оболочка | нативная Activity + WebView (Java, AGP 8.5) |
| Движок новеллы | ванильный HTML/CSS/JS, без зависимостей |
| Сценарий | [`app/src/main/assets/www/js/story.js`](app/src/main/assets/www/js/story.js) — граф узлов |
| Движок | [`app/src/main/assets/www/js/engine.js`](app/src/main/assets/www/js/engine.js) |
| Арт | сгенерирован ИИ, фоны JPEG + спрайты PNG с альфой |
| Сборка | подписанный APK в [`release/`](release/) (v1 + v2 + v3 signature, zipalign) |

### Собрать локально

Вариант с Android Studio / Gradle:

```bash
./gradlew :app:assembleRelease
# app/build/outputs/apk/release/app-release.apk
```

Опубликованный APK собран без Android Studio — из папки `app/src/main/assets/www`
упаковкой веб-ассетов в WebView-контейнер (нужен только Java-рантайм).

### Добавить свою сцену

В `story.js` узел выглядит так:

```js
my_node: {
  bg: 'bg_rooftop',
  sprites: { left: 'kit', right: 'yuki' },
  active: 'left',
  who: 'kit',
  text: 'Реплика героя.',
  next: 'next_node'
  // или: choices: [{ t: 'Текст выбора', to: 'node_id', aff: { kit: +1 } }]
}
```

После правки сценария достаточно пересобрать APK — нативный код менять не нужно.
