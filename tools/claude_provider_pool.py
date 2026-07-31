#!/usr/bin/env python3
"""Anthropic-compatible local failover gateway for Claude Code.

Provider source file format (one provider per line):
  KEY | URL | PROVIDER

The gateway reads the file on every request, so adding/removing a line in the
Android file manager takes effect without restarting it. It never returns keys
in status responses or logs prompt bodies.
"""
from __future__ import annotations

import hashlib
import os
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse
import uvicorn

def provider_file() -> Path:
    explicit = os.environ.get("CLAUDE_PROVIDER_FILE")
    candidates = [
        Path(explicit) if explicit else None,
        Path("/mnt/sdcard/ARMY/providers/claude.providers"),
        Path("/sdcard/ARMY/providers/claude.providers"),
    ]
    for candidate in candidates:
        if candidate and candidate.exists():
            return candidate
    return Path("/sdcard/ARMY/providers/claude.providers")


PROVIDER_FILE = provider_file()
MODEL = "claude-sonnet-5"
TIMEOUT_SECONDS = 90.0
RATE_LIMIT_PAUSE = 15 * 60
TRANSIENT_PAUSE = 5 * 60


@dataclass(frozen=True)
class Provider:
    key: str
    url: str
    name: str


# name -> (retry_after_epoch, reason). Keys are intentionally not retained here.
paused: dict[str, tuple[float, str]] = {}


def load_providers() -> list[Provider]:
    if not PROVIDER_FILE.exists():
        return []
    result: list[Provider] = []
    for raw in PROVIDER_FILE.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = [piece.strip() for piece in line.split("|")]
        if len(parts) != 3 or not all(parts):
            continue
        key, url, name = parts
        result.append(Provider(key=key, url=url.rstrip("/"), name=name))
    return result


def provider_id(provider: Provider) -> str:
    # A changed key becomes a new route without exposing the key in status/logs.
    fingerprint = hashlib.sha256(provider.key.encode()).hexdigest()[:12]
    return f"{provider.name}@{provider.url}#{fingerprint}"


def eligible(providers: list[Provider]) -> list[Provider]:
    now = time.time()
    return [p for p in providers if paused.get(provider_id(p), (0.0, ""))[0] <= now]


def pause(provider: Provider, seconds: int, reason: str) -> None:
    paused[provider_id(provider)] = (time.time() + seconds, reason)


def upstream_headers(request: Request, provider: Provider) -> dict[str, str]:
    headers = {
        "authorization": f"Bearer {provider.key}",
        "content-type": "application/json",
        "anthropic-version": request.headers.get("anthropic-version", "2023-06-01"),
    }
    for key in ("anthropic-beta", "user-agent"):
        if request.headers.get(key):
            headers[key] = request.headers[key]
    return headers


def error(message: str, status: int = 503) -> JSONResponse:
    return JSONResponse({"type": "error", "error": {"type": "api_error", "message": message}}, status_code=status)


async def relay(response: httpx.Response):
    try:
        async for chunk in response.aiter_raw():
            yield chunk
    finally:
        await response.aclose()


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.client = httpx.AsyncClient(timeout=httpx.Timeout(TIMEOUT_SECONDS))
    yield
    await app.state.client.aclose()


app = FastAPI(title="Claude Provider Pool", lifespan=lifespan)


@app.get("/health")
async def health() -> dict[str, Any]:
    providers = load_providers()
    now = time.time()
    return {
        "ok": True,
        "model": MODEL,
        "configured_providers": len(providers),
        "eligible_providers": len(eligible(providers)),
        "paused": [
            {"provider": name, "retry_after_seconds": max(0, int(until - now)), "reason": reason}
            for name, (until, reason) in paused.items() if until > now
        ],
    }


@app.post("/v1/messages")
async def messages(request: Request):
    try:
        body = await request.json()
    except ValueError:
        return error("Request body must be JSON", 400)
    if not isinstance(body, dict):
        return error("Request body must be a JSON object", 400)

    providers = load_providers()
    candidates = eligible(providers)
    if not candidates:
        return error("No eligible providers in claude.providers. Add KEY | URL | PROVIDER lines or wait for paused routes.")

    client: httpx.AsyncClient = request.app.state.client
    failures: list[str] = []
    for provider in candidates:
        payload = dict(body)
        payload["model"] = MODEL
        try:
            upstream_request = client.build_request(
                "POST", f"{provider.url}/v1/messages", json=payload, headers=upstream_headers(request, provider)
            )
            response = await client.send(upstream_request, stream=True)
            if response.status_code < 400:
                if payload.get("stream"):
                    return StreamingResponse(relay(response), media_type=response.headers.get("content-type", "text/event-stream"))
                content = await response.aread()
                await response.aclose()
                return Response(content, status_code=200, media_type="application/json")

            code = response.status_code
            await response.aclose()
            if code in (401, 403, 402):
                pause(provider, 24 * 60 * 60, f"HTTP {code}")
            elif code == 429:
                pause(provider, RATE_LIMIT_PAUSE, "HTTP 429")
            else:
                pause(provider, TRANSIENT_PAUSE, f"HTTP {code}")
            failures.append(f"{provider.name}: HTTP {code}")
        except (httpx.TimeoutException, httpx.HTTPError) as exc:
            pause(provider, TRANSIENT_PAUSE, type(exc).__name__)
            failures.append(f"{provider.name}: {type(exc).__name__}")

    return error("All configured Claude providers failed: " + "; ".join(failures))


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=1342)
