"""Мод: чтение веб-страницы в обычный текст.

Устанавливается командой: python3 kitai_cli.py mods install web-fetch
После установки в агенте появится команда /web URL
"""

from __future__ import annotations

import html
import ipaddress
import re
import socket
import urllib.error
import urllib.request
from urllib.parse import urlparse

COMMAND = "web"
HELP = "/web URL — скачать страницу и показать текст без HTML, пример: /web https://ollama.com"

MAX_CHARS = 8000
TIMEOUT = 30
USER_AGENT = "Mozilla/5.0 (compatible; OdeKitAi/1.0; +https://github.com/nurislamtagirov444-wq/-Ode-KitAi)"

_SCRIPT_STYLE_RE = re.compile(r"<(script|style|noscript)[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)
_TAG_RE = re.compile(r"<[^>]+>")
_SPACE_RE = re.compile(r"[ \t\r\f\v]+")
_NEWLINES_RE = re.compile(r"\n{3,}")


def _is_private_host(hostname: str) -> bool:
    """Не даём агенту лазить по локальной сети и облачным метадата-сервисам."""
    try:
        infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        return True
    for info in infos:
        address = info[4][0]
        try:
            ip = ipaddress.ip_address(address)
        except ValueError:
            return True
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            return True
    return False


def _to_text(raw_html: str) -> str:
    text = _SCRIPT_STYLE_RE.sub(" ", raw_html)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</(p|div|li|h[1-6]|tr)>", "\n", text, flags=re.IGNORECASE)
    text = _TAG_RE.sub(" ", text)
    text = html.unescape(text)
    text = _SPACE_RE.sub(" ", text)
    text = "\n".join(line.strip() for line in text.splitlines())
    return _NEWLINES_RE.sub("\n\n", text).strip()


def handle(args: str, context: dict) -> str:  # noqa: ARG001 - единый интерфейс плагинов
    url = args.strip()
    if not url:
        return "Использование: /web https://example.com"

    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return "Разрешены только http и https ссылки."
    if not parsed.hostname:
        return "В ссылке нет домена."
    if _is_private_host(parsed.hostname):
        return "Отказ: этот адрес ведёт в локальную сеть. Разрешены только публичные сайты."

    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:  # noqa: S310
            content_type = response.headers.get("Content-Type", "")
            raw = response.read(2_000_000)
    except urllib.error.HTTPError as exc:
        return f"Сайт ответил ошибкой {exc.code}. Проверь ссылку."
    except urllib.error.URLError as exc:
        return f"Не могу открыть страницу: {exc.reason}"

    charset = "utf-8"
    if "charset=" in content_type:
        charset = content_type.split("charset=")[-1].split(";")[0].strip() or "utf-8"
    body = raw.decode(charset, errors="replace")

    text = body if "text/plain" in content_type else _to_text(body)
    if not text:
        return "Страница открылась, но текста в ней не нашлось."
    if len(text) > MAX_CHARS:
        text = text[:MAX_CHARS] + "\n\n...текст обрезан..."
    return f"--- {url} ---\n{text}"
