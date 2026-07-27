"""Мод: заметки агента.

Устанавливается командой: python3 kitai_cli.py mods install notes
После установки появятся команды /note и /notes
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

COMMAND = "note"
HELP = "/note текст — сохранить заметку; /note list — показать все; /note clear — очистить"

MAX_NOTE_LEN = 2000
MAX_SHOW = 40


def _notes_file(context: dict) -> Path:
    base = Path(context.get("base_dir", Path.cwd()))
    state_dir = base / ".kitai_state"
    state_dir.mkdir(parents=True, exist_ok=True)
    return state_dir / "notes.md"


def handle(args: str, context: dict) -> str:
    path = _notes_file(context)
    text = args.strip()

    if not text or text == "list":
        if not path.exists():
            return "Заметок пока нет. Добавь: /note купить кабель"
        lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        if not lines:
            return "Заметок пока нет. Добавь: /note купить кабель"
        shown = lines[-MAX_SHOW:]
        header = f"Заметки ({len(lines)} шт., показаны последние {len(shown)}):"
        return header + "\n" + "\n".join(shown)

    if text == "clear":
        if path.exists():
            path.unlink()
        return "Заметки очищены."

    if len(text) > MAX_NOTE_LEN:
        return f"Заметка слишком длинная, максимум {MAX_NOTE_LEN} символов."

    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    with path.open("a", encoding="utf-8") as handle_file:
        handle_file.write(f"- [{stamp}] {text}\n")
    return f"Записал. Файл: {path.name}"
