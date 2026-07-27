"""Стратегия: какой провайдер вызвать первым и куда падать при отказе.

Главная идея: бесплатные лимиты кончаются, поэтому запрос идёт по цепочке.
Кончился Groq — идём в Gemini, кончился Gemini — в GitHub Models, в самом
конце локальная модель, у которой лимита по количеству запросов нет.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from . import config as cfg
from .providers import Provider, ProviderError, chat_once, load_providers


@dataclass
class Step:
    provider: str
    model: Optional[str] = None


@dataclass
class Profile:
    name: str
    title: str
    description: str
    chain: List[Step]
    allow_cloud: bool = True


@dataclass
class Attempt:
    provider: str
    model: Optional[str]
    ok: bool
    detail: str
    status: Optional[int] = None
    elapsed: Optional[float] = None


@dataclass
class RouteResult:
    ok: bool
    content: str = ""
    provider: Optional[str] = None
    model: Optional[str] = None
    elapsed: Optional[float] = None
    attempts: List[Attempt] = field(default_factory=list)

    def explain(self) -> str:
        """Публичный разбор: что пробовали и почему получилось так."""
        lines = []
        for index, attempt in enumerate(self.attempts, start=1):
            mark = "ok" if attempt.ok else "нет"
            model = attempt.model or "модель по умолчанию"
            lines.append(f"  {index}. {attempt.provider} / {model} — {mark}: {attempt.detail}")
        return "\n".join(lines) if lines else "  попыток не было"


class StrategyConfig:
    def __init__(self, data: Dict[str, Any]):
        self.raw = data
        self.active_profile: str = data.get("active_profile", "balanced")
        self.answer_format: Dict[str, Any] = data.get("answer_format", {})
        self.model_preferences: Dict[str, Any] = data.get("model_preferences", {})
        self.runtime: Dict[str, Any] = data.get("runtime", {})
        self.profiles: Dict[str, Profile] = {}
        for name, raw in (data.get("profiles") or {}).items():
            chain = [
                Step(provider=item["provider"], model=item.get("model"))
                for item in raw.get("chain", [])
                if item.get("provider")
            ]
            self.profiles[name] = Profile(
                name=name,
                title=raw.get("title", name),
                description=raw.get("description", ""),
                chain=chain,
                allow_cloud=bool(raw.get("allow_cloud", True)),
            )

    @classmethod
    def load(cls, path: Path = cfg.STRATEGY_FILE) -> "StrategyConfig":
        return cls(cfg.load_json(path))

    def save(self, path: Path = cfg.STRATEGY_FILE) -> None:
        self.raw["active_profile"] = self.active_profile
        cfg.save_json(path, self.raw)

    def profile(self, name: Optional[str] = None) -> Profile:
        name = name or self.active_profile
        if name not in self.profiles:
            available = ", ".join(sorted(self.profiles))
            raise KeyError(f"Профиль '{name}' не найден. Есть: {available}")
        return self.profiles[name]

    def set_active(self, name: str) -> Profile:
        profile = self.profile(name)
        self.active_profile = name
        return profile

    def avoided_families(self) -> List[str]:
        return [str(x).lower() for x in self.model_preferences.get("avoid_families", [])]

    def check_model_preference(self, model: Optional[str]) -> Optional[str]:
        """Вернуть предупреждение, если модель из нежелательного семейства."""
        if not model:
            return None
        lowered = model.lower()
        for family in self.avoided_families():
            if family in lowered:
                reason = self.model_preferences.get("avoid_reason", "")
                return f"модель '{model}' относится к семейству '{family}', которое ты просил не использовать. {reason}".strip()
        return None


def build_system_prompt(strategy: StrategyConfig, *, strategist: bool = True) -> str:
    """Системный промпт из настроек, а не захардкоженный текст."""
    fmt = strategy.answer_format
    lines = [
        "Ты практичный помощник-архитектор для пользователя-новичка.",
        "Отвечай на русском языке, спокойно и по шагам.",
    ]
    if fmt.get("no_emoji", True):
        lines.append("Не используй эмодзи, стикеры и рекламные слова.")
    if fmt.get("beginner_mode", True):
        lines.append(
            "Пользователь новичок: для каждого шага пиши что сделать, зачем, "
            "точную команду, нормальный результат и что делать при ошибке."
        )
    avoid = strategy.avoided_families()
    if avoid:
        lines.append(
            "Не рекомендуй по умолчанию модели семейств: "
            + ", ".join(avoid)
            + ". Предлагай альтернативы: Llama, Mistral, Gemma, Phi."
        )
    lines.append("Не выдумывай факты, версии, цены и лимиты. Если не уверен — скажи об этом прямо.")
    if strategist:
        sections = fmt.get("sections") or []
        if sections:
            lines.append("Для сложных задач используй структуру: " + " -> ".join(sections) + ".")
        final_block = fmt.get("final_block")
        if final_block:
            lines.append(f"В конце большого ответа добавь блок: {final_block}")
            lines.append("После него добавь строку 'СЛЕДУЮЩИЙ ЗАПРОС:' и один короткий запрос.")
    return "\n".join(lines)


class Router:
    """Выполняет запрос по цепочке провайдеров из активного профиля."""

    def __init__(
        self,
        providers: Optional[Dict[str, Provider]] = None,
        strategy: Optional[StrategyConfig] = None,
        *,
        chat_fn=chat_once,
    ):
        self.providers = providers if providers is not None else load_providers()
        self.strategy = strategy if strategy is not None else StrategyConfig.load()
        self._chat = chat_fn

    def plan(self, profile_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Показать план без запуска: кто готов, кто нет."""
        profile = self.strategy.profile(profile_name)
        rows = []
        for step in profile.chain:
            provider = self.providers.get(step.provider)
            if provider is None:
                rows.append(
                    {
                        "provider": step.provider,
                        "model": step.model,
                        "ready": False,
                        "reason": "провайдер не описан в config/providers.json",
                    }
                )
                continue
            skipped_by_policy = not profile.allow_cloud and not provider.is_local
            rows.append(
                {
                    "provider": provider.id,
                    "title": provider.title,
                    "model": step.model or provider.default_model,
                    "ready": provider.is_ready() and not skipped_by_policy,
                    "reason": (
                        "профиль запрещает облако"
                        if skipped_by_policy
                        else provider.readiness_hint()
                    ),
                    "limits": provider.limit_summary(),
                    "local": provider.is_local,
                }
            )
        return rows

    def run(
        self,
        messages: Sequence[Dict[str, str]],
        *,
        profile_name: Optional[str] = None,
        provider_override: Optional[str] = None,
        model_override: Optional[str] = None,
    ) -> RouteResult:
        runtime = self.strategy.runtime
        timeout = int(runtime.get("timeout_seconds", 120))
        retries = int(runtime.get("max_retries_per_step", 1))
        backoff = float(runtime.get("backoff_seconds", 2))
        temperature = float(runtime.get("temperature", 0.3))
        max_tokens = int(runtime.get("max_tokens", 1200))

        if provider_override:
            if provider_override not in self.providers:
                available = ", ".join(sorted(self.providers))
                raise KeyError(f"Провайдер '{provider_override}' не найден. Есть: {available}")
            chain = [Step(provider=provider_override, model=model_override)]
            allow_cloud = True
        else:
            profile = self.strategy.profile(profile_name)
            chain = profile.chain
            allow_cloud = profile.allow_cloud

        result = RouteResult(ok=False)
        payload = list(messages)

        for step in chain:
            provider = self.providers.get(step.provider)
            if provider is None:
                result.attempts.append(
                    Attempt(step.provider, step.model, False, "нет в config/providers.json")
                )
                continue
            if not allow_cloud and not provider.is_local:
                result.attempts.append(
                    Attempt(provider.id, step.model, False, "профиль запрещает облачных провайдеров")
                )
                continue
            if not provider.is_ready():
                result.attempts.append(
                    Attempt(provider.id, step.model, False, provider.readiness_hint())
                )
                continue

            model = model_override or step.model or provider.default_model
            for attempt_index in range(retries + 1):
                try:
                    response = self._chat(
                        provider,
                        payload,
                        model=model,
                        timeout=timeout,
                        temperature=temperature,
                        max_tokens=max_tokens,
                    )
                except ProviderError as exc:
                    last = attempt_index >= retries or not exc.retryable
                    result.attempts.append(
                        Attempt(provider.id, model, False, str(exc), status=exc.status)
                    )
                    if last:
                        break
                    time.sleep(backoff)
                    continue

                result.ok = True
                result.content = response["content"]
                result.provider = provider.id
                result.model = response["model"]
                result.elapsed = response["elapsed"]
                result.attempts.append(
                    Attempt(
                        provider.id,
                        response["model"],
                        True,
                        f"ответ получен за {response['elapsed']} c",
                        elapsed=response["elapsed"],
                    )
                )
                return result

        return result
