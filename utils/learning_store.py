"""
learning_store — 搜尋失敗與使用者回饋的 JSONL 儲存

設計原則：
- 只追加（append-only）：每筆記錄不可修改
- 零副作用：寫入失敗靜默 warning，不拋出例外影響主流程
- 輕量查詢：以關鍵字 token 匹配，不需外部依賴

Event Schema:
  {
    "event":     "search_miss" | "feedback",
    "ts":        "2026-03-02T12:00:00Z",
    "query":     "查詢字串",
    "top_score": 0.15,         // 搜尋最高分
    "context":   "search" | "chat" | "report",
    "qa_id":     1,            // 僅 feedback event 有
    "feedback":  "helpful" | "not_relevant"  // 僅 feedback event 有
  }
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# 預設路徑（可被測試 monkeypatch 覆蓋）
try:
    import config as _root_config
    _OUTPUT_DIR = _root_config.OUTPUT_DIR
except (ImportError, AttributeError):
    _OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"

_LEARNINGS_PATH = _OUTPUT_DIR / "learnings.jsonl"


class LearningStore:
    """JSONL-based learning store，所有操作為 stateless（每次讀寫都從磁碟）。"""

    def _learnings_path(self) -> Path:
        """回傳當前設定的 JSONL 路徑（可被測試 monkeypatch 直接覆蓋 module-level 變數）。"""
        return _LEARNINGS_PATH

    def record_miss(self, query: str, top_score: float, context: str) -> None:
        """
        記錄搜尋失敗（無相關結果）到 JSONL。

        Args:
            query:     使用者查詢字串
            top_score: 搜尋最高分（< 閾值時才 record miss）
            context:   呼叫來源（"search" | "chat" | "report"）
        """
        record = {
            "event": "search_miss",
            "ts": _now_iso(),
            "query": query,
            "top_score": round(top_score, 4),
            "context": context,
        }
        self._append(record)
        logger.debug("learning_store: miss query=%r top_score=%.4f", query, top_score)

    def record_feedback(
        self,
        query: str,
        qa_id: int,
        feedback: str,
        top_score: Optional[float] = None,
    ) -> None:
        """
        記錄使用者回饋到 JSONL。

        Args:
            query:     原始查詢字串
            qa_id:     使用者回饋的 Q&A ID
            feedback:  "helpful" | "not_relevant"
            top_score: 該 Q&A 的搜尋分數（可選）
        """
        record: dict = {
            "event": "feedback",
            "ts": _now_iso(),
            "query": query,
            "qa_id": qa_id,
            "feedback": feedback,
        }
        if top_score is not None:
            record["top_score"] = round(top_score, 4)
        self._append(record)
        logger.debug("learning_store: feedback qa_id=%d feedback=%r", qa_id, feedback)

    def get_relevant_learnings(self, query: str) -> list[dict]:
        """
        以關鍵字 token 匹配，回傳相關的 learning 記錄。

        策略：query 的任一 token（長度 >= 2）出現在歷史 query 中即命中。
        回傳最近 10 筆（newest first）。

        Args:
            query: 當前查詢字串

        Returns:
            list of matching learning records（最多 10 筆）
        """
        all_records = self._load_all()
        if not all_records:
            return []

        query_tokens = {t for t in query.lower().split() if len(t) >= 2}
        if not query_tokens:
            return []

        matched = [
            r for r in all_records
            if any(t in r.get("query", "").lower() for t in query_tokens)
        ]
        return list(reversed(matched))[:10]

    def _load_all(self) -> list[dict]:
        """從 JSONL 讀取所有記錄，失敗時回傳空 list。"""
        path = self._learnings_path()
        if not path.exists():
            return []
        records: list[dict] = []
        try:
            for line in path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    logger.warning("learning_store: 無效 JSON 行，略過")
        except OSError as exc:
            logger.warning("learning_store: 讀取失敗 %s — %s", path, exc)
        return records

    def _append(self, record: dict) -> None:
        """追加一行 JSON 到 JSONL，失敗時靜默 warning。"""
        path = self._learnings_path()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except OSError as exc:
            logger.warning("learning_store: 寫入失敗 %s — %s", path, exc)


def _now_iso() -> str:
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"


# module-level singleton
learning_store = LearningStore()
