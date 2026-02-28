"""
專案設定 — 從 .env 讀取，或使用預設值

環境變數採用 Lazy Loading（PEP 562 module-level __getattr__）：
- 路徑與常數在 import 時直接可用（無側效應）
- NOTION_TOKEN、OPENAI_API_KEY 等敏感 env var 在首次存取時才驗證
- 讓 Step 1（只需 NOTION_TOKEN）不會因為缺少 OPENAI_API_KEY 而失敗
"""
import math
import os
from pathlib import Path
from typing import Dict, Optional
from dotenv import load_dotenv

load_dotenv()

# ── 路徑（無副作用，直接定義）─────────────────────────
ROOT_DIR = Path(__file__).resolve().parent
RAW_JSON_DIR = ROOT_DIR / "raw_data" / "notion_json"
RAW_MD_DIR = ROOT_DIR / "raw_data" / "markdown"
IMAGES_DIR = ROOT_DIR / "raw_data" / "images"
OUTPUT_DIR = ROOT_DIR / "output"
QA_PER_MEETING_DIR = OUTPUT_DIR / "qa_per_meeting"

# ── 常數（不依賴 env，無副作用）──────────────────────
NOTION_API_VERSION = "2022-06-28"
NOTION_BASE_URL = "https://api.notion.com/v1"

# ── 處理參數 ──────────────────────────────────────────
# 單次 API 呼叫的最大 token 限制（避免太長的會議紀錄超限）
MAX_TOKENS_PER_CHUNK = 6000
# Q&A 相似度閾值（cosine similarity 超過此值視為重複）
SIMILARITY_THRESHOLD = 0.88

# ── Hybrid Search 語意 / 關鍵字比重 ──────────────────
# final_score = SEMANTIC_WEIGHT * cosine_sim + keyword_boost
# keyword_boost 上限由 KW_BOOST * KW_BOOST_MAX_HITS 決定（最多 0.30）
SEMANTIC_WEIGHT: float = 0.7
KEYWORD_WEIGHT: float = 0.3


# ── Env 工具函式 ──────────────────────────────────────


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


# ── Hybrid Search Keyword Boost（數值型 env，有預設值，import 時安全）─
KW_BOOST = _get_float_env("KW_BOOST", "0.10")
KW_BOOST_PARTIAL = _get_float_env("KW_BOOST_PARTIAL", "0.05")
KW_BOOST_MAX_HITS = _get_int_env("KW_BOOST_MAX_HITS", "3")


# ── Lazy Env Vars（首次存取時才驗證）──────────────────
# 使用 PEP 562 module-level __getattr__ 實現延遲載入
# 好處：import config 時不會因為缺少某些 env var 而 crash


class _LazyEnv:
    """Descriptor：首次存取 env var 時才做 require 檢查"""

    __slots__ = ("_key", "_default", "_value", "_resolved")

    def __init__(self, key: str, default: Optional[str] = None):
        self._key = key
        self._default = default
        self._value: Optional[str] = None
        self._resolved = False

    def resolve(self) -> str:
        if not self._resolved:
            raw = os.getenv(self._key, self._default)
            if self._default is None and (not raw or not raw.strip()):
                raise ValueError(
                    f"必需環境變數 {self._key!r} 未設定。"
                    f"請在 .env 檔案或環境中設定後再執行。"
                )
            self._value = raw.strip() if raw else ""
            self._resolved = True
        return self._value  # type: ignore[return-value]


# 註冊所有 lazy env vars
_LAZY_ATTRS: Dict[str, _LazyEnv] = {
    "NOTION_TOKEN": _LazyEnv("NOTION_TOKEN"),
    "NOTION_PARENT_PAGE_ID": _LazyEnv("NOTION_PARENT_PAGE_ID", default=""),
    "OPENAI_API_KEY": _LazyEnv("OPENAI_API_KEY"),
    "OPENAI_MODEL": _LazyEnv("OPENAI_MODEL", default="gpt-5.2"),
    "OPENAI_EMBEDDING_MODEL": _LazyEnv(
        "OPENAI_EMBEDDING_MODEL", default="text-embedding-3-small"
    ),
    "CLASSIFY_MODEL": _LazyEnv("CLASSIFY_MODEL", default="gpt-5-mini"),
    "EVAL_JUDGE_MODEL": _LazyEnv("EVAL_JUDGE_MODEL", default="gpt-5-mini"),
    "EVAL_RERANK_MODEL": _LazyEnv("EVAL_RERANK_MODEL", default="gpt-5-nano"),
    "SHEETS_URL": _LazyEnv("SHEETS_URL", default=""),
}


def __getattr__(name: str) -> str:
    """Module-level __getattr__ (PEP 562) — lazy env var 存取"""
    if name in _LAZY_ATTRS:
        return _LAZY_ATTRS[name].resolve()
    raise AttributeError(f"module 'config' has no attribute {name!r}")


def __dir__() -> list:
    """Module-level __dir__ (PEP 562) — 讓 dir(config) 可看到 lazy attrs"""
    base = list(globals().keys())
    base.extend(_LAZY_ATTRS.keys())
    return base
