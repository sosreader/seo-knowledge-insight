"""
步驟 4：依據每週 SEO 指標 + Q&A 知識庫，產生分析報告

使用方式：
    # 直接串 Google Sheets URL（最簡）：
    python scripts/04_generate_report.py --input "https://docs.google.com/spreadsheets/d/..."

    # 指定分頁（預設取 vocus）：
    python scripts/04_generate_report.py --input "https://..." --tab vocus

    # 從本機檔案讀（手動從試算表複製存檔用）：
    python scripts/04_generate_report.py --input metrics.tsv

    # 輸出到指定路徑：
    python scripts/04_generate_report.py --input "https://..." --output report.md
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from datetime import datetime
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)

# ── 路徑修正 ─────────────────────────────────────────
try:
    import config
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    import config

from utils.openai_helper import get_embeddings
from utils.pipeline_deps import preflight_check, StepDependency
from utils.observability import init_laminar, flush_laminar, observe
from utils.search_engine import compute_keyword_boost

from openai import OpenAI

from utils.metrics_parser import (
    DEFAULT_SHEETS_URL,
    ALERT_THRESHOLD_MONTHLY,
    ALERT_THRESHOLD_WEEKLY,
    CORE_METRICS,
    SKIP_METRICS,
    METRIC_QUERY_MAP,
    fetch_from_sheets,
    parse_metrics_tsv,
    detect_anomalies,
)

# 注意：ALERT_THRESHOLD_MONTHLY / ALERT_THRESHOLD_WEEKLY / CORE_METRICS /
#       SKIP_METRICS / METRIC_QUERY_MAP / fetch_from_sheets / parse_metrics_tsv /
#       detect_anomalies 已移至 utils/metrics_parser.py

# ──────────────────────────────────────────────────────
# Q&A 語意搜尋
# ──────────────────────────────────────────────────────

def _load_qa_database() -> list[dict]:
    """優先讀最終版，否則用原始版"""
    final = config.OUTPUT_DIR / "qa_final.json"
    raw = config.OUTPUT_DIR / "qa_all_raw.json"

    if final.exists():
        data = json.loads(final.read_text(encoding="utf-8"))
        qas = data.get("qa_database", [])
        # 若只跑了測試批次（<50），改用原始版
        if len(qas) >= 50:
            return qas

    if raw.exists():
        data = json.loads(raw.read_text(encoding="utf-8"))
        return data.get("qa_pairs", [])

    return []


def _load_persisted_embeddings(qa_count: int) -> np.ndarray | None:
    """載入 Step 3 持久化的 embedding，若不存在或數量不匹配則回傳 None。"""
    emb_path = config.OUTPUT_DIR / "qa_embeddings.npy"
    if not emb_path.exists():
        return None
    emb = np.load(emb_path)
    if emb.shape[0] != qa_count:
        print(f"   ⚠️  Embedding 數量 ({emb.shape[0]}) 與 Q&A 數量 ({qa_count}) 不匹配，重新計算")
        return None
    return emb


# _compute_keyword_boost 已移至 utils/search_engine.py 作為模組級函式。
# 以 _compute_keyword_boost 作為 shim，維持內部呼叫點不變。
def _compute_keyword_boost(
    queries: list[str],
    qa_pairs: list[dict],
    boost: float | None = None,
    max_hits: int | None = None,
) -> np.ndarray:
    """Thin wrapper → delegates to compute_keyword_boost in utils/search_engine."""
    return compute_keyword_boost(queries, qa_pairs, boost=boost, max_hits=max_hits)


@observe(name="find_relevant_qas_multi")
def find_relevant_qas_multi(
    queries: list[str],
    qa_pairs: list[dict],
    top_k_per_query: int = 3,
    total_max: int = 15,
    min_score: float = 0.28,
) -> list[dict]:
    """
    多查詢版（Hybrid Search）：針對每個異常指標分別做 embedding 搜尋，
    並結合關鍵字精確匹配 boost，取各查詢 top_k 結果後合併去重。
    回傳的每筆 Q&A 帶有 `_queries` 欄位，記錄哪些查詢命中了它。
    """
    if not qa_pairs or not queries:
        return []

    # 嘗試載入持久化 embedding（避免重算）
    persisted_embs = _load_persisted_embeddings(len(qa_pairs))
    if persisted_embs is not None:
        print("   ✨ 使用持久化 embedding（免重算）")
        # 只需 embed queries
        query_embeddings = get_embeddings(queries)
        query_embs = np.array(query_embeddings)
        qa_embs = persisted_embs
    else:
        # Fallback: 一次批次 embed 所有 queries + 所有 QA 問題
        questions = [qa.get("question", "") for qa in qa_pairs]
        all_texts = queries + questions
        all_embeddings = get_embeddings(all_texts)
        query_embs = np.array(all_embeddings[: len(queries)])
        qa_embs = np.array(all_embeddings[len(queries) :])

    qa_norm = qa_embs / (np.linalg.norm(qa_embs, axis=1, keepdims=True) + 1e-8)
    q_norm = query_embs / (np.linalg.norm(query_embs, axis=1, keepdims=True) + 1e-8)
    # 語意相似度矩陣
    score_matrix = q_norm @ qa_norm.T  # (n_queries, n_qa)

    # Hybrid: 加上關鍵字 boost
    keyword_boost = _compute_keyword_boost(queries, qa_pairs)
    score_matrix = score_matrix + keyword_boost

    # 收集每個 query 的 top-k
    collected: dict[int, dict] = {}  # qa_index -> 結果 dict
    for qi, query in enumerate(queries):
        scores = score_matrix[qi]
        top_indices = np.argsort(scores)[::-1][:top_k_per_query]
        for idx in top_indices:
            if scores[idx] < min_score:
                continue
            if idx not in collected:
                collected[idx] = {
                    **qa_pairs[idx],
                    "_score": float(scores[idx]),
                    "_queries": [query],
                }
            else:
                # 同一 Q&A 被多個 query 命中 → 更新最高分 + 累積 queries
                if scores[idx] > collected[idx]["_score"]:
                    collected[idx]["_score"] = float(scores[idx])
                collected[idx]["_queries"].append(query)

    # 依最高分排序，取前 total_max
    results = sorted(collected.values(), key=lambda x: -x["_score"])
    return results[:total_max]


@observe(name="_rerank_qas")
def _rerank_qas(
    candidates: list[dict],
    context_summary: str,
    top_k: int,
) -> list[dict]:
    """
    LLM Reranker：用 gpt-5-mini 從候選 Q&A 中選出對當週指標摘要最有幫助的 top_k 筆。
    以結構化輸出回傳排序後的 index 陣列，失敗時 fallback 回原有排序。
    """
    if len(candidates) <= top_k:
        return candidates  # 候選數量不足，不須 rerank

    client = OpenAI(api_key=config.OPENAI_API_KEY)

    # 建立候選清單（截短 answer 節省 token）
    numbered = []
    for i, qa in enumerate(candidates):
        ans_snippet = (qa.get("answer") or "")[:200].replace("\n", " ")
        numbered.append(f"[{i}] Q: {qa['question']}\n    A（節錄）: {ans_snippet}")
    candidates_text = "\n\n".join(numbered)

    # 截短 context 避免 token 過多
    ctx = context_summary[:600] if len(context_summary) > 600 else context_summary

    prompt = (
        f"本週 SEO 指標摘要：\n{ctx}\n\n"
        f"以下是 {len(candidates)} 筆候選 Q&A（編號 0–{len(candidates)-1}）：\n\n"
        f"{candidates_text}\n\n"
        f"請從中選出對解讀本週指標最有直接幫助的 {top_k} 筆，"
        f"以重要性遞減順序回傳 index 陣列（JSON），例如 {{\"ranked\": [3, 0, 5, ...]}}。"
        f"只回傳 JSON，不要說明。"
    )

    try:
        resp = client.chat.completions.create(
            model="gpt-5-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            max_completion_tokens=256,
        )
        raw = resp.choices[0].message.content or "{}"
        ranked_indices: list[int] = json.loads(raw).get("ranked", [])
        # 過濾合法 index，補足 top_k
        valid = [i for i in ranked_indices if isinstance(i, int) and 0 <= i < len(candidates)]
        # 補入未被選中的（按原分數順序），確保回傳剛好 top_k 筆
        seen = set(valid)
        for i in range(len(candidates)):
            if i not in seen:
                valid.append(i)
        reranked = [candidates[i] for i in valid[:top_k]]
        print(f"   🎯 Reranker 完成：{len(candidates)} → {len(reranked)} 筆")
        return reranked
    except Exception as e:
        print(f"   ⚠️  Reranker 失敗（{e}），使用原始排序")
        return candidates[:top_k]


# ──────────────────────────────────────────────────────
# 格式化輔助
# ──────────────────────────────────────────────────────

def _fmt_pct(v) -> str:
    if v is None:
        return "N/A"
    if isinstance(v, float):
        sign = "+" if v > 0 else ""
        return f"{sign}{v*100:.1f}%"
    return str(v)


def _fmt_num(v) -> str:
    if v is None:
        return "N/A"
    if isinstance(v, float):
        if v >= 1_000_000:
            return f"{v/1_000_000:.2f}M"
        if v >= 1_000:
            return f"{v:,.0f}"
        # 判斷是比例還是數值
        if abs(v) <= 5:
            return f"{v:.4f}"
        return f"{v:.1f}"
    return str(v)


def _build_metrics_summary(alerts: list[dict]) -> str:
    """把關注指標整理成文字摘要，供 LLM 閱讀"""
    lines = []

    core = [a for a in alerts if a["flag"] == "CORE"]
    alert_down = [a for a in alerts if a["flag"] == "ALERT_DOWN"]
    alert_up = [a for a in alerts if a["flag"] == "ALERT_UP"]

    if core:
        lines.append("【核心指標】")
        for m in core:
            lines.append(
                f"  {m['name']}: 最新 {_fmt_num(m['latest'])} | "
                f"月趨勢 {_fmt_pct(m['monthly'])} | 週趨勢 {_fmt_pct(m['weekly'])}"
            )

    if alert_down:
        lines.append("\n【顯著下滑（月趨勢）】")
        for m in sorted(alert_down, key=lambda x: (x.get("monthly") or 0)):
            lines.append(
                f"  {m['name']}: {_fmt_pct(m['monthly'])} (月) / {_fmt_pct(m['weekly'])} (週)"
            )

    if alert_up:
        lines.append("\n【顯著上升（月趨勢）】")
        for m in sorted(alert_up, key=lambda x: -(x.get("monthly") or 0)):
            lines.append(
                f"  {m['name']}: {_fmt_pct(m['monthly'])} (月) / {_fmt_pct(m['weekly'])} (週)"
            )

    return "\n".join(lines)


# ──────────────────────────────────────────────────────
# LLM 報告產生
# ──────────────────────────────────────────────────────

REPORT_SYSTEM_PROMPT = """\
你是資深 SEO 分析師，任務是把本週的指標變化「翻譯成意義」，並用過去顧問會議累積的 Q&A 知識庫作為佐證。

重要原則：
- 用戶可以直接看 Google Sheets，**不需要你重複數字**。
- 每一個觀察必須說明「這代表什麼」「為什麼發生」「應該怎麼做」。
- 每個 insight 都應盡量引用【Q&A 知識庫】的具體內容作為依據，格式：（參考：「{Q&A 的關鍵句}」）
- 如果知識庫沒有直接對應，請根據 SEO 原理推論，並標明「（推論）」。
- 避免泛泛的 SEO 建議；結合本週資料的具體變化給出針對性意見。
- 引用知識庫時，請同時標註原始會議來源（標題+日期），方便讀者追溯驗證。

報告格式（Markdown，用繁體中文，技術術語保留英文）：

## 本週核心訊號
（3-4 點，每點說明一個重要的「現象 → 意義 → 知識庫怎麼說」，不提數字）

## 異常指標解讀
（針對顯著上升 / 下滑的指標，逐一解釋可能的因果機制，重點引用知識庫）

## 本週行動清單
（3 條具體 Todo，每條注明依據是哪個 Q&A 的建議或觀察）

## 直接引用知識庫
（原文引用 1-2 個本週最相關的 Q&A 問答，格式：**Q**：… / **A（節錄）**：… / **來源**：…）
"""


@observe(name="generate_report")
def generate_report(metrics_summary: str, relevant_qas: list[dict], metrics_date: str) -> str:
    client = OpenAI(api_key=config.OPENAI_API_KEY)

    # 知識庫：讓每條 Q&A 盡量完整，並標示被哪些指標查詢命中（幫助 LLM 知道關聯性）
    qa_context = ""
    if relevant_qas:
        qa_context = "\n\n【Q&A 知識庫（來自歷次 SEO 顧問會議記錄）】\n"
        qa_context += "（以下知識由指標異常查詢匹配，括號內是觸發此 Q&A 的指標信號）\n"
        for i, qa in enumerate(relevant_qas[:12], 1):
            triggered = "、".join(qa.get("_queries", [])[:3])
            snippet = qa["answer"][:600] + ("..." if len(qa["answer"]) > 600 else "")
            # 溯源資訊：讓報告讀者可以追溯到原始會議
            source_title = qa.get("source_title", "")
            source_date = qa.get("source_date", "")
            source_info = ""
            if source_title or source_date:
                parts = [p for p in [source_title, source_date] if p]
                source_info = f"來源：{'、'.join(parts)}\n"
            qa_context += (
                f"\n[{i}] 觸發信號：{triggered}\n"
                f"{source_info}"
                f"Q: {qa['question']}\n"
                f"A: {snippet}\n"
            )

    user_msg = (
        f"報告日期：{metrics_date}\n\n"
        f"【本週指標摘要】（數字僅供 LLM 判斷方向，報告中請勿重複羅列）\n"
        f"{metrics_summary}"
        f"{qa_context}"
    )

    response = client.chat.completions.create(
        model=config.OPENAI_MODEL,
        messages=[
            {"role": "system", "content": REPORT_SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        max_completion_tokens=16384,  # gpt-5 推理模型：reasoning + output 共享，需預留足夠空間
    )

    msg = response.choices[0].message
    content = msg.content

    # gpt-5 系列可能將內容放在 reasoning_content（thinking output）
    if not content:
        reasoning = getattr(msg, "reasoning_content", None)
        if reasoning:
            print(f"   ⚠️  content 為空，嘗試使用 reasoning_content（{len(reasoning)} chars）")
            content = reasoning
        else:
            print(f"   ❌ finish_reason={response.choices[0].finish_reason}")
            print(f"   ❌ refusal={getattr(msg, 'refusal', None)}")
            print(f"   ❌ msg fields: {getattr(msg, 'model_fields_set', None)}")

    return content or "（報告產生失敗）"


# ──────────────────────────────────────────────────────
# 主程式
# ──────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="產生每週 SEO 分析報告")
    parser.add_argument(
        "--input", "-i",
        type=str,
        default=None,
        help="Google Sheets URL 或本機 TSV 路徑。不指定則用 config.SHEETS_URL 或預設 URL。",
    )
    parser.add_argument(
        "--tab",
        type=str,
        default="vocus",
        help="Google Sheets 分頁名稱（預設: vocus）",
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=None,
        help="輸出 Markdown 報告路徑。預設：output/report_YYYYMMDD.md",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=15,
        help="從知識庫最多取幾個相關 Q&A（預設 15）",
    )
    parser.add_argument(
        "--no-qa",
        action="store_true",
        help="不使用 Q&A 知識庫（單純分析指標）",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="只檢查依賴是否就緒，不實際執行",
    )
    args = parser.parse_args()

    init_laminar()

    # ── Preflight dependency check ───────────────────────────
    deps = []
    if not args.no_qa:
        deps = [
            StepDependency(
                path=config.OUTPUT_DIR / "qa_final.json",
                required=False,
                max_age_days=7,
                hint="請先執行 python scripts/03_dedupe_classify.py（或用 --no-qa 略過）",
            ),
            StepDependency(
                path=config.OUTPUT_DIR / "qa_embeddings.npy",
                required=False,
                max_age_days=7,
            ),
        ]
    preflight_check(
        deps=deps,
        env_keys=["OPENAI_API_KEY"],
        step_name="Step 4: 週報生成",
        check_only=args.check,
    )
    if args.check:
        return

    print("=" * 60)
    print("📊 SEO 週報產生器")
    print("=" * 60)

    # 決定資料來源（優先順序：--input > .env SHEETS_URL > 預設 URL）
    source = args.input or getattr(config, "SHEETS_URL", "") or DEFAULT_SHEETS_URL

    if source.startswith("http"):
        print(f"\n📥 從 Google Sheets 擷取（tab: {args.tab}）...")
        try:
            tsv_text = fetch_from_sheets(source, tab=args.tab)
        except Exception as e:
            print(f"❌ 下載失敗：{e}")
            print("💡 請確認該試算表權限為「任何知道連結者可檢視」")
            sys.exit(1)
    elif source:
        tsv_text = Path(source).read_text(encoding="utf-8")
    else:
        print("📋 請貼上試算表資料（完成後按 Ctrl+D）：")
        tsv_text = sys.stdin.read()

    if not tsv_text.strip():
        print("❌ 沒有收到資料")
        sys.exit(1)

    # 解析
    print("\n🔍 解析指標資料 ...")
    metrics = parse_metrics_tsv(tsv_text)
    if not metrics:
        print("❌ 無法解析指標，請確認格式是從 Google 試算表直接複製的 TSV")
        sys.exit(1)
    print(f"   解析到 {len(metrics)} 個指標")

    # 異常偵測
    alerts = detect_anomalies(metrics)
    alert_down = [a for a in alerts if a["flag"] == "ALERT_DOWN"]
    alert_up = [a for a in alerts if a["flag"] == "ALERT_UP"]
    print(f"   核心指標: {len([a for a in alerts if a['flag']=='CORE'])} 個")
    print(f"   顯著下滑: {len(alert_down)} 個 | 顯著上升: {len(alert_up)} 個")

    metrics_summary = _build_metrics_summary(alerts)

    # 語意搜尋相關 Q&A（多查詢策略：每個異常指標獨立查詢）
    relevant_qas = []
    if not args.no_qa:
        print("\n🔎 搜尋相關 Q&A 知識庫 ...")
        qa_pairs = _load_qa_database()
        if qa_pairs:
            print(f"   知識庫共 {len(qa_pairs)} 個 Q&A")
            # 為每個需要解釋的指標建立語意查詢
            queries: list[str] = []
            seen: set[str] = set()

            def _add_query(q: str) -> None:
                if q not in seen:
                    seen.add(q)
                    queries.append(q)

            for a in alerts:
                name = a["name"]
                monthly = a.get("monthly") or 0
                weekly = a.get("weekly") or 0
                direction = "下降" if (monthly < 0 or weekly < 0) else "上升"

                # 優先使用 METRIC_QUERY_MAP 的精確查詢
                if name in METRIC_QUERY_MAP:
                    for q in METRIC_QUERY_MAP[name]:
                        _add_query(q)
                else:
                    # 通用退回模板
                    if a["flag"] == "CORE":
                        _add_query(f"{name} {direction} 代表什麼 SEO 含義")
                    elif a["flag"] == "ALERT_DOWN":
                        _add_query(f"{name} 大幅下降 原因 怎麼處理")
                    elif a["flag"] == "ALERT_UP":
                        _add_query(f"{name} 大幅上升 代表什麼 注意事項")

            # 固定補充：確保核心知識庫場景必然覆蓋
            for q in [
                "CTR 持續下降 搜尋結果外觀 如何改善",
                "檢索未索引增加 WAF 封鎖 Googlebot",
                "Discover 流量波動 探索演算法",
                "AMP Article 流量下降 焦點新聞",
                "伺服器回應時間 爬蟲抓取 索引影響",
            ]:
                _add_query(q)

            # 先取較大的候選池（top_k 的 2 倍，最多 30），再用 LLM Reranker 精選
            candidate_pool = max(args.top_k * 2, 20)
            candidates = find_relevant_qas_multi(
                queries, qa_pairs,
                top_k_per_query=3,
                total_max=candidate_pool,
            )
            print(f"   使用 {len(queries)} 個查詢，候選 {len(candidates)} 個 Q&A")
            relevant_qas = _rerank_qas(candidates, metrics_summary, args.top_k)
            print(f"   使用 {len(queries)} 個查詢，找到 {len(relevant_qas)} 個相關 Q&A（已 Rerank）")
        else:
            print("   ⚠️  找不到 Q&A 知識庫，跳過（先執行步驟 2-3 建立知識庫）")

    # 取得日期，標準化為 YYYYMMDD
    sample_metric = next((m for m in metrics.values() if m.get("latest_date")), {})
    raw_date = sample_metric.get("latest_date", "")
    try:
        # 解析 M/D/YYYY → YYYYMMDD
        dt = datetime.strptime(raw_date, "%m/%d/%Y")
        date_str = dt.strftime("%Y%m%d")
        report_date = dt.strftime("%Y/%m/%d")
    except ValueError:
        date_str = datetime.today().strftime("%Y%m%d")
        report_date = raw_date or datetime.today().strftime("%Y/%m/%d")

    # 產生報告
    print(f"\n✍️  產生報告（日期：{report_date}）...")
    report_md = generate_report(metrics_summary, relevant_qas, report_date)

    # 輸出
    if args.output:
        out_path = Path(args.output)
    else:
        out_path = config.OUTPUT_DIR / f"report_{date_str}.md"

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report_md, encoding="utf-8")

    print("\n" + "=" * 60)
    print(f"✅ 報告完成！")
    print(f"   📄 {out_path}")
    print("=" * 60)

    # 直接印到 console
    print("\n" + "─" * 60)
    print(report_md)

    flush_laminar()


if __name__ == "__main__":
    main()
