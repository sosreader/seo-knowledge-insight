"""
SEO Insight API 設定
從環境變數讀取，不依賴 pipeline 的 config.py
"""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# ── OpenAI ─────────────────────────────────────────────
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-5.2")
OPENAI_EMBEDDING_MODEL: str = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")

# ── 資料路徑 ────────────────────────────────────────────
ROOT_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT_DIR / "output"
QA_JSON_PATH = OUTPUT_DIR / "qa_final.json"
QA_EMBEDDINGS_PATH = OUTPUT_DIR / "qa_embeddings.npy"

# ── API ─────────────────────────────────────────────────
CORS_ORIGINS: list[str] = [
    o.strip()
    for o in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
    if o.strip()
]

# ── RAG ─────────────────────────────────────────────────
SEARCH_TOP_K: int = int(os.getenv("SEARCH_TOP_K", "5"))
CHAT_CONTEXT_K: int = int(os.getenv("CHAT_CONTEXT_K", "5"))
