#!/usr/bin/env python3
"""
enrich_qa.py — Offline Q&A Enrichment Pipeline

對 qa_final.json 的每筆 Q&A 計算：
  - synonyms:         關鍵字的同義詞展開（utils/synonym_dict）
  - freshness_score:  時效性分數（utils/freshness，指數衰減）
  - search_hit_count: 搜尋命中次數（從 access_logs 聚合）

輸出：output/qa_enriched.json
  - 與 qa_final.json 格式相同
  - 每筆 Q&A 新增 "_enrichment" 欄位

不消耗 LLM token（純規則式，幂等）。
"""
from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

from typing import Any

logger = logging.getLogger(__name__)

# 確保 project root 在 path
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from utils.freshness import compute_freshness_score  # noqa: E402
from utils.maturity_classifier import classify_maturity_level  # noqa: E402
from utils.notion_url_map import build_source_to_notion_url  # noqa: E402
from utils.synonym_dict import expand_keywords  # noqa: E402

OUTPUT_DIR = _ROOT / "output"
QA_FINAL_PATH = OUTPUT_DIR / "qa_final.json"
QA_ENRICHED_PATH = OUTPUT_DIR / "qa_enriched.json"
ACCESS_LOGS_DIR = OUTPUT_DIR / "access_logs"

INTENT_PATTERNS: dict[str, tuple[str, ...]] = {
    "diagnosis": ("異常", "下滑", "問題", "診斷", "原因", "why", "根因"),
    "root-cause": ("root cause", "根因", "歸因", "waf", "canonical", "衝突"),
    "implementation": ("如何", "怎麼", "修正", "實作", "設定", "schema", "標記"),
    "measurement": ("ga", "ga4", "gsc", "ctr", "曝光", "點擊", "kpi", "追蹤", "ratio", "share", "佔比"),
    "reporting": ("報告", "週報", "監測", "儀表板", "slice"),
    "platform-decision": ("平台", "策略", "roadmap", "優先", "取捨", "vocus"),
}

SCENARIO_PATTERNS: dict[str, tuple[str, ...]] = {
    "discover": ("discover", "探索"),
    "google-news": ("google news", "news", "新聞"),
    "faq-rich-result": ("faq", "rich result", "搜尋外觀"),
    "ga4-attribution": ("ga4", "attribution", "歸因", "unassigned"),
    "author-page": ("/user", "作者頁", "author"),
    "image-seo": ("image", "圖片", "alt", "縮圖"),
    "core-web-vitals": ("core web vitals", "cwv", "lcp", "cls", "行動版", "手機體驗"),
    "video-seo": ("videoobject", "video appearance", "影片", "video"),
    "sitemap-api": ("sitemap", "url inspection", "inspection api", "cms api"),
    "ai-referral-traffic": ("chatgpt", "perplexity", "gemini", "ai 流量", "流量佔比"),
}

CATEGORY_HINTS: dict[str, tuple[str, ...]] = {
    "技術SEO": (
        "core web vitals", "lcp", "cls", "schema", "結構化資料", "ttfb", "速度", "amp",
        "videoobject", "video appearance", "sitemap", "url inspection", "inspection api",
        "mobile seo", "行動版", "手機", "json-ld",
    ),
    "索引與檢索": ("索引", "coverage", "googlebot", "canonical", "檢索未索引"),
    "搜尋表現分析": ("ctr", "曝光", "點擊", "排名", "serp", "search console", "kpi", "品牌", "非品牌", "brand", "non-brand"),
    "GA與數據追蹤": ("ga", "ga4", "歸因", "事件", "direct", "unassigned", "chatgpt", "perplexity", "gemini", "ratio", "share", "佔比"),
    "Discover與AMP": ("discover", "amp", "news", "探索"),
    "內容策略": ("內容", "文章", "供給", "eeat", "主題", "更新"),
    "連結策略": ("連結", "內部連結", "錨點", "backlink"),
    "平台策略": ("平台", "作者", "路徑", "站內", "vocus", "/user", "cms"),
    "演算法與趨勢": ("演算法", "更新", "ai", "趨勢", "gemini", "perplexity", "chatgpt", "ai overview", "ai search", "llm"),
}


def _normalize_text(qa: dict[str, Any]) -> str:
    text_parts = [qa.get("question", ""), qa.get("answer", "")]
    text_parts.extend(qa.get("keywords", []))
    return " ".join(str(part) for part in text_parts if part).lower()


def _infer_categories(primary_category: str, text: str) -> tuple[list[str], str]:
    categories: list[str] = [primary_category] if primary_category else []
    for category, hints in CATEGORY_HINTS.items():
        if category == primary_category:
            continue
        if any(hint in text for hint in hints):
            categories.append(category)

    if any(token in text for token in ("discover", "google news", "news", "探索", "amp")):
        categories.append("Discover與AMP")
    if any(token in text for token in ("演算法", "update", "趨勢", "ai overview", "ai search", "chatgpt", "gemini", "perplexity", "sge", "discover", "google news")):
        categories.append("演算法與趨勢")
    if any(token in text for token in ("waf", "googlebot", "canonical", "coverage", "檢索未索引", "sitemap", "url inspection", "inspection api", "索引")):
        categories.extend(["索引與檢索", "技術SEO"])
    if any(token in text for token in ("ga", "ga4", "gsc", "direct", "referral", "歸因")) and any(token in text for token in ("discover", "amp", "news", "探索")):
        categories.extend(["GA與數據追蹤", "Discover與AMP"])
    if any(token in text for token in ("轉換率", "conversion", "signups", "註冊")) and any(token in text for token in ("ai search", "ai overview", "chatgpt", "perplexity", "gemini", "ai 流量")):
        categories.extend(["搜尋表現分析", "內容策略", "演算法與趨勢"])

    # Preserve order while removing duplicates.
    deduped = list(dict.fromkeys(categories))
    if len(deduped) >= 3:
        confidence = "high"
    elif len(deduped) == 2:
        confidence = "medium"
    else:
        confidence = "low"
    return deduped, confidence


def _infer_labels(text: str, mapping: dict[str, tuple[str, ...]]) -> list[str]:
    labels: list[str] = []
    for label, hints in mapping.items():
        if any(hint in text for hint in hints):
            labels.append(label)
    return labels


def _infer_serving_tier(qa: dict[str, Any], confidence: str) -> str:
    curation_tag = str(qa.get("manual_curation_tag", "")).lower()
    curation_reason = str(qa.get("manual_curation_reason", "")).lower()
    if "booster" in curation_tag or "booster" in curation_reason:
        return "booster"
    if confidence == "low":
        return "supporting"
    return "canonical"


def _derive_retrieval_phrases(question: str, keywords: list[str]) -> list[str]:
    phrases: list[str] = []
    q_tokens = [token for token in question.lower().split() if len(token) >= 2]
    for idx in range(len(q_tokens) - 1):
        phrases.append(f"{q_tokens[idx]} {q_tokens[idx + 1]}")
    phrases.extend(keyword.lower() for keyword in keywords if keyword)
    return list(dict.fromkeys(phrases))[:12]


def _infer_granularity(text: str) -> str:
    if any(token in text for token in ("步驟", "checklist", "如何", "修正", "設定")):
        return "tactical"
    if any(token in text for token in ("診斷", "根因", "為什麼", "異常")):
        return "diagnostic"
    return "strategic"


def _infer_evidence_scope(text: str) -> list[str]:
    scopes: list[str] = []
    if any(token in text for token in ("cwv", "schema", "索引", "crawl", "canonical", "技術")):
        scopes.append("technical")
    if any(token in text for token in ("內容", "文章", "eeat", "主題", "編輯")):
        scopes.append("content")
    if any(token in text for token in ("ga", "ga4", "gsc", "曝光", "點擊", "ctr", "session")):
        scopes.append("analytics")
    if any(token in text for token in ("平台", "作者", "路徑", "ia", "產品")):
        scopes.append("platform")
    return scopes


def _infer_retrieval_metadata(qa: dict[str, Any]) -> dict[str, Any]:
    primary_category = str(qa.get("category", "")).strip()
    keywords = [str(keyword) for keyword in qa.get("keywords", []) if keyword]
    question = str(qa.get("question", ""))
    text = _normalize_text(qa)

    categories, confidence = _infer_categories(primary_category, text)
    intent_labels = _infer_labels(text, INTENT_PATTERNS)
    scenario_tags = _infer_labels(text, SCENARIO_PATTERNS)
    serving_tier = _infer_serving_tier(qa, confidence)
    retrieval_phrases = _derive_retrieval_phrases(question, keywords)

    retrieval_surface_parts = [question, str(qa.get("answer", ""))]
    retrieval_surface_parts.extend(categories)
    retrieval_surface_parts.extend(intent_labels)
    retrieval_surface_parts.extend(scenario_tags)
    retrieval_surface_parts.extend(keywords)

    metadata: dict[str, Any] = {
        "primary_category": primary_category,
        "categories": categories,
        "intent_labels": intent_labels,
        "scenario_tags": scenario_tags,
        "serving_tier": serving_tier,
        "retrieval_phrases": retrieval_phrases,
        "retrieval_surface_text": "\n".join(part for part in retrieval_surface_parts if part),
        "content_granularity": _infer_granularity(text),
        "evidence_scope": _infer_evidence_scope(text),
        "booster_target_queries": retrieval_phrases[:5] if serving_tier == "booster" else [],
        "hard_negative_terms": ["無關", "不適用", "誤判"] if confidence == "low" else [],
        "backfill_confidence": confidence,
    }
    return metadata


def _infer_maturity_relevance(qa: dict[str, Any]) -> str | None:
    existing = qa.get("maturity_relevance")
    if existing in {"L1", "L2", "L3", "L4"}:
        return str(existing)
    enrichment_existing = (qa.get("_enrichment") or {}).get("maturity_relevance")
    if enrichment_existing in {"L1", "L2", "L3", "L4"}:
        return str(enrichment_existing)
    return classify_maturity_level(
        keywords=[str(keyword) for keyword in qa.get("keywords", []) if keyword],
        question=str(qa.get("question", "")),
        answer=str(qa.get("answer", "")),
    )


def _aggregate_hit_counts() -> dict[str, int]:
    """
    從 access_logs/*.jsonl 聚合每筆 Q&A 的搜尋命中次數。

    只計算含 top_score 欄位的新格式記錄（MEDIUM-5 修復後才有）。
    若 access_logs 不存在，回傳空 dict。
    新舊記錄相容：int ID 自動轉 str。
    """
    hit_counts: dict[str, int] = {}
    if not ACCESS_LOGS_DIR.exists():
        return hit_counts

    for log_file in sorted(ACCESS_LOGS_DIR.glob("access_*.jsonl")):
        try:
            for line in log_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                record = json.loads(line)
                if record.get("event") not in ("search", "chat"):
                    continue
                if "top_score" not in record:
                    continue
                for qa_id in record.get("returned_ids", []):
                    key = str(qa_id)
                    hit_counts[key] = hit_counts.get(key, 0) + 1
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("access_log 讀取失敗：%s — %s", log_file, exc)

    return hit_counts


def _enrich_qa(
    qa: dict,
    hit_counts: dict[str, int],
    notion_url_map: dict[str, str],
) -> dict:
    """
    對單筆 Q&A 計算 enrichment 欄位。

    Args:
        qa:             原始 Q&A dict（qa_final.json 格式）
        hit_counts:     {qa_id: count} 聚合搜尋命中次數
        notion_url_map: {source_file: notion_url} 映射

    Returns:
        新的 dict（不修改原始 qa），加入 "_enrichment" 欄位
    """
    keywords = qa.get("keywords", [])
    source_date = qa.get("source_date", "")
    is_evergreen = bool(qa.get("evergreen", False))

    synonyms = expand_keywords(keywords)
    freshness_score = compute_freshness_score(source_date, is_evergreen)
    qa_id = qa.get("stable_id", str(qa.get("id", 0)))
    search_hit_count = hit_counts.get(qa_id, 0)

    # Notion URL：從 source_file 查映射
    source_file = qa.get("source_file", "")
    notion_url = notion_url_map.get(source_file, "")

    # source_url：article 類型直接使用 Q&A 本身的 source_url；meeting 類型用 notion_url
    source_type = qa.get("source_type", "meeting")
    source_url_value = str(qa.get("source_url", "")).strip()
    if source_type != "meeting" and source_url_value:
        source_url = source_url_value
    else:
        source_url = notion_url

    retrieval_metadata = _infer_retrieval_metadata(qa)
    maturity_relevance = _infer_maturity_relevance(qa)

    enrichment = {
        "synonyms": synonyms,
        "freshness_score": freshness_score,
        "search_hit_count": search_hit_count,
        "notion_url": notion_url,
        "source_url": source_url,
        "maturity_relevance": maturity_relevance,
        "backfill_confidence": retrieval_metadata["backfill_confidence"],
    }
    return {
        **qa,
        "maturity_relevance": maturity_relevance,
        "primary_category": retrieval_metadata["primary_category"],
        "categories": retrieval_metadata["categories"],
        "intent_labels": retrieval_metadata["intent_labels"],
        "scenario_tags": retrieval_metadata["scenario_tags"],
        "serving_tier": retrieval_metadata["serving_tier"],
        "retrieval_phrases": retrieval_metadata["retrieval_phrases"],
        "retrieval_surface_text": retrieval_metadata["retrieval_surface_text"],
        "content_granularity": retrieval_metadata["content_granularity"],
        "evidence_scope": retrieval_metadata["evidence_scope"],
        "booster_target_queries": retrieval_metadata["booster_target_queries"],
        "hard_negative_terms": retrieval_metadata["hard_negative_terms"],
        "_enrichment": enrichment,
    }


def run_enrichment(
    input_path: Path = QA_FINAL_PATH,
    output_path: Path = QA_ENRICHED_PATH,
) -> dict:
    """
    執行完整 enrichment pipeline。

    Args:
        input_path:  輸入 qa_final.json
        output_path: 輸出 qa_enriched.json

    Returns:
        {
            "total": int,
            "enriched": int,
            "avg_synonyms": float,
            "avg_freshness": float,
            "notion_url_count": int,
            "notion_url_pct": float,
        }
    """
    if not input_path.exists():
        raise FileNotFoundError(f"找不到輸入檔案：{input_path}")

    logger.info("讀取 %s", input_path)
    raw = json.loads(input_path.read_text(encoding="utf-8"))
    qa_list: list[dict] = raw.get("qa_database", [])

    if not qa_list:
        raise ValueError("qa_database 為空，請先執行 Step 3（dedupe-classify）")

    logger.info("聚合 access_logs 搜尋命中次數...")
    hit_counts = _aggregate_hit_counts()
    logger.info("有搜尋記錄的 Q&A：%d 筆", len(hit_counts))

    logger.info("建立 Notion URL 映射...")
    notion_url_map = build_source_to_notion_url()
    logger.info("Notion URL 映射：%d 筆", len(notion_url_map))

    logger.info("Enrichment 中（%d 筆 Q&A）...", len(qa_list))
    enriched_list = [_enrich_qa(qa, hit_counts, notion_url_map) for qa in qa_list]

    total_synonyms = sum(len(qa["_enrichment"]["synonyms"]) for qa in enriched_list)
    total_freshness = sum(qa["_enrichment"]["freshness_score"] for qa in enriched_list)
    total_with_url = sum(1 for qa in enriched_list if qa["_enrichment"].get("notion_url"))
    categories_coverage = sum(1 for qa in enriched_list if qa.get("categories"))
    intent_coverage = sum(1 for qa in enriched_list if qa.get("intent_labels"))
    scenario_coverage = sum(1 for qa in enriched_list if qa.get("scenario_tags"))
    serving_tier_coverage = sum(1 for qa in enriched_list if qa.get("serving_tier"))
    confidence_distribution: dict[str, int] = {"high": 0, "medium": 0, "low": 0}
    for qa in enriched_list:
        confidence = qa.get("_enrichment", {}).get("backfill_confidence", "low")
        confidence_distribution[confidence] = confidence_distribution.get(confidence, 0) + 1
    n = len(enriched_list)

    if notion_url_map and total_with_url == 0:
        logger.warning(
            "Notion URL 映射有 %d 筆但無 Q&A 命中，請確認 source_file 格式是否與映射 key 相符",
            len(notion_url_map),
        )

    output_data = {
        **{k: v for k, v in raw.items() if k != "qa_database"},
        "qa_database": enriched_list,
        "_enriched_at": datetime.now(timezone.utc).isoformat(),
    }

    # 原子寫入
    tmp = output_path.with_suffix(".tmp")
    tmp.write_text(json.dumps(output_data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(output_path)
    logger.info("已寫入 %s（%d 筆）", output_path, n)

    stats = {
        "total": n,
        "enriched": n,
        "avg_synonyms": round(total_synonyms / n, 2) if n else 0.0,
        "avg_freshness": round(total_freshness / n, 4) if n else 0.0,
        "notion_url_count": total_with_url,
        "notion_url_pct": round(total_with_url / n * 100, 1) if n else 0.0,
        "categories_coverage": round(categories_coverage / n, 4) if n else 0.0,
        "intent_labels_coverage": round(intent_coverage / n, 4) if n else 0.0,
        "scenario_tags_coverage": round(scenario_coverage / n, 4) if n else 0.0,
        "serving_tier_coverage": round(serving_tier_coverage / n, 4) if n else 0.0,
        "backfill_confidence_distribution": confidence_distribution,
    }
    logger.info(
        "Enrichment 完成：avg_synonyms=%.2f, avg_freshness=%.4f, notion_url=%.1f%%",
        stats["avg_synonyms"],
        stats["avg_freshness"],
        stats["notion_url_pct"],
    )
    return stats


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    import argparse

    parser = argparse.ArgumentParser(description="Offline Q&A enrichment（synonym + freshness + usage）")
    parser.add_argument("--input", default=str(QA_FINAL_PATH), help="輸入 JSON 路徑")
    parser.add_argument("--output", default=str(QA_ENRICHED_PATH), help="輸出 JSON 路徑")
    args = parser.parse_args()

    stats = run_enrichment(Path(args.input), Path(args.output))
    print(f"Total Q&A:       {stats['total']}")
    print(f"Avg synonyms:    {stats['avg_synonyms']:.2f}")
    print(f"Avg freshness:   {stats['avg_freshness']:.4f}")
    print(f"Notion URL:      {stats['notion_url_count']}/{stats['total']} ({stats['notion_url_pct']:.1f}%)")
