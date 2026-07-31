#!/usr/bin/env python3
"""Small local OpenAI-compatible proxy for Tooken Club.
The upstream key is read only from TOOKEN_API_KEY in this process environment.
"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse
import uvicorn

UPSTREAM = os.environ.get("TOOKEN_BASE_URL", "https://tooken.club/v1").rstrip("/")
KEY = os.environ.get("TOOKEN_API_KEY", "")


def error(message: str, code: int = 500) -> JSONResponse:
    return JSONResponse({"error": {"message": message, "type": "tooken_proxy_error"}}, status_code=code)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not KEY:
        raise RuntimeError("TOOKEN_API_KEY is not set")
    app.state.client = httpx.AsyncClient(timeout=httpx.Timeout(120.0))
    yield
    await app.state.client.aclose()


app = FastAPI(title="Local Tooken proxy", lifespan=lifespan)


def headers(request: Request) -> dict[str, str]:
    result = {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}
    if request.headers.get("accept"):
        result["Accept"] = request.headers["accept"]
    return result


@app.get("/health")
async def health() -> dict[str, object]:
    return {"ok": True, "upstream": UPSTREAM, "key_configured": bool(KEY)}


@app.get("/v1/models")
async def models(request: Request):
    client: httpx.AsyncClient = request.app.state.client
    try:
        response = await client.get(f"{UPSTREAM}/models", headers=headers(request))
        return Response(response.content, status_code=response.status_code, media_type="application/json")
    except httpx.HTTPError as exc:
        return error(f"Could not list Tooken models: {type(exc).__name__}", 502)


async def stream(response: httpx.Response):
    try:
        async for chunk in response.aiter_raw():
            yield chunk
    finally:
        await response.aclose()


@app.post("/v1/chat/completions")
async def chat(request: Request):
    try:
        body = await request.json()
    except ValueError:
        return error("Request body must be JSON", 400)
    client: httpx.AsyncClient = request.app.state.client
    try:
        upstream_request = client.build_request("POST", f"{UPSTREAM}/chat/completions", json=body, headers=headers(request))
        response = await client.send(upstream_request, stream=True)
        if response.status_code >= 400:
            content = await response.aread()
            await response.aclose()
            return Response(content, status_code=response.status_code, media_type="application/json")
        if body.get("stream"):
            return StreamingResponse(stream(response), media_type=response.headers.get("content-type", "text/event-stream"))
        content = await response.aread()
        await response.aclose()
        return Response(content, media_type=response.headers.get("content-type", "application/json"))
    except httpx.HTTPError as exc:
        return error(f"Tooken request failed: {type(exc).__name__}", 502)


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=1341)
