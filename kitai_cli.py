#!/usr/bin/env python3
"""Ode KitAi — управление бесплатным доступом к моделям, модами и стратегией.

Быстрый старт:
    python3 kitai_cli.py setup       # что нужно сделать, по шагам
    python3 kitai_cli.py doctor      # проверить, что реально работает
    python3 kitai_cli.py ask "..."   # спросить модель по активной стратегии

Зависимостей нет: только стандартная библиотека Python 3.9+.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import List, Optional

from kitai import config as cfg
from kitai import mods as mods_mod
from kitai.providers import ProviderError, load_providers, ping
from kitai.strategy import Router, StrategyConfig, build_system_prompt

LINE = "-" * 60


def _print_header(text: str) -> None:
    print()
    print(text)
    print(LINE)


# --------------------------------------------------------------------------
# providers
# --------------------------------------------------------------------------


def cmd_providers(args: argparse.Namespace) -> int:
    providers = load_providers()
    if args.json:
        payload = [
            {
                "id": p.id,
                "title": p.title,
                "kind": p.kind,
                "ready": p.is_ready(),
                "default_model": p.default_model,
                "limits": p.limits,
            }
            for p in providers.values()
        ]
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    _print_header("Способы бесплатного доступа к моделям")
    for provider in providers.values():
        mark = "ГОТОВ" if provider.is_ready() else "нужен ключ"
        print(f"\n[{provider.id}] {provider.title}  —  {mark}")
        print(f"  тип:      {'локально' if provider.is_local else 'облако, бесплатный уровень'}")
        print(f"  модель:   {provider.default_model}")
        print(f"  лимиты:   {provider.limit_summary()}")
        print(f"  цена:     {provider.cost}")
        print(f"  приватность: {provider.privacy}")
        print(f"  статус:   {provider.readiness_hint()}")
        if not provider.is_ready():
            print(f"  получить ключ: {provider.signup}")
        print(f"  документация: {provider.docs}")
    print()
    print("Ключи хранятся только в файле .env, который не попадает в git.")
    print("Добавить ключ: python3 kitai_cli.py key set GROQ_API_KEY")
    return 0


def cmd_key(args: argparse.Namespace) -> int:
    providers = load_providers()
    known = {p.api_key_env: p for p in providers.values() if p.api_key_env}

    if args.key_action == "list":
        _print_header("Ключи (значения скрыты)")
        for env_name, provider in known.items():
            import os

            print(f"  {env_name:24} {cfg.mask_secret(os.environ.get(env_name))}   -> {provider.title}")
        print()
        print(f"Файл ключей: {cfg.ENV_FILE}")
        print("Никогда не публикуй этот файл и не присылай ключи в чат.")
        return 0

    name = args.name
    if not name:
        print("Укажи имя переменной, например: python3 kitai_cli.py key set GROQ_API_KEY")
        return 2
    if name not in known:
        print(f"Неизвестная переменная '{name}'. Известные: {', '.join(sorted(known))}")
        return 2

    if args.key_action == "set":
        import getpass

        provider = known[name]
        print(f"Провайдер: {provider.title}")
        print(f"Где взять ключ: {provider.signup}")
        try:
            value = getpass.getpass(f"Вставь {name} (ввод скрыт, Enter для отмены): ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nОтменено.")
            return 1
        if not value:
            print("Пусто, ничего не изменил.")
            return 1

        existing = cfg.parse_env_text(
            cfg.ENV_FILE.read_text(encoding="utf-8") if cfg.ENV_FILE.exists() else ""
        )
        existing[name] = value
        lines = ["# Ключи Ode KitAi. Этот файл не должен попадать в git.", ""]
        lines += [f"{key}={val}" for key, val in sorted(existing.items())]
        cfg.ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
        try:
            cfg.ENV_FILE.chmod(0o600)
        except OSError:
            pass
        print(f"Сохранил в {cfg.ENV_FILE} (права 600). Проверь: python3 kitai_cli.py doctor")
        return 0

    print("Действия: key list | key set <ИМЯ>")
    return 2


# --------------------------------------------------------------------------
# strategy
# --------------------------------------------------------------------------


def cmd_strategy(args: argparse.Namespace) -> int:
    strategy = StrategyConfig.load()

    if args.strategy_action in (None, "show"):
        _print_header("Стратегия")
        print(f"Активный профиль: {strategy.active_profile}")
        print()
        for name, profile in strategy.profiles.items():
            mark = "  <-- активен" if name == strategy.active_profile else ""
            print(f"  {name}{mark}")
            print(f"      {profile.title}")
            print(f"      {profile.description}")
            chain = " -> ".join(
                f"{s.provider}:{s.model}" if s.model else s.provider for s in profile.chain
            )
            print(f"      цепочка: {chain}")
            print()
        avoid = strategy.avoided_families()
        if avoid:
            print(f"Не предлагаются модели семейств: {', '.join(avoid)}")
        print("Переключить: python3 kitai_cli.py strategy use fast_free")
        return 0

    if args.strategy_action == "use":
        try:
            profile = strategy.set_active(args.profile)
        except KeyError as exc:
            print(str(exc))
            return 2
        strategy.save()
        print(f"Активный профиль: {profile.name} — {profile.title}")
        print(f"Что это значит: {profile.description}")
        return 0

    if args.strategy_action == "plan":
        router = Router(strategy=strategy)
        profile = strategy.profile(args.profile)
        _print_header(f"План профиля '{profile.name}': {profile.title}")
        rows = router.plan(profile.name)
        ready_count = 0
        for index, row in enumerate(rows, start=1):
            state = "готов" if row["ready"] else "НЕ готов"
            if row["ready"]:
                ready_count += 1
            print(f"  {index}. {row.get('title', row['provider'])}")
            print(f"     модель: {row.get('model')}")
            print(f"     статус: {state} — {row.get('reason', '')}")
            print(f"     лимиты: {row.get('limits', '')}")
        print()
        if ready_count == 0:
            print("Ни один шаг не готов. Добавь ключ или запусти Ollama:")
            print("  python3 kitai_cli.py key set GROQ_API_KEY")
            print("  docker compose up -d")
        else:
            print(f"Готовых шагов: {ready_count} из {len(rows)}. Этого хватит для работы.")
        return 0

    if args.strategy_action == "prompt":
        print(build_system_prompt(strategy))
        return 0

    print("Действия: strategy show | strategy use <профиль> | strategy plan | strategy prompt")
    return 2


# --------------------------------------------------------------------------
# mods
# --------------------------------------------------------------------------


def cmd_mods(args: argparse.Namespace) -> int:
    if args.mods_action in (None, "list"):
        rows = mods_mod.status()
        _print_header("Модификации агента")
        for row in rows:
            mark = "установлен" if row["installed"] else "не установлен"
            print(f"\n  {row['id']}  [{row['type']}]  — {mark}")
            print(f"      {row['title']}")
            print(f"      {row['description']}")
            print(f"      риск: {row['risk']}")
            if row["url"]:
                print(f"      источник: {row['url']}")
            if row["path"]:
                print(f"      путь: {row['path']}")
        print()
        print("Установить: python3 kitai_cli.py mods install web-fetch")
        print("Правило: скачать не значит запустить. Сторонний код читай перед запуском.")
        return 0

    if args.mods_action == "install":
        try:
            result = mods_mod.install(args.mod_id, force=args.force, name=args.name)
        except mods_mod.ModError as exc:
            print(f"Не получилось: {exc}")
            return 1
        print(result["message"])
        return 0

    if args.mods_action == "remove":
        try:
            print(mods_mod.remove(args.mod_id))
        except mods_mod.ModError as exc:
            print(f"Не получилось: {exc}")
            return 1
        return 0

    print("Действия: mods list | mods install <id> | mods remove <id>")
    return 2


# --------------------------------------------------------------------------
# doctor / ask / setup
# --------------------------------------------------------------------------


def cmd_doctor(args: argparse.Namespace) -> int:
    providers = load_providers()
    strategy = StrategyConfig.load()

    _print_header("Проверка окружения")
    print(f"Python: {sys.version.split()[0]}")
    print(f"Файл ключей .env: {'есть' if cfg.ENV_FILE.exists() else 'нет (это нормально в начале)'}")
    print(f"Активный профиль: {strategy.active_profile}")

    _print_header("Проверка провайдеров (реальные запросы)")
    working: List[str] = []
    for provider in providers.values():
        if not provider.is_ready():
            print(f"  {provider.id:16} пропуск — {provider.readiness_hint()}")
            continue
        if args.offline:
            print(f"  {provider.id:16} ключ на месте (сеть не проверялась, режим --offline)")
            working.append(provider.id)
            continue
        result = ping(provider, timeout=args.timeout)
        if result["ok"]:
            working.append(provider.id)
            print(f"  {provider.id:16} РАБОТАЕТ — {result['model']}, {result['elapsed']} c")
        else:
            print(f"  {provider.id:16} не отвечает — {result['reason']}")

    _print_header("Итог")
    if working:
        print(f"Рабочих способов доступа: {len(working)} ({', '.join(working)})")
        print("Можно спрашивать: python3 kitai_cli.py ask \"привет\"")
    else:
        print("Пока не работает ни один способ. Самый быстрый путь получить бесплатный доступ:")
        print("  1. Открой https://console.groq.com, войди через GitHub, создай API Key")
        print("  2. python3 kitai_cli.py key set GROQ_API_KEY")
        print("  3. python3 kitai_cli.py doctor")
        print()
        print("Либо полностью локально, без ключей и интернета:")
        print("  docker compose up -d && ./scripts/pull-model.sh llama3.2:3b")
    return 0 if working else 1


def cmd_ask(args: argparse.Namespace) -> int:
    strategy = StrategyConfig.load()
    router = Router(strategy=strategy)

    warning = strategy.check_model_preference(args.model)
    if warning:
        print(f"Предупреждение: {warning}")
        print()

    question = " ".join(args.question).strip()
    if not question:
        print("Нечего спрашивать. Пример: python3 kitai_cli.py ask \"как поднять Ollama\"")
        return 2

    messages = [
        {"role": "system", "content": build_system_prompt(strategy, strategist=args.strategist)},
        {"role": "user", "content": question},
    ]

    try:
        result = router.run(
            messages,
            profile_name=args.profile,
            provider_override=args.provider,
            model_override=args.model,
        )
    except KeyError as exc:
        print(str(exc))
        return 2

    if not result.ok:
        print("Ни один провайдер не ответил.")
        print()
        print("Что пробовал:")
        print(result.explain())
        print()
        print("Что делать:")
        print("  1. python3 kitai_cli.py doctor — увидеть точную причину")
        print("  2. python3 kitai_cli.py key set GROQ_API_KEY — добавить бесплатный ключ")
        print("  3. docker compose up -d — поднять локальную модель без лимитов")
        return 1

    if args.verbose:
        print("Как выбирался ответ:")
        print(result.explain())
        print()

    print(result.content)
    print()
    print(LINE)
    print(f"Ответил: {result.provider} / {result.model} за {result.elapsed} c")
    return 0


def cmd_setup(args: argparse.Namespace) -> int:  # noqa: ARG001
    providers = load_providers()
    strategy = StrategyConfig.load()
    ready = [p for p in providers.values() if p.is_ready()]

    _print_header("Настройка Ode KitAi с нуля")
    print("Здесь три вещи: бесплатный доступ к моделям, моды для агента, стратегия ответов.")

    _print_header("Шаг 1. Бесплатный доступ (выбери минимум один путь)")
    print("Путь A — облако, быстро, ничего не устанавливать. Занимает 5 минут.")
    print("  1. Открой https://console.groq.com и войди через GitHub")
    print("  2. Раздел API Keys -> Create API Key -> скопируй")
    print("  3. Выполни: python3 kitai_cli.py key set GROQ_API_KEY")
    print("  Нормальный результат: 'Сохранил в .env'")
    print("  Лимит: 30 запросов в минуту, до 14400 в сутки на llama-3.1-8b-instant. Карта не нужна.")
    print()
    print("Путь B — локально, без лимитов на количество запросов и без интернета.")
    print("  1. docker compose up -d")
    print("  2. ./scripts/pull-model.sh llama3.2:3b")
    print("  3. Открой http://localhost:3000")
    print("  Нормальный результат: страница Open WebUI открылась и модель видна в списке.")
    print("  Ограничение: скорость упирается в твоё железо, 16 GB RAM тянет модели до 7B спокойно.")

    _print_header("Шаг 2. Моды агента")
    print("  python3 kitai_cli.py mods list             — посмотреть доступные")
    print("  python3 kitai_cli.py mods install web-fetch — добавить чтение сайтов")
    print("  python3 kitai_cli.py mods install notes     — добавить заметки")
    print("  python3 kitai_cli.py mods install strategy-tools — управление стратегией из чата")

    _print_header("Шаг 3. Стратегия")
    print(f"  Сейчас активен профиль: {strategy.active_profile}")
    print("  python3 kitai_cli.py strategy          — все профили")
    print("  python3 kitai_cli.py strategy use fast_free — режим максимальной скорости")
    print("  python3 kitai_cli.py strategy plan     — какой провайдер сработает первым")

    _print_header("Шаг 4. Проверка")
    print("  python3 kitai_cli.py doctor")
    print("  python3 kitai_cli.py ask \"проверка связи\"")

    _print_header("Твоё состояние прямо сейчас")
    if ready:
        print(f"Готовы к работе: {', '.join(p.id for p in ready)}")
    else:
        print("Пока не настроен ни один провайдер. Начни с Пути A — он быстрее.")
    print()
    print("Честно про лимиты: бесплатного облачного безлимита не существует.")
    print("Облако даёт скорость, но ограничивает число запросов в сутки.")
    print("Локальный запуск снимает лимит запросов, но упирается в RAM и скорость.")
    print("Связка обоих через профиль 'balanced' — самое близкое к безлимиту.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="kitai",
        description="Ode KitAi: бесплатный доступ к моделям, моды агента, настройка стратегии.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command")

    p_setup = sub.add_parser("setup", help="пошаговая инструкция с нуля")
    p_setup.set_defaults(func=cmd_setup)

    p_prov = sub.add_parser("providers", help="список способов бесплатного доступа")
    p_prov.add_argument("--json", action="store_true", help="вывод в JSON")
    p_prov.set_defaults(func=cmd_providers)

    p_key = sub.add_parser("key", help="управление ключами (значения не печатаются)")
    p_key.add_argument("key_action", choices=["list", "set"], nargs="?", default="list")
    p_key.add_argument("name", nargs="?", help="имя переменной, например GROQ_API_KEY")
    p_key.set_defaults(func=cmd_key)

    p_strat = sub.add_parser("strategy", help="профили стратегии и цепочка провайдеров")
    p_strat.add_argument(
        "strategy_action", choices=["show", "use", "plan", "prompt"], nargs="?", default="show"
    )
    p_strat.add_argument("profile", nargs="?", help="имя профиля")
    p_strat.set_defaults(func=cmd_strategy)

    p_mods = sub.add_parser("mods", help="модификации агента")
    p_mods.add_argument("mods_action", choices=["list", "install", "remove"], nargs="?", default="list")
    p_mods.add_argument("mod_id", nargs="?", help="идентификатор мода")
    p_mods.add_argument("--force", action="store_true", help="перезаписать существующий плагин")
    p_mods.add_argument("--name", help="имя папки для мода типа repo")
    p_mods.set_defaults(func=cmd_mods)

    p_doc = sub.add_parser("doctor", help="проверить, что реально работает")
    p_doc.add_argument("--offline", action="store_true", help="не делать сетевых запросов")
    p_doc.add_argument("--timeout", type=int, default=20, help="таймаут проверки, секунды")
    p_doc.set_defaults(func=cmd_doctor)

    p_ask = sub.add_parser("ask", help="задать вопрос по активной стратегии")
    p_ask.add_argument("question", nargs="+", help="текст вопроса")
    p_ask.add_argument("--profile", help="использовать другой профиль разово")
    p_ask.add_argument("--provider", help="принудительно выбрать провайдера")
    p_ask.add_argument("--model", help="принудительно выбрать модель")
    p_ask.add_argument("--strategist", action="store_true", help="полный формат стратега")
    p_ask.add_argument("-v", "--verbose", action="store_true", help="показать разбор попыток")
    p_ask.set_defaults(func=cmd_ask)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    cfg.ensure_dirs()
    cfg.load_env()

    parser = build_parser()
    args = parser.parse_args(argv)

    if not getattr(args, "func", None):
        parser.print_help()
        print()
        print("Начни отсюда: python3 kitai_cli.py setup")
        return 0

    try:
        return args.func(args)
    except FileNotFoundError as exc:
        print(f"Не хватает файла: {exc}")
        return 1
    except ProviderError as exc:
        print(f"Ошибка провайдера: {exc}")
        return 1
    except KeyboardInterrupt:
        print("\nПрервано.")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
