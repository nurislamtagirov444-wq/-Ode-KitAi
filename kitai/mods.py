"""Менеджер модификаций (модов) агента.

Два типа модов:
1. plugin — файл .py, который кладётся в ./plugins и добавляет команду агенту.
2. repo   — сторонний git-репозиторий, который скачивается в ./mods.

Правило безопасности одно и оно жёсткое: скачивание не равно запуску.
Сторонний код никогда не выполняется автоматически.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from . import config as cfg

ALLOWED_HOSTS = {"github.com", "gitlab.com", "codeberg.org"}
SAFE_NAME_RE = re.compile(r"^[A-Za-z0-9._-]{1,80}$")
BUILTIN_DIR = Path(__file__).resolve().parent / "builtin_mods"


class ModError(RuntimeError):
    """Понятная человеку ошибка при работе с модом."""


@dataclass
class Mod:
    id: str
    type: str
    title: str
    description: str = ""
    source: Optional[str] = None
    file: Optional[str] = None
    url: Optional[str] = None
    license: str = ""
    risk: str = "unknown"
    note: str = ""
    needs_network: bool = False
    extra: Dict[str, Any] = field(default_factory=dict)


def load_registry(path: Path = cfg.MODS_REGISTRY_FILE) -> Dict[str, Mod]:
    data = cfg.load_json(path)
    mods: Dict[str, Mod] = {}
    for raw in data.get("mods", []):
        mod = Mod(
            id=raw["id"],
            type=raw.get("type", "plugin"),
            title=raw.get("title", raw["id"]),
            description=raw.get("description", ""),
            source=raw.get("source"),
            file=raw.get("file"),
            url=raw.get("url"),
            license=raw.get("license", ""),
            risk=raw.get("risk", "unknown"),
            note=raw.get("note", ""),
            needs_network=bool(raw.get("needs_network", False)),
        )
        mods[mod.id] = mod
    return mods


def load_state(path: Path = cfg.MODS_STATE_FILE) -> Dict[str, Any]:
    return cfg.load_json_or_default(path, {"installed": {}})


def save_state(state: Dict[str, Any], path: Path = cfg.MODS_STATE_FILE) -> None:
    cfg.save_json(path, state)


def validate_git_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise ModError("Разрешены только HTTPS-ссылки, например https://github.com/user/repo.git")
    if parsed.hostname not in ALLOWED_HOSTS:
        raise ModError("Разрешены только хосты: " + ", ".join(sorted(ALLOWED_HOSTS)))
    if not parsed.path or parsed.path.count("/") < 2:
        raise ModError("Ссылка должна вести на репозиторий: https://github.com/user/repo.git")


def default_repo_name(url: str) -> str:
    name = Path(urlparse(url).path).name
    if name.endswith(".git"):
        name = name[:-4]
    if not name or not SAFE_NAME_RE.fullmatch(name):
        raise ModError("Не могу определить безопасное имя папки, укажи его вручную")
    return name


def install_plugin_mod(mod: Mod, *, plugin_dir: Path = cfg.PLUGIN_DIR, force: bool = False) -> Path:
    if not mod.file:
        raise ModError(f"У мода {mod.id} не указано поле file")
    if mod.source != "builtin":
        raise ModError(
            f"Мод {mod.id} не встроенный. Для внешних плагинов используй 'kitai mods add-file <путь>' "
            "после того как сам прочитал код."
        )
    source_path = BUILTIN_DIR / mod.file
    if not source_path.is_file():
        raise ModError(f"Файл встроенного мода не найден: {source_path}")

    plugin_dir.mkdir(parents=True, exist_ok=True)
    target = plugin_dir / mod.file
    if target.exists() and not force:
        raise ModError(f"Плагин уже установлен: {target}. Добавь --force для перезаписи.")
    shutil.copyfile(source_path, target)
    return target


def install_repo_mod(
    mod: Mod,
    *,
    mods_dir: Path = cfg.MODS_DIR,
    name: Optional[str] = None,
    runner=subprocess.run,
) -> Path:
    if not mod.url:
        raise ModError(f"У мода {mod.id} не указан url")
    validate_git_url(mod.url)
    target_name = name or default_repo_name(mod.url)
    if not SAFE_NAME_RE.fullmatch(target_name):
        raise ModError("Имя папки: только буквы, цифры, точка, дефис, подчёркивание")

    mods_dir.mkdir(parents=True, exist_ok=True)
    dest = (mods_dir / target_name).resolve()
    if mods_dir.resolve() not in dest.parents:
        raise ModError("Небезопасный путь назначения")
    if dest.exists():
        raise ModError(f"Папка уже существует: {dest}")

    proc = runner(
        ["git", "clone", "--depth", "1", mod.url, str(dest)],
        text=True,
        capture_output=True,
        timeout=900,
        check=False,
    )
    if proc.returncode != 0:
        raise ModError("git clone не удался:\n" + (proc.stderr or proc.stdout or "нет вывода"))
    return dest


def install(
    mod_id: str,
    *,
    registry: Optional[Dict[str, Mod]] = None,
    force: bool = False,
    name: Optional[str] = None,
) -> Dict[str, Any]:
    registry = registry if registry is not None else load_registry()
    mod = registry.get(mod_id)
    if mod is None:
        available = ", ".join(sorted(registry))
        raise ModError(f"Мод '{mod_id}' не найден. Доступные: {available}")

    if mod.type == "plugin":
        path = install_plugin_mod(mod, force=force)
        message = f"Плагин установлен: {path.relative_to(cfg.BASE_DIR)}. Команда появится в агенте после перезапуска."
    elif mod.type == "repo":
        path = install_repo_mod(mod, name=name)
        message = (
            f"Репозиторий скачан: {path.relative_to(cfg.BASE_DIR)}\n"
            "Важно: код скачан, но НЕ запущен. Сначала прочитай README и лицензию."
        )
    else:
        raise ModError(f"Неизвестный тип мода: {mod.type}")

    state = load_state()
    state.setdefault("installed", {})[mod.id] = {
        "type": mod.type,
        "path": str(path.relative_to(cfg.BASE_DIR)),
        "title": mod.title,
        "risk": mod.risk,
    }
    save_state(state)
    return {"mod": mod, "path": path, "message": message}


def remove(mod_id: str, *, registry: Optional[Dict[str, Mod]] = None) -> str:
    state = load_state()
    installed = state.get("installed", {})
    entry = installed.get(mod_id)
    if entry is None:
        raise ModError(f"Мод '{mod_id}' не отмечен как установленный")

    path = cfg.BASE_DIR / entry["path"]
    if entry["type"] == "plugin":
        if path.is_file():
            path.unlink()
    elif entry["type"] == "repo":
        resolved = path.resolve()
        if cfg.MODS_DIR.resolve() not in resolved.parents:
            raise ModError("Отказ: путь вне папки mods")
        if resolved.is_dir():
            shutil.rmtree(resolved)

    installed.pop(mod_id, None)
    save_state(state)
    return f"Мод '{mod_id}' удалён: {entry['path']}"


def status(registry: Optional[Dict[str, Mod]] = None) -> List[Dict[str, Any]]:
    registry = registry if registry is not None else load_registry()
    installed = load_state().get("installed", {})
    rows = []
    for mod in registry.values():
        entry = installed.get(mod.id)
        exists = False
        if entry:
            exists = (cfg.BASE_DIR / entry["path"]).exists()
        rows.append(
            {
                "id": mod.id,
                "type": mod.type,
                "title": mod.title,
                "risk": mod.risk,
                "installed": bool(entry) and exists,
                "path": entry["path"] if entry else None,
                "description": mod.description,
                "url": mod.url,
            }
        )
    return rows
