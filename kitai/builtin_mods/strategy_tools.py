"""Мод: управление стратегией прямо из чата с агентом.

Устанавливается командой: python3 kitai_cli.py mods install strategy-tools
После установки появится команда /strategy
"""

from __future__ import annotations

import sys
from pathlib import Path

COMMAND = "strategy"
HELP = "/strategy — показать профили; /strategy use <имя> — переключить; /strategy plan — цепочка провайдеров"


def _load():
    base = Path(__file__).resolve().parent.parent
    if str(base) not in sys.path:
        sys.path.insert(0, str(base))
    from kitai.strategy import Router, StrategyConfig  # noqa: PLC0415

    return Router, StrategyConfig


def handle(args: str, context: dict) -> str:  # noqa: ARG001 - единый интерфейс плагинов
    try:
        Router, StrategyConfig = _load()
    except Exception as exc:  # noqa: BLE001 - показываем причину пользователю
        return f"Не могу загрузить модуль стратегии: {exc}"

    parts = args.split()
    strategy = StrategyConfig.load()

    if not parts:
        lines = [f"Активный профиль: {strategy.active_profile}", "", "Доступные профили:"]
        for name, profile in strategy.profiles.items():
            mark = " (активен)" if name == strategy.active_profile else ""
            lines.append(f"  {name}{mark} — {profile.title}")
            lines.append(f"      {profile.description}")
        lines.append("")
        lines.append("Переключить: /strategy use fast_free")
        return "\n".join(lines)

    action = parts[0]

    if action == "use":
        if len(parts) < 2:
            return "Укажи профиль: /strategy use fast_free"
        try:
            profile = strategy.set_active(parts[1])
        except KeyError as exc:
            return str(exc)
        strategy.save()
        return f"Активный профиль теперь: {profile.name} — {profile.title}"

    if action == "plan":
        router = Router(strategy=strategy)
        rows = router.plan()
        lines = [f"Цепочка профиля '{strategy.active_profile}':"]
        for index, row in enumerate(rows, start=1):
            mark = "готов" if row["ready"] else "не готов"
            lines.append(f"  {index}. {row['provider']} / {row.get('model')} — {mark}")
            lines.append(f"      {row.get('reason', '')}")
        return "\n".join(lines)

    return "Команды: /strategy | /strategy use <профиль> | /strategy plan"
