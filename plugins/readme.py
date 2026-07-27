"""Плагин для чтения README у скачанных модификаций."""

from __future__ import annotations

import shlex
from pathlib import Path

COMMAND = "readme"
HELP = "/readme [путь] — показать README из репозитория или папки mods, пример: /readme mods/open-webui"

MAX_CHARS = 12_000
README_NAMES = ("README.md", "README.rst", "README.txt", "readme.md", "readme.txt")


def _inside(child: Path, parent: Path) -> bool:
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def _pick_readme(path: Path) -> Path:
    if path.is_file():
        return path
    if not path.is_dir():
        raise FileNotFoundError(path)

    for name in README_NAMES:
        candidate = path / name
        if candidate.is_file():
            return candidate

    matches = sorted(path.glob("README*")) + sorted(path.glob("readme*"))
    for candidate in matches:
        if candidate.is_file():
            return candidate

    raise FileNotFoundError(f"README не найден в {path}")


def handle(args: str, context: dict) -> str:
    base_dir = Path(context["base_dir"]).resolve()
    mods_dir = Path(context["mods_dir"]).resolve()

    if not args:
        if not mods_dir.exists():
            return "Папка mods пока пустая. Скачай мод: /github_clone https://github.com/user/repo.git"
        items = [p.name for p in sorted(mods_dir.iterdir()) if p.is_dir()]
        if not items:
            return "Папка mods пока пустая. Скачай мод: /github_clone https://github.com/user/repo.git"
        return "Скачанные моды:\n" + "\n".join(f"- mods/{name}" for name in items)

    parts = shlex.split(args)
    if len(parts) != 1:
        return "Использование: /readme [путь], например /readme mods/open-webui"

    requested = (base_dir / parts[0]).resolve()
    if not _inside(requested, base_dir):
        return "Можно читать файлы только внутри этого репозитория."

    readme = _pick_readme(requested).resolve()
    if not _inside(readme, base_dir):
        return "Можно читать файлы только внутри этого репозитория."

    text = readme.read_text(encoding="utf-8", errors="replace")
    if len(text) > MAX_CHARS:
        text = text[:MAX_CHARS] + "\n\n...обрезано..."

    relative = readme.relative_to(base_dir)
    return f"--- {relative} ---\n{text}"
