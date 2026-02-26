"""
OpenAI API 封裝
- Q&A 萃取
- Embedding 計算
- 去重合併
- 分類標籤
"""
from __future__ import annotations

import json
from typing import Any

import functools

from openai import OpenAI

import config


@functools.lru_cache(maxsize=1)
def _client() -> OpenAI:
    return OpenAI(api_key=config.OPENAI_API_KEY)


# ──────────────────────────────────────────────────────
# Q&A 萃取
# ──────────────────────────────────────────────────────

EXTRACT_SYSTEM_PROMPT = """\
你是一位資深的 SEO 專家。你的任務是從 SEO 顧問會議紀錄中萃取有價值的知識點，\
整理成問答 (Q&A) 格式。

規則：
1. 每個 Q 應該是一個具體的、可獨立理解的 SEO 問題
2. 每個 A 應該是根據會議內容整理的完整回答，包含具體建議和原因
3. 如果會議中提到具體的工具、數據或案例，請在 A 中保留
4. 如果某個知識點有時效性（例如某個演算法更新），請在 A 中標註
5. 忽略純行政、日程安排等非 SEO 知識的內容
6. 如果會議紀錄中包含圖片描述或截圖說明，請在相關的 A 中提及
7. 萃取的粒度要適中：一個 Q&A 聚焦在一個主題，但不要拆得太細

請用繁體中文輸出。

輸出格式（嚴格遵守 JSON）：
{
  "qa_pairs": [
    {
      "question": "問題文字",
      "answer": "回答文字",
      "keywords": ["關鍵字1", "關鍵字2"],
      "confidence": 0.9
    }
  ],
  "meeting_summary": "一句話概述這次會議的主要內容"
}

confidence 是 0-1 之間的數字，表示你對這個 Q&A 品質的信心程度。\
如果是會議中明確討論的內容，信心應該較高；如果是你推測的，應該較低。
"""


def extract_qa_from_text(
    meeting_text: str,
    meeting_title: str = "",
    meeting_date: str = "",
) -> dict:
    """
    從單份會議紀錄文字中萃取 Q&A pairs。
    回傳 dict: {qa_pairs: [...], meeting_summary: str}
    """
    client = _client()

    user_msg = f"以下是一份 SEO 顧問會議紀錄"
    if meeting_title:
        user_msg += f"（標題：{meeting_title}）"
    if meeting_date:
        user_msg += f"（日期：{meeting_date}）"
    user_msg += f"：\n\n---\n\n{meeting_text}\n\n---\n\n請萃取 Q&A。"

    response = client.chat.completions.create(
        model=config.OPENAI_MODEL,
        messages=[
            {"role": "system", "content": EXTRACT_SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        response_format={"type": "json_object"},
        temperature=0.3,
        max_tokens=4096,
    )

    content = response.choices[0].message.content or "{}"
    try:
        result = json.loads(content)
    except json.JSONDecodeError:
        result = {"qa_pairs": [], "meeting_summary": "JSON 解析失敗"}

    return result


# ──────────────────────────────────────────────────────
# Embedding
# ──────────────────────────────────────────────────────

def get_embeddings(texts: list[str]) -> list[list[float]]:
    """
    對一批文字計算 embedding。
    自動處理空字串和批次限制。
    """
    client = _client()

    # 過濾空字串，記住原始位置
    valid_indices = [i for i, t in enumerate(texts) if t.strip()]
    valid_texts = [texts[i] for i in valid_indices]

    if not valid_texts:
        return [[0.0] * 1536] * len(texts)

    # OpenAI embedding API 一次最多 2048 條
    all_embeddings: list[list[float]] = []
    batch_size = 500

    for start in range(0, len(valid_texts), batch_size):
        batch = valid_texts[start : start + batch_size]
        response = client.embeddings.create(
            model=config.OPENAI_EMBEDDING_MODEL,
            input=batch,
        )
        for item in response.data:
            all_embeddings.append(item.embedding)

    # 重建完整陣列（空字串給零向量）
    dim = len(all_embeddings[0]) if all_embeddings else 1536
    result = [[0.0] * dim] * len(texts)
    for idx, emb in zip(valid_indices, all_embeddings):
        result[idx] = emb

    return result


# ──────────────────────────────────────────────────────
# 合併重複 Q&A
# ──────────────────────────────────────────────────────

MERGE_SYSTEM_PROMPT = """\
你是 SEO 專家。以下是幾組語意相似的 Q&A，它們來自不同時間的會議紀錄。
請合併成 **一組** 更完整、更精確的 Q&A。

合併規則：
1. 問題(Q)用最清晰的方式重新表述
2. 回答(A)整合所有版本的資訊，保留最新、最完整的建議
3. 如果不同版本有矛盾，以較新日期的為準，並註明「此建議可能隨時間演變」
4. 保留具體的數據、工具名稱、案例

用繁體中文。

輸出 JSON：
{
  "question": "合併後的問題",
  "answer": "合併後的回答",
  "keywords": ["關鍵字1", "關鍵字2"],
  "source_dates": ["2024-01-15", "2024-03-20"]
}
"""


def merge_similar_qas(qa_group: list[dict]) -> dict:
    """
    合併一組相似的 Q&A 成一個。
    qa_group: [{question, answer, source_title, source_date, ...}, ...]
    """
    client = _client()

    group_text = "\n\n".join(
        f"--- Q&A #{i+1} (來源: {qa.get('source_title', 'N/A')}, "
        f"日期: {qa.get('source_date', 'N/A')}) ---\n"
        f"Q: {qa['question']}\n"
        f"A: {qa['answer']}"
        for i, qa in enumerate(qa_group)
    )

    response = client.chat.completions.create(
        model=config.OPENAI_MODEL,
        messages=[
            {"role": "system", "content": MERGE_SYSTEM_PROMPT},
            {"role": "user", "content": group_text},
        ],
        response_format={"type": "json_object"},
        temperature=0.3,
        max_tokens=2048,
    )

    content = response.choices[0].message.content or "{}"
    try:
        result = json.loads(content)
    except json.JSONDecodeError:
        # fallback: 用第一筆
        result = {
            "question": qa_group[0]["question"],
            "answer": qa_group[0]["answer"],
            "keywords": qa_group[0].get("keywords", []),
            "source_dates": [q.get("source_date", "") for q in qa_group],
        }

    # 保留來源資訊
    result["merged_from"] = [
        {
            "source_title": qa.get("source_title", ""),
            "source_date": qa.get("source_date", ""),
        }
        for qa in qa_group
    ]
    return result


# ──────────────────────────────────────────────────────
# 分類標籤
# ──────────────────────────────────────────────────────

CLASSIFY_SYSTEM_PROMPT = """\
你是 SEO 專家。請為以下 Q&A 加上分類標籤。

分類維度：

1. **category**（主分類，選一個）：
   - 技術SEO
   - 內容策略
   - 連結建設
   - 關鍵字研究
   - 網站架構
   - Core Web Vitals
   - 本地SEO
   - 電商SEO
   - GA/GSC 數據分析
   - SEO 工具
   - 演算法更新
   - 其他

2. **difficulty**（難度）：基礎 / 進階

3. **evergreen**（時效性）：
   - true = 常青知識，不太會過時
   - false = 可能隨演算法/平台更新而過時

用繁體中文。輸出 JSON：
{
  "category": "分類",
  "difficulty": "基礎 或 進階",
  "evergreen": true/false
}
"""


def classify_qa(question: str, answer: str) -> dict:
    """對單個 Q&A 進行分類"""
    client = _client()

    response = client.chat.completions.create(
        model="gpt-5-nano",  # 分類是簡單結構化任務，用最小模型省成本
        messages=[
            {"role": "system", "content": CLASSIFY_SYSTEM_PROMPT},
            {"role": "user", "content": f"Q: {question}\n\nA: {answer}"},
        ],
        response_format={"type": "json_object"},
        temperature=0.1,
        max_tokens=256,
    )

    content = response.choices[0].message.content or "{}"
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return {"category": "其他", "difficulty": "基礎", "evergreen": True}
