#!/usr/bin/env python3
"""Мини-сервер для сайта Ode KitAi.

- Раздаёт статические файлы из папки web/.
- Даёт единый /api/chat для нескольких AI-провайдеров.
- Может работать без скачивания локальной модели через remote/free-tier провайдеры.
- Не требует внешних Python-зависимостей.

Запуск:
    python3 web/server.py

Переменные окружения:
    OLLAMA_URL=http://localhost:11434
    POLLINATIONS_API_KEY=pk_...        # опционально
    OPENROUTER_API_KEY=sk-or-...       # опционально
    GROQ_API_KEY=gsk_...               # опционально
    OPENAI_COMPATIBLE_BASE_URL=...     # опционально, например https://api.example.com/v1
    OPENAI_COMPATIBLE_API_KEY=...      # опционально
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

WEB_DIR = Path(__file__).resolve().parent
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434").rstrip("/")
POLLINATIONS_BASE_URL = os.environ.get("POLLINATIONS_BASE_URL", "https://gen.pollinations.ai").rstrip("/")
POLLINATIONS_API_KEY = os.environ.get("POLLINATIONS_API_KEY", "").strip()
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "").strip()
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "").strip()
OPENAI_COMPATIBLE_BASE_URL = os.environ.get("OPENAI_COMPATIBLE_BASE_URL", "").rstrip("/")
OPENAI_COMPATIBLE_API_KEY = os.environ.get("OPENAI_COMPATIBLE_API_KEY", "").strip()
MAX_BODY_BYTES = 2_000_000
MAX_PROMPT_CHARS_FOR_SIMPLE_GET = 12_000

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


def _read_json_or_text(exc: urllib.error.HTTPError) -> dict[str, Any]:
    raw = exc.read().decode("utf-8", errors="replace")
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return parsed
        return {"error": parsed}
    except json.JSONDecodeError:
        return {"error": raw or str(exc)}


def _request_json(
    url: str,
    *,
    payload: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: int = 240,
) -> tuple[int, dict[str, Any]]:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    merged_headers = {"Content-Type": "application/json", "User-Agent": "OdeKitAi/0.2"}
    if headers:
        merged_headers.update(headers)
    request = urllib.request.Request(
        url,
        data=data,
        headers=merged_headers,
        method="GET" if payload is None else "POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 - провайдер выбирается владельцем сайта
            raw = response.read().decode("utf-8", errors="replace")
            try:
                body = json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                body = {"text": raw}
            return int(response.status), body if isinstance(body, dict) else {"data": body}
    except urllib.error.HTTPError as exc:
        return int(exc.code), _read_json_or_text(exc)
    except (urllib.error.URLError, TimeoutError) as exc:
        return HTTPStatus.BAD_GATEWAY, {"error": "Не удалось подключиться к провайдеру", "details": str(exc), "url": url}


def _request_text(url: str, *, headers: dict[str, str] | None = None, timeout: int = 240) -> tuple[int, str | dict[str, Any]]:
    merged_headers = {"User-Agent": "OdeKitAi/0.2"}
    if headers:
        merged_headers.update(headers)
    request = urllib.request.Request(url, headers=merged_headers, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 - провайдер выбирается владельцем сайта
            return int(response.status), response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        return int(exc.code), _read_json_or_text(exc)
    except (urllib.error.URLError, TimeoutError) as exc:
        return HTTPStatus.BAD_GATEWAY, {"error": "Не удалось подключиться к провайдеру", "details": str(exc), "url": url}


def _ollama_request(endpoint: str, payload: dict[str, Any] | None = None) -> tuple[int, dict[str, Any]]:
    status, data = _request_json(f"{OLLAMA_URL}{endpoint}", payload=payload)
    if status == HTTPStatus.BAD_GATEWAY:
        data.update({"ollama_url": OLLAMA_URL})
    return status, data


def _messages_to_plain_prompt(messages: list[dict[str, str]]) -> str:
    labels = {"system": "СИСТЕМНЫЕ ПРАВИЛА", "user": "ПОЛЬЗОВАТЕЛЬ", "assistant": "АССИСТЕНТ"}
    chunks = []
    for message in messages:
        role = labels.get(message["role"], message["role"].upper())
        chunks.append(f"{role}:\n{message['content']}")
    chunks.append("АССИСТЕНТ:")
    return "\n\n".join(chunks)


def _extract_openai_content(data: dict[str, Any]) -> str:
    choices = data.get("choices")
    if isinstance(choices, list) and choices:
        first = choices[0]
        if isinstance(first, dict):
            message = first.get("message")
            if isinstance(message, dict):
                content = message.get("content")
                if isinstance(content, str):
                    return content
                if isinstance(content, list):
                    parts: list[str] = []
                    for item in content:
                        if isinstance(item, dict) and isinstance(item.get("text"), str):
                            parts.append(item["text"])
                    if parts:
                        return "\n".join(parts)
            text = first.get("text")
            if isinstance(text, str):
                return text
    message = data.get("message")
    if isinstance(message, dict) and isinstance(message.get("content"), str):
        return str(message["content"])
    text = data.get("text")
    if isinstance(text, str):
        return text
    return json.dumps(data, ensure_ascii=False, indent=2)


def _openai_compatible_request(
    *,
    provider_name: str,
    base_url: str,
    api_key: str,
    model: str,
    messages: list[dict[str, str]],
    options: dict[str, Any],
    require_key: bool = True,
    extra_headers: dict[str, str] | None = None,
) -> tuple[int, dict[str, Any]]:
    if require_key and not api_key:
        return HTTPStatus.BAD_REQUEST, {
            "error": f"Для провайдера {provider_name} нужен API key в переменной окружения сервера.",
            "details": "Не отправляй ключ в чат. Задай переменную окружения локально и перезапусти сайт.",
        }
    if not base_url:
        return HTTPStatus.BAD_REQUEST, {"error": f"Для провайдера {provider_name} не задан base_url"}

    headers: dict[str, str] = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    if extra_headers:
        headers.update(extra_headers)

    payload = {
        "model": model,
        "messages": messages,
        "temperature": float(options.get("temperature", 0.4)),
        "max_tokens": int(options.get("num_predict", 512)),
        "stream": False,
    }
    status, data = _request_json(f"{base_url.rstrip('/')}/chat/completions", payload=payload, headers=headers)
    if status >= 400:
        data.setdefault("provider", provider_name)
        return status, data
    return status, {
        "provider": provider_name,
        "message": {"role": "assistant", "content": _extract_openai_content(data)},
        "raw": data,
    }


def _pollinations_request(model: str, messages: list[dict[str, str]], options: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    # Если пользователь задал ключ Pollinations — используем нормальный OpenAI-compatible chat endpoint.
    if POLLINATIONS_API_KEY:
        return _openai_compatible_request(
            provider_name="pollinations",
            base_url=f"{POLLINATIONS_BASE_URL}/v1",
            api_key=POLLINATIONS_API_KEY,
            model=model or "mistral",
            messages=messages,
            options=options,
            require_key=True,
        )

    # Без ключа используем простой text endpoint. Он хуже для истории диалога, зато не требует скачивания модели.
    plain_prompt = _messages_to_plain_prompt(messages)[-MAX_PROMPT_CHARS_FOR_SIMPLE_GET:]
    query = urllib.parse.urlencode({"model": model or "mistral"})
    url = f"{POLLINATIONS_BASE_URL}/text/{urllib.parse.quote(plain_prompt, safe='')}?{query}"
    status, data = _request_text(url)
    if status >= 400:
        return status, {"provider": "pollinations-simple", "error": data}
    return status, {"provider": "pollinations-simple", "message": {"role": "assistant", "content": str(data)}}


def _provider_status_payload() -> dict[str, Any]:
    return {
        "pollinations": {
            "label": "Pollinations no-download",
            "requires_local_model": False,
            "requires_server_key": False,
            "configured": True,
            "note": "Работает через интернет. Без ключа используется простой text endpoint; с POLLINATIONS_API_KEY — chat endpoint.",
        },
        "puter": {
            "label": "Puter.js browser AI",
            "requires_local_model": False,
            "requires_server_key": False,
            "configured": True,
            "note": "Работает в браузере через аккаунт Puter. Серверный API не нужен.",
        },
        "openrouter": {
            "label": "OpenRouter",
            "requires_local_model": False,
            "requires_server_key": True,
            "configured": bool(OPENROUTER_API_KEY),
            "env": "OPENROUTER_API_KEY",
        },
        "groq": {
            "label": "Groq",
            "requires_local_model": False,
            "requires_server_key": True,
            "configured": bool(GROQ_API_KEY),
            "env": "GROQ_API_KEY",
        },
        "custom-openai": {
            "label": "Custom OpenAI-compatible",
            "requires_local_model": False,
            "requires_server_key": False,
            "configured": bool(OPENAI_COMPATIBLE_BASE_URL),
            "env": "OPENAI_COMPATIBLE_BASE_URL / OPENAI_COMPATIBLE_API_KEY",
        },
        "ollama": {
            "label": "Ollama local",
            "requires_local_model": True,
            "requires_server_key": False,
            "configured": True,
            "ollama_url": OLLAMA_URL,
        },
    }


class SiteHandler(BaseHTTPRequestHandler):
    server_version = "OdeKitAiSite/0.2"

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
                    "providers": _provider_status_payload(),
                },
            )
            return

        if self.path == "/api/providers":
            _json_response(self, HTTPStatus.OK, {"providers": _provider_status_payload()})
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

        provider = str(payload.get("provider", "pollinations")).strip().lower()
        model = payload.get("model")
        messages = payload.get("messages")
        if not isinstance(model, str) or not model.strip() or len(model) > 180:
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

        if provider == "ollama":
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
        elif provider == "pollinations":
            status, data = _pollinations_request(model.strip(), safe_messages, options)
        elif provider == "openrouter":
            status, data = _openai_compatible_request(
                provider_name="openrouter",
                base_url="https://openrouter.ai/api/v1",
                api_key=OPENROUTER_API_KEY,
                model=model.strip(),
                messages=safe_messages,
                options=options,
                extra_headers={"HTTP-Referer": "http://localhost:7860", "X-Title": "Ode KitAi"},
            )
        elif provider == "groq":
            status, data = _openai_compatible_request(
                provider_name="groq",
                base_url="https://api.groq.com/openai/v1",
                api_key=GROQ_API_KEY,
                model=model.strip(),
                messages=safe_messages,
                options=options,
            )
        elif provider == "custom-openai":
            status, data = _openai_compatible_request(
                provider_name="custom-openai",
                base_url=OPENAI_COMPATIBLE_BASE_URL,
                api_key=OPENAI_COMPATIBLE_API_KEY,
                model=model.strip(),
                messages=safe_messages,
                options=options,
                require_key=False,
            )
        else:
            status, data = HTTPStatus.BAD_REQUEST, {"error": f"Неизвестный провайдер: {provider}"}

        _json_response(self, status, data)


def main() -> int:
    parser = argparse.ArgumentParser(description="Ode KitAi local/no-download website")
    parser.add_argument("--host", default="127.0.0.1", help="Host для сайта")
    parser.add_argument("--port", default=7860, type=int, help="Port для сайта")
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), SiteHandler)
    print(f"Ode KitAi site: http://{args.host}:{args.port}")
    print(f"Ollama URL: {OLLAMA_URL}")
    print("No-download providers: pollinations, puter(browser), openrouter(env), groq(env), custom-openai(env)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nОстановлено.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
