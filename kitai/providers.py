"""Работа с провайдерами: описание, ключи, один общий OpenAI-совместимый вызов.

Все перечисленные провайдеры умеют формат OpenAI /chat/completions,
поэтому код вызова один на всех — меняются только base_url, ключ и модель.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import config as cfg


class ProviderError(RuntimeError):
    """Ошибка вызова провайдера, понятная человеку."""

    def __init__(self, message: str, *, status: Optional[int] = None, retryable: bool = False):
        super().__init__(message)
        self.status = status
        self.retryable = retryable


@dataclass
class Provider:
    id: str
    title: str
    kind: str
    base_url: str
    default_model: str
    models: List[str] = field(default_factory=list)
    api_key_env: Optional[str] = None
    api_key_required: bool = False
    base_url_env: Optional[str] = None
    limits: Dict[str, Any] = field(default_factory=dict)
    per_model_limits: Dict[str, Any] = field(default_factory=dict)
    privacy: str = ""
    cost: str = ""
    signup: str = ""
    docs: str = ""
    good_for: List[str] = field(default_factory=list)
    weak_for: List[str] = field(default_factory=list)

    @property
    def is_local(self) -> bool:
        return self.kind == "local"

    def resolved_base_url(self) -> str:
        """Переменная окружения важнее значения из конфига."""
        if self.base_url_env:
            env_value = os.environ.get(self.base_url_env, "").strip()
            if env_value:
                if self.id == "ollama" and not env_value.rstrip("/").endswith("/v1"):
                    return env_value.rstrip("/") + "/v1"
                return env_value.rstrip("/")
        return self.base_url.rstrip("/")

    def api_key(self) -> Optional[str]:
        if not self.api_key_env:
            return None
        value = os.environ.get(self.api_key_env, "").strip()
        return value or None

    def is_ready(self) -> bool:
        """Готов ли провайдер к работе прямо сейчас."""
        if not self.api_key_required:
            return True
        return self.api_key() is not None

    def readiness_hint(self) -> str:
        if self.is_ready():
            if self.api_key_env:
                return f"ключ {self.api_key_env}: {cfg.mask_secret(self.api_key())}"
            return "ключ не требуется"
        return f"нет ключа {self.api_key_env}. Получить: {self.signup}"

    def limit_summary(self) -> str:
        rpm = self.limits.get("rpm")
        rpd = self.limits.get("rpd")
        if rpm is None and rpd is None:
            return self.limits.get("note", "лимиты уточняй в документации")
        parts = []
        if rpm:
            parts.append(f"{rpm} запросов/мин")
        if rpd:
            parts.append(f"{rpd} запросов/сутки")
        return ", ".join(parts)


def load_providers(path: Path = cfg.PROVIDERS_FILE) -> Dict[str, Provider]:
    data = cfg.load_json(path)
    providers: Dict[str, Provider] = {}
    for raw in data.get("providers", []):
        provider = Provider(
            id=raw["id"],
            title=raw.get("title", raw["id"]),
            kind=raw.get("kind", "cloud_free"),
            base_url=raw.get("base_url", ""),
            default_model=raw.get("default_model", ""),
            models=list(raw.get("models", [])),
            api_key_env=raw.get("api_key_env"),
            api_key_required=bool(raw.get("api_key_required", False)),
            base_url_env=raw.get("base_url_env"),
            limits=dict(raw.get("limits", {})),
            per_model_limits=dict(raw.get("per_model_limits", {})),
            privacy=raw.get("privacy", ""),
            cost=raw.get("cost", ""),
            signup=raw.get("signup", ""),
            docs=raw.get("docs", ""),
            good_for=list(raw.get("good_for", [])),
            weak_for=list(raw.get("weak_for", [])),
        )
        providers[provider.id] = provider
    if not providers:
        raise ValueError(f"В {path} нет ни одного провайдера")
    return providers


def _extract_error_message(body: str, status: int) -> str:
    try:
        payload = json.loads(body)
    except (json.JSONDecodeError, TypeError):
        return body.strip()[:300] or f"HTTP {status}"
    error = payload.get("error")
    if isinstance(error, dict):
        return str(error.get("message") or error)[:300]
    if isinstance(error, str):
        return error[:300]
    return str(payload)[:300]


def chat_once(
    provider: Provider,
    messages: List[Dict[str, str]],
    *,
    model: Optional[str] = None,
    timeout: int = 120,
    temperature: float = 0.3,
    max_tokens: int = 1200,
) -> Dict[str, Any]:
    """Один запрос к провайдеру в формате OpenAI chat/completions."""
    model = model or provider.default_model
    if not model:
        raise ProviderError(f"Для провайдера {provider.id} не выбрана модель")

    if provider.api_key_required and not provider.api_key():
        raise ProviderError(
            f"Нет ключа {provider.api_key_env} для {provider.title}. Получить: {provider.signup}",
            retryable=False,
        )

    url = provider.resolved_base_url() + "/chat/completions"
    payload: Dict[str, Any] = {
        "model": model,
        "messages": messages,
        "stream": False,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    headers = {"Content-Type": "application/json"}
    key = provider.api_key()
    if key:
        headers["Authorization"] = f"Bearer {key}"
    if provider.id == "openrouter":
        # OpenRouter просит идентифицировать приложение, это часть их правил.
        headers["HTTP-Referer"] = "https://github.com/nurislamtagirov444-wq/-Ode-KitAi"
        headers["X-Title"] = "Ode KitAi"

    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )

    started = time.time()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
            body = response.read().decode("utf-8", errors="replace")
            data = json.loads(body)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        message = _extract_error_message(body, exc.code)
        retryable = exc.code in {408, 409, 429, 500, 502, 503, 504}
        human = message
        if exc.code == 429:
            human = f"лимит исчерпан или слишком часто (429): {message}"
        elif exc.code in {401, 403}:
            human = f"ключ не принят ({exc.code}): {message}"
        raise ProviderError(human, status=exc.code, retryable=retryable) from exc
    except urllib.error.URLError as exc:
        raise ProviderError(f"нет связи с {provider.title}: {exc.reason}", retryable=True) from exc
    except json.JSONDecodeError as exc:
        raise ProviderError(f"{provider.title} вернул не JSON: {exc}", retryable=True) from exc

    choices = data.get("choices") or []
    if not choices:
        raise ProviderError(f"{provider.title} вернул пустой ответ: {str(data)[:200]}", retryable=True)
    content = (choices[0].get("message") or {}).get("content")
    if not isinstance(content, str) or not content.strip():
        raise ProviderError(f"{provider.title} вернул ответ без текста", retryable=True)

    usage = data.get("usage") or {}
    return {
        "provider": provider.id,
        "model": data.get("model", model),
        "content": content.strip(),
        "elapsed": round(time.time() - started, 2),
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
    }


def ping(provider: Provider, *, timeout: int = 20, model: Optional[str] = None) -> Dict[str, Any]:
    """Короткая проверка: отвечает ли провайдер вообще."""
    if not provider.is_ready():
        return {"provider": provider.id, "ok": False, "reason": provider.readiness_hint()}
    try:
        result = chat_once(
            provider,
            [{"role": "user", "content": "Ответь одним словом: ok"}],
            model=model,
            timeout=timeout,
            max_tokens=16,
        )
    except ProviderError as exc:
        return {"provider": provider.id, "ok": False, "reason": str(exc), "status": exc.status}
    return {
        "provider": provider.id,
        "ok": True,
        "model": result["model"],
        "elapsed": result["elapsed"],
        "reply": result["content"][:60],
    }
