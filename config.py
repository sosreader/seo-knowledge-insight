"""
專案設定 — 從 .env 讀取，或使用預設值
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── 路徑 ──────────────────────────────────────────────
ROOT_DIR = Path(__file__).resolve().parent
RAW_JSON_DIR = ROOT_DIR / "raw_data" / "notion_json"
RAW_MD_DIR = ROOT_DIR / "raw_data" / "markdown"
IMAGES_DIR = ROOT_DIR / "raw_data" / "images"
OUTPUT_DIR = ROOT_DIR / "output"
QA_PER_MEETING_DIR = OUTPUT_DIR / "qa_per_meeting"

# ── Notion ────────────────────────────────────────────
NOTION_TOKEN = os.getenv("NOTION_TOKEN", "")
NOTION_PARENT_PAGE_ID = os.getenv("NOTION_PARENT_PAGE_ID", "")
NOTION_API_VERSION = "2022-06-28"
NOTION_BASE_URL = "https://api.notion.com/v1"

# ── OpenAI ────────────────────────────────────────────
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
OPENAI_EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")

# ── 處理參數 ──────────────────────────────────────────
# 單次 API 呼叫的最大 token 限制（避免太長的會議紀錄超限）
MAX_TOKENS_PER_CHUNK = 6000
# Q&A 相似度閾值（cosine similarity 超過此值視為重複）
SIMILARITY_THRESHOLD = 0.88
# 批次處理的並行數
BATCH_CONCURRENCY = 5
