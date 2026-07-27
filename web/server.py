#!/usr/bin/env python3
"""Мини-сервер для сайта Ode KitAi.

- Раздаёт статические файлы из папки web/.
- Проксирует запросы браузера к локальному Ollama API.
- Не требует внешних Python-зависимостей.

Запуск:
    python3 web/server.py

Переменные окружения:
    OLLAMA_URL=http://localhost:11434
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import sys
import urllib.error
import urllib.request
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

WEB_DIR = Path(__file__).resolve().parent
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434").rstrip("/")
MAX_BODY_BYTES = 2_000_000

mimetypes.add_type("text/javascript; charset=utf-8", ".js")
mimetypes.add_type("text/css; charset=utf-8", ".css")
mimetypes.add_type("application/json; charset=utf-8", ".json")
mimetypes.add_type("text/plain; charset=utf-8", ".txt")


def _json_response(handler: BaseHTTPRequestHandler, status: int, payload: dict[str, Any]) -> None:
    body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Cache-Control", "no-store")
    handler.end_headers()
    handler.wfile.write(body)


def _safe_static_path(raw_path: str) -> Path | None:
    path = raw_path.split("?", 1)[0].split("#", 1)[0]
    if path in {"", "/"}:
        path = "/index.html"
    candidate = (WEB_DIR / path.lstrip("/")).resolve()
    try:
        candidate.relative_to(WEB_DIR)
    except ValueError:
        return None
    if candidate.is_dir():
        candidate = candidate / "index.html"
    return candidate


def _ollama_request(endpoint: str, payload: dict[str, Any] | None = None) -> tuple[int, dict[str, Any]]:
    url = f"{OLLAMA_URL}{endpoint}"
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="GET" if payload is None else "POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=240) as response:  # noqa: S310 - URL задаётся владельцем среды
            raw = response.read().decode("utf-8")
            return int(response.status), json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            body = json.loads(raw)
        except json.JSONDecodeError:
            body = {"error": raw or str(exc)}
        return int(exc.code), body
    except (urllib.error.URLError, TimeoutError) as exc:
        return HTTPStatus.BAD_GATEWAY, {
            "error": "Не удалось подключиться к Ollama",
            "details": str(exc),
            "ollama_url": OLLAMA_URL,
        }


class SiteHandler(BaseHTTPRequestHandler):
    server_version = "OdeKitAiSite/0.1"

    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"[{self.log_date_time_string()}] {self.address_string()} {fmt % args}", file=sys.stderr)

    def do_GET(self) -> None:  # noqa: N802 - интерфейс BaseHTTPRequestHandler
        if self.path == "/api/health":
            status, data = _ollama_request("/api/tags")
            _json_response(
                self,
                HTTPStatus.OK,
                {
                    "site": "ok",
                    "ollama_url": OLLAMA_URL,
                    "ollama_reachable": status == HTTPStatus.OK,
                    "ollama_status": status,
                    "models_count": len(data.get("models", [])) if isinstance(data, dict) else 0,
                    "ollama_response": data if status != HTTPStatus.OK else None,
                },
            )
            return

        if self.path == "/api/tags":
            status, data = _ollama_request("/api/tags")
            _json_response(self, status, data)
            return

        candidate = _safe_static_path(self.path)
        if candidate is None or not candidate.exists() or not candidate.is_file():
            _json_response(self, HTTPStatus.NOT_FOUND, {"error": "Файл не найден"})
            return

        content_type = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
        body = candidate.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:  # noqa: N802 - интерфейс BaseHTTPRequestHandler
        if self.path != "/api/chat":
            _json_response(self, HTTPStatus.NOT_FOUND, {"error": "Unknown API endpoint"})
            return

        content_length = int(self.headers.get("Content-Length", "0"))
        if content_length <= 0 or content_length > MAX_BODY_BYTES:
            _json_response(self, HTTPStatus.BAD_REQUEST, {"error": "Некорректный размер запроса"})
            return

        try:
            payload = json.loads(self.rfile.read(content_length).decode("utf-8"))
        except json.JSONDecodeError:
            _json_response(self, HTTPStatus.BAD_REQUEST, {"error": "Некорректный JSON"})
            return

        model = payload.get("model")
        messages = payload.get("messages")
        if not isinstance(model, str) or not model.strip() or len(model) > 120:
            _json_response(self, HTTPStatus.BAD_REQUEST, {"error": "Укажи корректную модель"})
            return
        if not isinstance(messages, list) or not messages:
            _json_response(self, HTTPStatus.BAD_REQUEST, {"error": "messages должен быть непустым списком"})
            return

        safe_messages: list[dict[str, str]] = []
        for item in messages[-40:]:
            if not isinstance(item, dict):
                continue
            role = item.get("role")
            content = item.get("content")
            if role not in {"system", "user", "assistant"} or not isinstance(content, str):
                continue
            safe_messages.append({"role": role, "content": content[:20_000]})

        if not safe_messages:
            _json_response(self, HTTPStatus.BAD_REQUEST, {"error": "Нет валидных сообщений"})
            return

        options = payload.get("options") if isinstance(payload.get("options"), dict) else {}
        ollama_payload = {
            "model": model.strip(),
            "stream": False,
            "messages": safe_messages,
            "options": {
                "temperature": float(options.get("temperature", 0.4)),
                "num_ctx": int(options.get("num_ctx", 4096)),
                "num_predict": int(options.get("num_predict", 512)),
            },
        }

        status, data = _ollama_request("/api/chat", ollama_payload)
        _json_response(self, status, data)


def main() -> int:
    parser = argparse.ArgumentParser(description="Ode KitAi local website")
    parser.add_argument("--host", default="127.0.0.1", help="Host для сайта")
    parser.add_argument("--port", default=7860, type=int, help="Port для сайта")
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), SiteHandler)
    print(f"Ode KitAi site: http://{args.host}:{args.port}")
    print(f"Ollama URL: {OLLAMA_URL}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nОстановлено.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
