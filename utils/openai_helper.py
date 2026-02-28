"""
OpenAI API 封裝
- Q&A 萃取
- Embedding 計算
- 去重合併
- 分類標籤
"""
from __future__ import annotations

import functools
import json

from openai import OpenAI

import config
from utils.observability import observe


@functools.lru_cache(maxsize=1)
def _client() -> OpenAI:
    return OpenAI(api_key=config.OPENAI_API_KEY)


# ──────────────────────────────────────────────────────
# Q&A 萃取
# ──────────────────────────────────────────────────────

EXTRACT_SYSTEM_PROMPT = """\
你同時扮演三個角色來完成 SEO 知識萃取任務：

**知識本體設計師**：你理解 SEO 領域的概念樹。每個 Q&A 必須能獨立放進知識庫，\
讀者不需要看過原始會議就能理解問題與答案。

**SEO 實踐審計員**：你熟悉真實網站的運營挑戰。在判斷「可執行性」時，評估建議是否有\
實際工具配套（GSC、GA4 等），以及步驟是否可在真實環境落地。

**品質評估官**：你用「完整性 + 可執行性 + 可驗證性」來衡量每個 A 的品質，\
並根據資訊來源的確定程度給出 confidence。

你的任務是從 SEO 顧問會議紀錄中萃取有價值的知識點，整理成問答 (Q&A) 格式。

## 規則

1. 每個 Q 必須是一個**自包含**（self-contained）的 SEO 問題 — 讀者不需要看過原始會議紀錄就能理解問題在問什麼
2. 每個 A 應該是根據會議內容整理的完整回答，包含**具體建議、原因說明和行動方向**
3. 如果會議中提到具體的工具、數據或案例，請在 A 中保留
4. 如果某個知識點有時效性（例如某個演算法更新），請在 A 中標註「（時效性：YYYY-MM）」
5. **不要萃取**：純行政內容、日程安排、閒聊、模糊到無法形成知識點的對話
6. 如果會議紀錄中包含圖片描述或截圖說明，請在相關的 A 中提及
7. 萃取的粒度要適中：一個 Q&A 聚焦在一個主題，但不要拆得太細
8. 如果會議中某議題只是初步討論、結論為「待確認」「需要再觀察」「下次再看」，\
仍可萃取為 Q&A，但 A 中須明確標註「（待確認）」或「（持續觀察中）」，\
且 confidence 應設為 0.5 以下
9. 如果某個 Q&A 的回答來自顧問的明確建議（有具體做法），confidence 應 ≥ 0.8；\
若只是與會者的猜測或推論，confidence 應在 0.5–0.7 之間
10. keywords 限 3–7 個，必須是 SEO 領域術語或具體名詞（如 canonical、Discover、CTR），\
避免通用詞（如「方法」「建議」「討論」）

## Answer 完整度要求

每個 A 應盡可能包含以下四個層次（What / Why / How / Evidence）：

- **What**：直接說明建議或結論是什麼
- **Why**：解釋原因或背後的機制（Google 演算法邏輯、SEO 影響路徑）
- **How**：給出具體可執行的做法、步驟或工具
- **Evidence**：提供數據、工具位置、案例或可驗證的來源（如 GSC 路徑）

**Completeness 評分對比示範：**

3 分（不完整）：
A: canonical 應該指向乾淨的 URL 版本。

5 分（完整）：
A: [What] canonical 應統一指向不帶 query string 的乾淨 URL。[Why] Google 爬蟲有時會自行選擇錯誤的 canonical，浪費爬蟲預算、影響索引準確性。[How] 在所有帶參數頁面的 <head> 加入 `<link rel="canonical" href="https://example.com/page">`，指向標準版本。[Evidence] 可在 GSC「索引 > 頁面」查看「系統選擇的 canonical」欄位，確認是否符合預期。

如果原始會議提供的資訊不足以填寫某個層次，請只保留有據可查的內容，不要虛構。

## 防止幻覺（嚴格遵守）

1. **僅從會議文本提取**：不要用你的通用 SEO 知識補充會議未提及的細節。
   - ❌ 會議只說「title tag 有問題」，你卻加上「通常 50–60 字最佳」→ 這是虛構
   - ✅ 只寫會議實際討論的內容，不確定的部分標註「（具體做法未提及）」

2. **工具路徑要具體或標註**：
   - ❌「在 GA4 查看」→ 太模糊
   - ✅「在 GSC『索引 > 頁面』查看」→ 具體路徑
   - ✅「在 GA4 追蹤」加上「（具體路徑未提及）」→ 誠實標註

3. **不要虛構數字**：
   - ❌ 會議說「流量下降」，你寫「下降約 20%」→ 數字是捏造的
   - ✅ 保留原文「流量下降」，或「（具體幅度未提及）」

## 補充標準知識（How 為空時可用）

當 How 層無法從會議文本填寫時，允許補充「通用 SEO 標準做法」，但嚴格要求：
1. 在補充內容前加 `[補充]` 標記，與 [How] 同一段落
2. `[補充]` 內容必須是「任何 SEO 從業者都知道的通用排查/操作步驟」
3. **禁止**：把「此次會議的特定情況」套用到通用做法
4. **禁止**：在 [補充] 中寫入任何數字或會議未提及的具體結果
5. 僅在 How 完全空白或只有「（具體做法未提及）」時才使用 [補充]

## 範例

以下範例說明期望的萃取品質：

### 範例 1：顧問明確建議（confidence 高，完整 Answer）
會議片段：「顧問建議把 canonical 都指向沒有 query string 的版本，因為 Google 有時候會自己選錯 canonical。」
→ 正確萃取：
Q: 網站有多個帶 query string 的 URL 版本時，canonical 應該如何設定？
A: [What] 顧問建議將 canonical 統一指向不帶 query string 的乾淨 URL 版本。[Why] Google 有時會自行選擇錯誤的 canonical，導致爬蟲資源浪費和索引混亂。[How] 在所有帶參數的頁面 <head> 加上 `<link rel="canonical" href="https://example.com/page">` 指向乾淨版本。[Evidence] 可在 GSC「索引 > 頁面 > 系統選擇的 canonical」欄位驗證設定是否生效。
confidence: 0.9

### 範例 2：觀察中議題（confidence 低）
會議片段：「最近 Discover 流量掉很多，不確定是不是演算法改了，下次再看看。」
→ 正確萃取：
Q: Google Discover 流量突然大幅下降，可能的原因是什麼？
A: 會議中觀察到 Discover 流量近期顯著下降，但尚無法確認具體原因，推測可能與 Google 演算法調整有關。（持續觀察中）
confidence: 0.4

### 範例 3：部分資訊但不完整（confidence 中等）
會議片段：「我們最近在試驗新的 title tag 結構，目前流量沒有明顯變化，Google 的 snippet 有時顯示不太對。」
→ 正確萃取：
Q: 修改 title tag 結構後，如何確認是否真的對 SEO 有效？
A: [What] 改變 title tag 結構需要 3–4 週觀察期，不能依賴短期流量判斷。[Why] Google 不一定完全採用 title tag 生成 snippet，有時會抽取頁面其他內容；snippet 呈現變化比流量更早反映改動效果。[How] 持續監控：(1) GSC「搜尋結果」觀察 CTR 變化；(2) 直接在 SERP 搜尋目標關鍵字，確認 snippet 是否按新 title 顯示。[Evidence] （具體實驗結果與數據未提及，持續觀察中）
confidence: 0.65

### 範例 4：運營型診斷問題（[補充] 標記正確使用）
會議片段：「robots.txt 在 12/21 有改過，把太多圖片 URL 開放給爬蟲了，已修復但還在觀察。」
→ 正確萃取：
Q: robots.txt 設定過度開放導致大量圖片 URL 被爬取後，應如何診斷修復效果？
A: [What] 會議記錄 robots.txt 已於 12/21 修正，修正前設定過度開放，導致爬蟲抓取大量圖片/resize URL。[Why] 過度開放的 robots.txt 讓 Google 抓取大量低品質/重複頁面，推高 GSC「已檢索未索引」數量，浪費爬蟲預算。[How] （會議未提及具體修正規則內容）[補充] 標準驗證步驟：(1) 在 GSC「設定 > robots.txt」工具確認新規則是否生效；(2) 觀察 GSC「索引 > 頁面」中「已檢索未索引」趨勢，預期 1–2 週後回落；(3) 若分開設定 Googlebot-Image，需確認圖片 URL 規則無衝突。[Evidence] 會議記錄顯示修正日期 12/21，可在 GSC Coverage 報表觀察後續趨勢。
confidence: 0.7

### 不應萃取的例子
- 「下次會議改到星期五」→ ❌ 行政事務
- 「這個我回去看看」→ ❌ 無具體知識點
- 「嗯嗯，好」→ ❌ 對話語助詞

## 輸出格式（嚴格遵守 JSON）

{
  "qa_pairs": [
    {
      "question": "問題文字（自包含、可獨立理解）",
      "answer": "回答文字（包含具體建議和原因）",
      "keywords": ["SEO術語1", "SEO術語2"],
      "confidence": 0.9
    }
  ],
  "meeting_summary": "一句話概述這次會議的主要內容"
}

## confidence 評分標準
- 0.85–1.0：顧問明確給出的建議或結論，有具體做法
- 0.7–0.85：會議有討論且有初步共識，但未必是顧問直接建議
- 0.5–0.7：與會者的推測、假設，或僅有部分線索
- 0.3–0.5：待確認事項、尚在觀察中、無明確結論

請用繁體中文輸出。
"""


@observe(name="extract_qa_from_text")
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
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "extract_qa",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "qa_pairs": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "question": {
                                        "type": "string",
                                        "description": "SEO 問題，自包含可獨立理解，20–150 字",
                                    },
                                    "answer": {
                                        "type": "string",
                                        "description": "包含 What/Why/How/Evidence 的完整回答，至少 100 字",
                                    },
                                    "keywords": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                        "description": "3–7 個 SEO 術語或具體名詞，避免「方法」「建議」等通用詞",
                                    },
                                    "confidence": {
                                        "type": "number",
                                        "description": "0.0–1.0 的置信度：顧問明確建議≥0.8，推測≤0.7，待確認≤0.5",
                                    },
                                },
                                "required": ["question", "answer", "keywords", "confidence"],
                                "additionalProperties": False,
                            },
                        },
                        "meeting_summary": {"type": "string"},
                    },
                    "required": ["qa_pairs", "meeting_summary"],
                    "additionalProperties": False,
                },
            },
        },
        max_completion_tokens=16000,  # gpt-5 推理模型：reasoning token 佔用大，需預留足夠空間
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

@observe(name="get_embeddings")
def get_embeddings(texts: list[str]) -> list[list[float]]:
    """
    對一批文字計算 embedding。
    自動處理空字串和批次限制。
    每個文字獨立 cache（content-addressed），無變內容不重打 API。
    """
    from utils.pipeline_cache import cache_get, cache_set

    client = _client()

    # 過濾空字串，記住原始位置
    valid_indices = [i for i, t in enumerate(texts) if t.strip()]
    valid_texts = [texts[i] for i in valid_indices]

    if not valid_texts:
        return [[0.0] * 1536 for _ in range(len(texts))]

    # ── Cache check per-text ──────────────────────────────
    cached_map: dict[int, list[float]] = {}
    miss_indices: list[int] = []
    miss_texts: list[str] = []

    for idx, text in zip(valid_indices, valid_texts):
        hit = cache_get("embedding", text)
        if hit is not None:
            cached_map[idx] = hit
        else:
            miss_indices.append(idx)
            miss_texts.append(text)

    if cached_map:
        print(f"   📦 embedding cache: {len(cached_map)}/{len(valid_texts)} hits")

    # ── API 呼叫（僅補 miss）────────────────────────────
    all_miss_embeddings: list[list[float]] = []
    batch_size = 500

    if miss_texts:
        for start in range(0, len(miss_texts), batch_size):
            batch = miss_texts[start : start + batch_size]
            response = client.embeddings.create(
                model=config.OPENAI_EMBEDDING_MODEL,
                input=batch,
            )
            for item in response.data:
                all_miss_embeddings.append(item.embedding)

        # 寫入 cache
        for text, emb in zip(miss_texts, all_miss_embeddings):
            cache_set("embedding", text, emb)

    # ── 重建完整結果陣列 ───────────────────────────────
    miss_map = dict(zip(miss_indices, all_miss_embeddings))
    dim = (
        len(next(iter(cached_map.values())))
        if cached_map
        else (len(all_miss_embeddings[0]) if all_miss_embeddings else 1536)
    )
    result = [[0.0] * dim for _ in range(len(texts))]
    for idx in valid_indices:
        result[idx] = cached_map.get(idx) or miss_map.get(idx) or [0.0] * dim

    return result


# ──────────────────────────────────────────────────────
# 合併重複 Q&A
# ──────────────────────────────────────────────────────

MERGE_SYSTEM_PROMPT = """\
你是 SEO 專家。以下是幾組語意相似的 Q&A，它們來自不同時間的會議紀錄。
請合併成 **一組** 更完整、更精確的 Q&A。

合併規則：
1. 問題(Q)用最清晰的方式重新表述，必須自包含（讀者不需要知道原始會議背景）
2. 回答(A)整合所有版本的資訊，保留最新、最完整的建議
3. 如果不同版本有矛盾，以較新日期的為準，並註明「此建議可能隨時間演變」
4. 保留具體的數據、工具名稱、案例
5. 如果某版本有時效性標註，合併後也要保留
6. keywords 限 3–7 個 SEO 術語，避免通用詞

用繁體中文。

輸出 JSON：
{
  "question": "合併後的問題",
  "answer": "合併後的回答",
  "keywords": ["SEO術語1", "SEO術語2"],
  "source_dates": ["2024-01-15", "2024-03-20"]
}
"""


@observe(name="merge_similar_qas")
def merge_similar_qas(qa_group: list[dict]) -> dict:
    """
    合併一組相似的 Q&A 成一個。
    qa_group: [{question, answer, source_title, source_date, ...}, ...]
    """
    from utils.pipeline_cache import cache_get, cache_set

    client = _client()

    # ── Cache key: sorted (question, answer) pairs ─────────────────
    # 排序以保證相同組合不同順序仍命中 cache
    import json as _json
    group_key = _json.dumps(
        sorted(
            [{"q": qa["question"], "a": qa["answer"]} for qa in qa_group],
            key=lambda x: x["q"],
        ),
        ensure_ascii=False,
        sort_keys=True,
    )
    cached = cache_get("merge", group_key)
    if cached is not None:
        # Re-attach merged_from（包含 source 資訊，不放入 cache）
        cached["merged_from"] = [
            {
                "source_title": qa.get("source_title", ""),
                "source_date": qa.get("source_date", ""),
                "source_file": qa.get("source_file", ""),
                "stable_id": qa.get("stable_id", ""),
            }
            for qa in qa_group
        ]
        return cached

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
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "merge_qa",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "question": {"type": "string"},
                        "answer": {"type": "string"},
                        "keywords": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "source_dates": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    },
                    "required": ["question", "answer", "keywords", "source_dates"],
                    "additionalProperties": False,
                },
            },
        },
        max_completion_tokens=8192,  # gpt-5 推理模型：需額外空間給 reasoning
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
            "source_file": qa.get("source_file", ""),
            "stable_id": qa.get("stable_id", ""),
        }
        for qa in qa_group
    ]

    # ── 寫入 cache（不含 merged_from，保持 content-addressable）──
    cache_payload = {
        "question": result["question"],
        "answer": result["answer"],
        "keywords": result["keywords"],
        "source_dates": result["source_dates"],
    }
    cache_set("merge", group_key, cache_payload)

    return result


CLASSIFY_SYSTEM_PROMPT = """\
你是 SEO 專家。請為以下 Q&A 加上分類標籤。

分類維度：

1. **category**（主分類，選一個）：
   - 索引與檢索（Coverage、索引狀態、robots.txt、sitemap、canonical、未索引、重複內容）
   - 連結策略（內部連結、外部連結、Disavow、連結架構、錨文字、反向連結）
   - 搜尋表現分析（曝光、點擊、CTR、排名變化、SERP 外觀、位置平均）
   - 內容策略（關鍵字佈局、主題聚合、延伸閱讀、內容經營、E-E-A-T、Meta 標籤）
   - Discover與AMP（Google Discover、AMP Article、推薦流量、焦點新聞 Top Stories）
   - 技術SEO（速度、Core Web Vitals、結構化資料、URL 結構、重複頁面、HTTPS、hreflang）
   - GA與數據追蹤（GA4、事件追蹤、歸因分析、PWA 追蹤、Search Console 數據解讀）
   - 平台策略（Vocus 產品面 SEO，如自訂網域、方案頁、SEO 功能設定、站內搜尋）
   - 演算法與趨勢（Google 演算法更新、Helpful Content、SERP 變化、AI 搜尋趨勢、SGE）
   - 其他（以上皆不適用時才選）

2. **difficulty**（難度）：
   - 基礎：概念明確、操作直觀，SEO 新手也能理解和執行
   - 進階：需要較深技術知識或跨系統整合，適合有一定 SEO 經驗者

3. **evergreen**（時效性）：
   - true = 常青知識，演算法或平台更新後仍大致適用
   - false = 可能隨演算法/平台版本更新而過時（如特定演算法名稱、具體數字閾值）

## 分類示範（few-shot examples）

### 索引與檢索
Q: robots.txt 設定過度開放導致圖片 URL 被大量爬取，應如何診斷？
A: 修正 robots.txt 規則後，到 GSC「設定 > robots.txt」確認規則生效，並觀察「已檢索未索引」趨勢。
→ category: 索引與檢索, difficulty: 進階, evergreen: true

Q: canonical 指向帶 query string 的 URL 會有什麼問題？
A: Google 可能忽略錯誤的 canonical，自行選擇標準版，導致爬蟲預算浪費和索引不準確。
→ category: 索引與檢索, difficulty: 基礎, evergreen: true

### 連結策略
Q: 內部連結的錨文字應該怎麼設定才對 SEO 有益？
A: 錨文字應包含目標頁面的主要關鍵字，避免「點這裡」等非描述性文字，但不要堆砌。
→ category: 連結策略, difficulty: 基礎, evergreen: true

Q: 如何評估一批外部連結是否需要 Disavow？
A: 觀察連結的 spam score、相關性和 anchor text，若疑似負面 SEO 且無法聯繫移除再考慮 Disavow。
→ category: 連結策略, difficulty: 進階, evergreen: true

### 搜尋表現分析
Q: Search Console 的 CTR 持續下降但曝光不變，通常代表什麼問題？
A: 可能是 title/meta description 不夠吸引人，或 SERP 出現更多競爭者佔據版位，需優化片段外觀。
→ category: 搜尋表現分析, difficulty: 基礎, evergreen: true

Q: 位置平均上升但點擊下降，這個背離現象該怎麼解讀？
A: 排名上升可能是長尾關鍵字佔比增加（搜尋量低），或 Rich Result 讓使用者直接在 SERP 得到答案。
→ category: 搜尋表現分析, difficulty: 進階, evergreen: true

### 內容策略
Q: 主題聚合（Topic Cluster）策略中，支柱頁和群集頁應如何分工？
A: 支柱頁覆蓋主題的廣度，群集頁深化特定子主題，內部連結雙向連接，讓 Google 理解主題權威性。
→ category: 內容策略, difficulty: 進階, evergreen: true

Q: Meta title 超過 60 字會被截斷，這對 SEO 有影響嗎？
A: 超過閾值的 title 在 SERP 中顯示「...」，影響點擊率，但不直接影響排名；建議控制在 50–60 字。
→ category: 內容策略, difficulty: 基礎, evergreen: false

### Discover與AMP
Q: Google Discover 流量突然下降，最可能的原因是什麼？
A: Discover 流量波動大，常見原因包括：封面圖片品質不佳、內容與使用者興趣匹配度低、近期演算法調整。
→ category: Discover與AMP, difficulty: 進階, evergreen: true

Q: AMP Article 索引數下降對 Google News 流量有什麼影響？
A: AMP Article 是進入 Google News Top Stories 的主要路徑；索引數下降會直接砍掉焦點新聞版位流量。
→ category: Discover與AMP, difficulty: 進階, evergreen: true

### 技術SEO
Q: Core Web Vitals 的 LCP 太高，主要的改善方向有哪些？
A: 常見是圖片過大或伺服器回應慢；可用 lazy loading、CDN、WebP 格式、預載入 LCP 圖片改善。
→ category: 技術SEO, difficulty: 進階, evergreen: true

Q: 結構化資料（VideoObject）消失會對 Video Appearance 有什麼影響？
A: Video Appearance 完全依賴正確實作的 VideoObject；消失後影片SERP外觀消失，流量可能大幅下滑。
→ category: 技術SEO, difficulty: 進階, evergreen: true

### GA與數據追蹤
Q: GA4 的 Organic Search 工作階段包含哪些流量來源？
A: 包含 Google、Bing 等搜尋引擎的直接點擊；但 Discover 和 Google News 的流量歸屬在 GA4 中是「Organic Social」或「Unassigned」。
→ category: GA與數據追蹤, difficulty: 進階, evergreen: false

Q: 如何在 GA4 中追蹤 AMP 頁面的工作階段？
A: AMP 頁面需透過 AMP Client ID API 和 gtag 正確串接，否則 AMP 來源流量會斷鏈成新的工作階段。
→ category: GA與數據追蹤, difficulty: 進階, evergreen: true

### 平台策略
Q: Vocus 自訂網域設定後，原有的 vocus.cc 網址 SEO 權重如何轉移？
A: 需要設定 301 永久重新導向，讓 Google 把舊 URL 的權重轉移到自訂網域；Search Console 也要重新驗證。
→ category: 平台策略, difficulty: 進階, evergreen: true

### 演算法與趨勢
Q: Google 2024 年 3 月核心更新主要針對什麼內容？
A: 主要打擊低品質、AI 批量生成的內容，強調 E-E-A-T；排名下降的網站應檢查內容原創性和作者專業度。
→ category: 演算法與趨勢, difficulty: 進階, evergreen: false

Q: Google SGE（AI 概覽）對傳統 SEO 流量有什麼影響？
A: SGE 可能讓使用者在 SERP 即得到答案而不點擊，資訊型關鍵字 CTR 預期下降，品牌型和交易型關鍵字影響較小。
→ category: 演算法與趨勢, difficulty: 進階, evergreen: false

用繁體中文。
"""


@observe(name="classify_qa")
def classify_qa(question: str, answer: str) -> dict:
    """對單個 Q&A 進行分類（列入 content-addressed cache）"""
    from utils.pipeline_cache import cache_get, cache_set

    # ── cache check ───────────────────────────────────────
    cache_key = f"{question}\n\n{answer}"
    cached = cache_get("classify", cache_key)
    if cached is not None:
        return cached

    client = _client()

    response = client.chat.completions.create(
        model=config.CLASSIFY_MODEL,  # 分類用小模型省成本，預設 gpt-5-mini，可透過 CLASSIFY_MODEL env 覆蓋
        messages=[
            {"role": "system", "content": CLASSIFY_SYSTEM_PROMPT},
            {"role": "user", "content": f"Q: {question}\n\nA: {answer}"},
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "classify_qa",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "category": {
                            "type": "string",
                            "enum": [
                                "索引與檢索", "連結策略", "搜尋表現分析",
                                "內容策略", "Discover與AMP", "技術SEO",
                                "GA與數據追蹤", "平台策略", "演算法與趨勢", "其他",
                            ],
                        },
                        "difficulty": {
                            "type": "string",
                            "enum": ["基礎", "進階"],
                        },
                        "evergreen": {"type": "boolean"},
                    },
                    "required": ["category", "difficulty", "evergreen"],
                    "additionalProperties": False,
                },
            },
        },
        max_completion_tokens=2048,  # gpt-5-mini 推理模型需要足夠空間給 reasoning + JSON output
    )

    content = response.choices[0].message.content or "{}"
    try:
        result = json.loads(content)
    except json.JSONDecodeError:
        result = {"category": "其他", "difficulty": "基礎", "evergreen": True}

    # ── 寫入 cache ───────────────────────────────────────
    cache_set("classify", cache_key, result)
    return result
