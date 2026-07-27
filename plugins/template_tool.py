"""Шаблон своего плагина.

Скопируй этот файл, переименуй COMMAND и измени handle().
"""

COMMAND = "template"
HELP = "/template текст — пример шаблона плагина"


def handle(args: str, context: dict) -> str:  # noqa: ARG001 - context нужен для единого интерфейса
    if not args:
        return "Передай текст: /template привет"
    return f"Шаблон получил: {args}"
