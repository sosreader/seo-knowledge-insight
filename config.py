"""
專案設定 — 從 .env 讀取，或使用預設值
"""
import math
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


def _require_env(key: str) -> str:
    """取得必需環境變數；未設定或空白時立即拋出例外（fail-fast）。"""
    value = os.getenv(key)
    if not value or not value.strip():
        raise ValueError(
            f"必需環境變數 {key!r} 未設定。請在 .env 檔案或環境中設定後再執行。"
        )
    return value.strip()


def _get_float_env(key: str, default: str) -> float:
    """取得數值型環境變數；格式錯誤或非有限正數時拋出有意義的例外。"""
    raw = os.getenv(key, default)
    try:
        result = float(raw)
    except ValueError:
        raise ValueError(f"環境變數 {key!r} 必須是數字，目前值：{raw!r}")
    if not math.isfinite(result) or result < 0:
        raise ValueError(f"環境變數 {key!r} 必須是非負有限數字，目前值：{raw!r}")
    return result


def _get_int_env(key: str, default: str, min_value: int = 1) -> int:
    """取得整數型環境變數；格式錯誤或低於最小值時拋出有意義的例外。"""
    raw = os.getenv(key, default)
    try:
        result = int(raw)
    except ValueError:
        raise ValueError(f"環境變數 {key!r} 必須是整數，目前值：{raw!r}")
    if result < min_value:
        raise ValueError(f"環境變數 {key!r} 必須 >= {min_value}，目前值：{raw!r}")
    return result


# ── Notion ────────────────────────────────────────────
NOTION_TOKEN = _require_env("NOTION_TOKEN")
NOTION_PARENT_PAGE_ID = os.getenv("NOTION_PARENT_PAGE_ID", "")
NOTION_API_VERSION = "2022-06-28"
NOTION_BASE_URL = "https://api.notion.com/v1"

# ── OpenAI ────────────────────────────────────────────
OPENAI_API_KEY = _require_env("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.2")
OPENAI_EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")

# ── Google Sheets ─────────────────────────────────────
# 步驟 4 週報：試算表 URL（可省略 gid，程式會依 tab 名稱自動解析）
SHEETS_URL = os.getenv("SHEETS_URL", "")

# ── 處理參數 ──────────────────────────────────────────
# 單次 API 呼叫的最大 token 限制（避免太長的會議紀錄超限）
MAX_TOKENS_PER_CHUNK = 6000
# Q&A 相似度閾值（cosine similarity 超過此值視為重複）
SIMILARITY_THRESHOLD = 0.88

# ── Hybrid Search Keyword Boost ────────────────────────
# 每個完整命中的 boost 分數（雙向匹配）
KW_BOOST = _get_float_env("KW_BOOST", "0.10")
# 中文 bigram 弱命中的 boost 分數
KW_BOOST_PARTIAL = _get_float_env("KW_BOOST_PARTIAL", "0.05")
# 最多計入幾個 keyword 命中（避免 boost 過大）
KW_BOOST_MAX_HITS = _get_int_env("KW_BOOST_MAX_HITS", "3")
