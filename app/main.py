"""
FastAPI application entry point
"""
from __future__ import annotations

import logging
import os

# ── Laminar 必須在所有 LLM SDK 載入前初始化，才能正確 auto-instrument OpenAI ──
# Laminar.initialize() 會 monkey-patch openai / anthropic 等 SDK。
# 若在 `from app.routers import chat` 之後才初始化，openai 已被 import，patch 失效，
# 導致 Top LLM spans / Tokens / Cost dashboard 全空白。
_lmnr_key = os.getenv("LMNR_PROJECT_API_KEY", "")
try:
    from lmnr import Laminar
    if _lmnr_key:
        Laminar.initialize(project_api_key=_lmnr_key)
except ImportError:
    Laminar = None  # type: ignore[assignment,misc]

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app import config
from app.core.limiter import limiter
from app.core.security import verify_api_key
from app.core.store import store
from app.routers import chat, feedback, qa, search

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)

if not _lmnr_key:
    logger.warning("LMNR_PROJECT_API_KEY not set — Laminar tracing disabled")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 啟動時載入資料
    logger.info("Loading QA store from %s ...", config.QA_JSON_PATH)
    store.load()
    logger.info("QA store ready: %d items", len(store.items))
    yield
    # 關閉時不需清理，GC 會回收


app = FastAPI(
    title="SEO Insight API",
    version="1.0.0",
    description="SEO 知識庫語意搜尋與 RAG 問答 API",
    lifespan=lifespan,
)

# ── Phase B：Rate Limit 狀態掛載 ─────────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Phase C：全局 Exception Handler ──────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Unhandled exception: %s", exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"data": None, "error": "Internal server error", "meta": {}},
    )


# ── Phase A：Auth dependency 掛在所有 /api/v1 路由 ───────────────────────────
_auth = [Depends(verify_api_key)]

app.include_router(search.router, dependencies=_auth)
app.include_router(chat.router, dependencies=_auth)
app.include_router(qa.router, dependencies=_auth)
app.include_router(feedback.router, dependencies=_auth)


@app.get("/health", tags=["infra"])
def health() -> dict:
    return {"status": "ok", "qa_count": len(store.items)}
