"""FastAPI service for Nithi Sahaya."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import threading
import time
from collections import deque
from dataclasses import dataclass
from functools import lru_cache
from typing import Iterator

from fastapi import FastAPI, HTTPException, Request as FastAPIRequest
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from scripts.ask import AnswerEngine

load_dotenv()
logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    created_at: float
    value: dict


class SlidingWindowLimiter:
    """Small in-process limiter; use a shared store when running multiple workers."""

    def __init__(self, limit: int, window_seconds: int) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self.requests: dict[str, deque[float]] = {}
        self.lock = threading.Lock()

    def allow(self, client: str) -> bool:
        now = time.monotonic()
        with self.lock:
            bucket = self.requests.setdefault(client, deque())
            while bucket and now - bucket[0] >= self.window_seconds:
                bucket.popleft()
            if len(bucket) >= self.limit:
                return False
            bucket.append(now)
            return True


class AskRequest(BaseModel):
    question: str = Field(min_length=2, max_length=4000)
    language: str = Field(default="English", min_length=2, max_length=32)


def cache_key(question: str, language: str, k: int) -> str:
    normalized = " ".join(question.casefold().split())
    raw = f"{language.casefold()}\0{k}\0{normalized}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def answer_chunks(result: dict, chunk_size: int = 256) -> Iterator[bytes]:
    """Yield answer metadata and text chunks using the text/event-stream format."""
    metadata = json.dumps({
        "sources": result.get("sources", []),
        "web_sources": result.get("web_sources", []),
        "refused": result.get("refused", False),
        "reason": result.get("reason"),
    }, ensure_ascii=False)
    yield f"event: metadata\ndata: {metadata}\n\n".encode("utf-8")
    answer = result.get("answer", "")
    for offset in range(0, len(answer), chunk_size):
        payload = json.dumps({"text": answer[offset:offset + chunk_size]}, ensure_ascii=False)
        yield f"data: {payload}\n\n".encode("utf-8")
    yield b"data: [DONE]\n\n"


@lru_cache(maxsize=1)
def get_engine() -> AnswerEngine:
    return AnswerEngine()


app = FastAPI(title="Nithi Sahaya API", version="1.0.0")
origins = [value.strip() for value in os.getenv("CORS_ORIGINS", "").split(",") if value.strip()]
if origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_methods=["POST", "GET"],
        allow_headers=["Content-Type"],
    )

limiter = SlidingWindowLimiter(
    limit=int(os.getenv("RATE_LIMIT_REQUESTS", "20")),
    window_seconds=int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60")),
)
cache: dict[str, CacheEntry] = {}
cache_lock = threading.Lock()
CACHE_TTL = int(os.getenv("ANSWER_CACHE_TTL_SECONDS", "3600"))
CACHE_MAX = int(os.getenv("ANSWER_CACHE_MAX_ENTRIES", "500"))


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/ask")
async def ask(payload: AskRequest, request: FastAPIRequest) -> StreamingResponse:
    client_ip = request.client.host if request.client else "unknown"
    if not limiter.allow(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Please try again shortly.")

    k = int(os.getenv("RETRIEVAL_TOP_K", "8"))
    key = cache_key(payload.question, payload.language, k)
    now = time.monotonic()
    with cache_lock:
        entry = cache.get(key)
        if entry and now - entry.created_at < CACHE_TTL:
            result = entry.value
        else:
            cache.pop(key, None)
            result = None

    if result is None:
        try:
            result = await asyncio.to_thread(lambda: get_engine().ask(payload.question, payload.language, k))
        except Exception as exc:
            # Keep internal exception details out of the response and avoid logging user text.
            cause = exc.__cause__
            logger.error(
                "Answer service failure (type=%s, stage=%s, status=%s, cause_type=%s, upstream=%s)",
                type(exc).__name__,
                getattr(exc, "stage", "unknown"),
                getattr(exc, "code", None) or getattr(exc, "status", None) or "unknown",
                type(cause).__name__ if cause else "none",
                getattr(exc, "detail", "") or "unavailable",
            )
            raise HTTPException(status_code=503, detail="The answer service is temporarily unavailable.") from exc
        with cache_lock:
            if len(cache) >= CACHE_MAX:
                oldest_key = min(cache, key=lambda item: cache[item].created_at)
                cache.pop(oldest_key, None)
            cache[key] = CacheEntry(time.monotonic(), result)

    return StreamingResponse(
        answer_chunks(result),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
    )
