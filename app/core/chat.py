"""
RAG chat — embedding 查詢 + GPT 對話
"""
from __future__ import annotations

import logging

import numpy as np
from openai import AsyncOpenAI

from app import config
from app.core.store import QAItem, store

logger = logging.getLogger(__name__)

_client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)

# ─────────────────────────── embedding ────────────────────────────


async def get_embedding(text: str) -> np.ndarray:
    """回傳 L2 歸一化的 embedding ndarray (float32)"""
    resp = await _client.embeddings.create(
        model=config.OPENAI_EMBEDDING_MODEL,
        input=text.strip(),
    )
    vec = np.array(resp.data[0].embedding, dtype=np.float32)
    norm = np.linalg.norm(vec)
    return vec / norm if norm > 0 else vec


# ─────────────────────────── RAG chat ─────────────────────────────

_SYSTEM_PROMPT = """\
你是一位資深 SEO 顧問，根據以下 SEO 知識庫內容回答用戶的問題。
回答時請：
1. 直接針對問題給出具體建議，不要含糊其辭
2. 引用知識庫中的案例或數字來支撐建議
3. 若知識庫沒有相關資訊，誠實說明並提供通用建議
4. 回答使用繁體中文，技術術語可以保留英文
"""


def _format_context(hits: list[tuple[QAItem, float]]) -> str:
    parts: list[str] = []
    for idx, (item, score) in enumerate(hits, 1):
        parts.append(
            f"[{idx}] Q: {item.question}\n"
            f"    A: {item.answer}\n"
            f"    (來源: {item.source_title or item.source_date}, 相似度: {score:.2f})"
        )
    return "\n\n".join(parts)


def _item_to_source(item: QAItem, score: float) -> dict:
    return {
        "id": item.id,
        "question": item.question,
        "category": item.category,
        "source_title": item.source_title,
        "source_date": item.source_date,
        "score": round(score, 4),
    }


async def rag_chat(
    message: str,
    history: list[dict] | None = None,
) -> dict:
    """
    執行 RAG 問答。

    Args:
        message: 用戶問題
        history: OpenAI messages 格式的歷史對話，
                 e.g. [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]

    Returns:
        {"answer": str, "sources": list[dict]}
    """
    # 1. embed 用戶問題
    query_vec = await get_embedding(message)

    # 2. 語意搜尋
    hits = store.search(query_vec, top_k=config.CHAT_CONTEXT_K)

    # 3. 組 context
    context = _format_context(hits)

    # 4. 組 messages
    messages: list[dict] = [{"role": "system", "content": _SYSTEM_PROMPT}]

    if context:
        messages.append(
            {
                "role": "system",
                "content": f"--- 相關 SEO 知識庫 ---\n{context}\n--- 知識庫結束 ---",
            }
        )

    if history:
        messages.extend(history)

    messages.append({"role": "user", "content": message})

    # 5. 呼叫 GPT
    resp = await _client.chat.completions.create(
        model=config.OPENAI_MODEL,
        messages=messages,
        temperature=0.3,
    )

    answer = resp.choices[0].message.content or ""
    sources = [_item_to_source(item, score) for item, score in hits]

    logger.debug("rag_chat: %d sources used, answer length=%d", len(sources), len(answer))
    return {"answer": answer, "sources": sources}
