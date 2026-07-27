"""Плагин для безопасного клонирования модификаций из GitHub/GitLab/Codeberg."""

from __future__ import annotations

import re
import shlex
import subprocess
from pathlib import Path
from urllib.parse import urlparse

COMMAND = "github_clone"
HELP = "/github_clone URL [имя_папки] — клонировать GitHub/GitLab/Codeberg репозиторий в ./mods"

ALLOWED_HOSTS = {"github.com", "gitlab.com", "codeberg.org"}
SAFE_NAME_RE = re.compile(r"^[A-Za-z0-9._-]{1,80}$")


def _default_name(url: str) -> str:
    parsed = urlparse(url)
    name = Path(parsed.path).name
    if name.endswith(".git"):
        name = name[:-4]
    if not name or not SAFE_NAME_RE.fullmatch(name):
        raise ValueError("не могу определить безопасное имя папки; укажи имя вторым аргументом")
    return name


def _validate_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise ValueError("разрешены только HTTPS URL, например https://github.com/user/repo.git")
    if parsed.hostname not in ALLOWED_HOSTS:
        allowed = ", ".join(sorted(ALLOWED_HOSTS))
        raise ValueError(f"разрешены только хосты: {allowed}")
    if not parsed.path or parsed.path.count("/") < 2:
        raise ValueError("URL должен указывать на репозиторий, например https://github.com/user/repo.git")


def handle(args: str, context: dict) -> str:
    if not args:
        return "Использование: /github_clone https://github.com/user/repo.git [имя_папки]"

    parts = shlex.split(args)
    if not parts:
        return "Использование: /github_clone https://github.com/user/repo.git [имя_папки]"
    if len(parts) > 2:
        return "Слишком много аргументов. Использование: /github_clone URL [имя_папки]"

    url = parts[0]
    _validate_url(url)

    target_name = parts[1] if len(parts) == 2 else _default_name(url)
    if not SAFE_NAME_RE.fullmatch(target_name):
        return "Имя папки должно содержать только буквы, цифры, точку, подчёркивание или дефис."

    mods_dir = Path(context["mods_dir"]).resolve()
    mods_dir.mkdir(exist_ok=True)
    dest = (mods_dir / target_name).resolve()
    if mods_dir not in dest.parents:
        return "Небезопасный путь назначения."
    if dest.exists():
        return f"Папка уже существует: {dest}"

    proc = subprocess.run(  # noqa: S603 - команда без shell, URL валидируется выше
        ["git", "clone", "--depth", "1", url, str(dest)],
        cwd=str(context["base_dir"]),
        text=True,
        capture_output=True,
        timeout=600,
        check=False,
    )
    if proc.returncode != 0:
        return "Ошибка git clone:\n" + (proc.stderr or proc.stdout)

    return (
        f"Готово: {dest}\n"
        "Важно: я только скачал код. Перед запуском проверь README, зависимости и лицензии."
    )
