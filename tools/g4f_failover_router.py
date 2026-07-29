#!/usr/bin/env python3
"""OpenAI-compatible failover router for local g4f provider routes.

FCC can point its llama.cpp-compatible base URL at this router.  The router
tries the configured g4f providers one at a time and returns the first one
that accepts the request.  It never logs prompt bodies or API credentials.

Usage:
  /root/g4f-venv/bin/python tools/g4f_failover_router.py \
    --config tools/g4f_failover_routes.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse
import uvicorn


class RouterConfig:
    def __init__(self, raw: dict[str, Any]) -> None:
        self.g4f_base_url = str(raw.get("g4f_base_url", "http://127.0.0.1:1337")).rstrip("/")
        self.host = str(raw.get("host", "127.0.0.1"))
        self.port = int(raw.get("port", 1340))
        self.timeout_seconds = float(raw.get("request_timeout_seconds", 45))
        self.routes = raw.get("routes", {})
        if not isinstance(self.routes, dict) or not self.routes:
            raise ValueError("config.routes must contain at least one model route")

    def candidates(self, requested_model: str) -> list[dict[str, str]]:
        candidates = self.routes.get(requested_model) or self.routes.get("default") or []
        valid: list[dict[str, str]] = []
        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue
            provider = candidate.get("provider")
            model = candidate.get("model")
            if isinstance(provider, str) and isinstance(model, str):
                valid.append({"provider": provider, "model": model})
        return valid


def load_config(path: Path) -> RouterConfig:
    return RouterConfig(json.loads(path.read_text(encoding="utf-8")))


def openai_error(message: str, status_code: int = 502) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"message": message, "type": "g4f_failover_error"}},
    )


def filtered_headers(request: Request) -> dict[str, str]:
    """Forward only headers that are useful to the local g4f server."""
    headers = {"content-type": request.headers.get("content-type", "application/json")}
    if request.headers.get("accept"):
        headers["accept"] = request.headers["accept"]
    return headers


async def relay_stream(upstream: httpx.Response):
    try:
        async for chunk in upstream.aiter_raw():
            yield chunk
    finally:
        await upstream.aclose()


def create_app(config: RouterConfig) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.client = httpx.AsyncClient(timeout=httpx.Timeout(config.timeout_seconds))
        yield
        await app.state.client.aclose()

    app = FastAPI(title="Local g4f failover router", lifespan=lifespan)

    @app.get("/health")
    async def health() -> dict[str, Any]:
        return {
            "ok": True,
            "upstream": config.g4f_base_url,
            "models": sorted(key for key in config.routes if key != "default"),
            "timeout_seconds": config.timeout_seconds,
        }

    @app.get("/v1/models")
    async def models() -> dict[str, Any]:
        model_names = sorted(key for key in config.routes if key != "default")
        return {
            "object": "list",
            "data": [{"id": model, "object": "model", "owned_by": "g4f-failover"} for model in model_names],
        }

    @app.post("/v1/chat/completions")
    async def chat_completions(request: Request) -> Response:
        try:
            payload = await request.json()
        except json.JSONDecodeError:
            return openai_error("Request body must be JSON", 400)

        if not isinstance(payload, dict):
            return openai_error("Request body must be a JSON object", 400)

        requested_model = payload.get("model")
        if not isinstance(requested_model, str) or not requested_model:
            return openai_error("Request must include a model", 400)

        candidates = config.candidates(requested_model)
        if not candidates:
            return openai_error(f"No failover routes configured for model '{requested_model}'", 400)

        client: httpx.AsyncClient = request.app.state.client
        errors: list[str] = []
        for candidate in candidates:
            upstream_payload = dict(payload)
            upstream_payload["model"] = candidate["model"]
            url = f"{config.g4f_base_url}/api/{candidate['provider']}/chat/completions"
            try:
                upstream_request = client.build_request(
                    "POST", url, json=upstream_payload, headers=filtered_headers(request)
                )
                upstream = await client.send(upstream_request, stream=True)
                if upstream.status_code >= 400:
                    errors.append(f"{candidate['provider']}/{candidate['model']}: HTTP {upstream.status_code}")
                    await upstream.aclose()
                    continue

                content_type = upstream.headers.get("content-type", "application/json")
                if payload.get("stream"):
                    return StreamingResponse(
                        relay_stream(upstream),
                        status_code=upstream.status_code,
                        media_type=content_type,
                    )

                content = await upstream.aread()
                await upstream.aclose()
                return Response(content=content, status_code=200, media_type=content_type)
            except (httpx.TimeoutException, httpx.HTTPError) as exc:
                errors.append(f"{candidate['provider']}/{candidate['model']}: {type(exc).__name__}")

        return openai_error("All configured g4f routes failed: " + "; ".join(errors))

    return app


def main() -> None:
    parser = argparse.ArgumentParser(description="Local sequential failover router for g4f")
    parser.add_argument("--config", type=Path, required=True, help="Path to JSON routing configuration")
    args = parser.parse_args()
    config = load_config(args.config)
    uvicorn.run(create_app(config), host=config.host, port=config.port)


if __name__ == "__main__":
    main()
