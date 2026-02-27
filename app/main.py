"""
FastAPI application entry point
"""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from lmnr import Laminar

from app import config
from app.core.store import store
from app.routers import chat, qa, search

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)

Laminar.initialize(project_api_key=os.getenv("LMNR_PROJECT_API_KEY"))


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

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(search.router)
app.include_router(chat.router)
app.include_router(qa.router)


@app.get("/health", tags=["infra"])
def health() -> dict:
    return {"status": "ok", "qa_count": len(store.items)}
