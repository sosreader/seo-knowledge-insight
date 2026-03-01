"""
Laminar 離線評估：Enrichment 前後 KW Hit Rate 比較

評估目標：
  - kw_hit_rate_with_synonyms: 使用同義詞擴展後的關鍵字命中率
  - freshness_rank_quality:    舊 Q&A 排名是否低於新 Q&A（相同語意相關度）
  - synonym_coverage:          每筆 Q&A 平均同義詞數量

Dataset: eval/golden_retrieval.json
Requires: output/qa_enriched.json（先執行 make enrich）
         LMNR_PROJECT_API_KEY（可選，若無則跑本地評估）

Run:
    python evals/eval_enrichment.py
    lmnr eval evals/eval_enrichment.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from lmnr import evaluate  # type: ignore[import]
    _LMNR_AVAILABLE = True
except ImportError:
    _LMNR_AVAILABLE = False

# ── Dataset ───────────────────────────────────────────────────────────────────

_golden_path = PROJECT_ROOT / "eval" / "golden_retrieval.json"
_enriched_path = PROJECT_ROOT / "output" / "qa_enriched.json"
_final_path = PROJECT_ROOT / "output" / "qa_final.json"


def _load_qa_database(path: Path) -> list[dict]:
    """載入 qa_final.json 或 qa_enriched.json 的 qa_database 清單。"""
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data.get("qa_database", [])
    except (json.JSONDecodeError, OSError):
        return []


def _build_dataset() -> list[dict]:
    """
    從 golden_retrieval.json 建立評估 dataset。

    若 golden 不存在，使用 qa_enriched.json 的前 20 筆建立最小 dataset。
    """
    if _golden_path.exists():
        try:
            golden = json.loads(_golden_path.read_text(encoding="utf-8"))
            return [
                {
                    "data": {"query": item["query"]},
                    "target": {
                        "expected_keywords": item.get("expected_keywords", []),
                        "expected_categories": item.get("expected_categories", []),
                    },
                }
                for item in golden[:50]
            ]
        except (json.JSONDecodeError, KeyError):
            pass

    # Fallback: 用 enriched Q&A 的前 20 筆問題作為查詢
    qa_list = _load_qa_database(_enriched_path) or _load_qa_database(_final_path)
    return [
        {
            "data": {"query": qa["question"]},
            "target": {"expected_keywords": qa.get("keywords", [])},
        }
        for qa in qa_list[:20]
    ]


_dataset = _build_dataset()

if not _dataset:
    print("[eval_enrichment] No dataset available — run pipeline Steps 1–3 first", file=sys.stderr)
    sys.exit(1)


# ── Executor ──────────────────────────────────────────────────────────────────

def enriched_retrieval_executor(data: dict) -> dict:
    """
    Keyword-based retrieval using enriched knowledge base.

    若 qa_enriched.json 存在，利用 synonyms 欄位進行擴展搜尋。
    否則 fallback 到 qa_final.json 做標準關鍵字搜尋。
    """
    query: str = data["query"]

    # 優先使用 enriched
    qa_list = _load_qa_database(_enriched_path) or _load_qa_database(_final_path)
    if not qa_list:
        return {"results": [], "query": query, "enriched": False}

    is_enriched = _enriched_path.exists()
    query_lower = query.lower()
    query_tokens = set(query_lower.split())

    scored: list[tuple[float, dict]] = []
    for qa in qa_list:
        keywords = qa.get("keywords", [])
        synonyms = qa.get("_enrichment", {}).get("synonyms", []) if is_enriched else []
        all_terms = keywords + synonyms

        hits = sum(
            1 for term in all_terms
            if term.lower() in query_lower or any(t in term.lower() for t in query_tokens)
        )
        freshness = qa.get("_enrichment", {}).get("freshness_score", 1.0) if is_enriched else 1.0

        if hits > 0:
            score = hits * freshness
            scored.append((score, qa))

    scored.sort(key=lambda x: -x[0])
    results = [qa for _, qa in scored[:5]]

    return {
        "results": results,
        "query": query,
        "enriched": is_enriched,
    }


# ── Evaluators ────────────────────────────────────────────────────────────────

def kw_hit_rate_with_synonyms(output: dict, target: dict) -> float:
    """
    評估指標 1：同義詞擴展後的關鍵字命中率

    計算 expected_keywords 中，有多少在 top-5 結果的 keywords + synonyms 中出現。
    """
    expected = target.get("expected_keywords", [])
    if not expected:
        return 1.0

    results = output.get("results", [])
    if not results:
        return 0.0

    all_terms: set[str] = set()
    for qa in results:
        for kw in qa.get("keywords", []):
            all_terms.add(kw.lower())
        for syn in qa.get("_enrichment", {}).get("synonyms", []):
            all_terms.add(syn.lower())

    hits = sum(1 for kw in expected if any(kw.lower() in t or t in kw.lower() for t in all_terms))
    return hits / len(expected)


def freshness_rank_quality(output: dict, target: dict) -> float:
    """
    評估指標 2：時效性排名品質

    檢查結果中舊的（非 evergreen）Q&A 是否不在 Top-3。
    若 enriched=False，直接回傳 1.0（無法評估）。
    """
    if not output.get("enriched", False):
        return 1.0

    results = output.get("results", [])
    if not results:
        return 1.0

    top3 = results[:3]
    stale_in_top3 = 0
    for qa in top3:
        enrichment = qa.get("_enrichment", {})
        freshness = float(enrichment.get("freshness_score", 1.0))
        evergreen = qa.get("evergreen", True)
        if not evergreen and freshness < 0.7:
            stale_in_top3 += 1

    # 越少 stale Q&A 在 Top-3，品質越高
    return 1.0 - (stale_in_top3 / 3.0)


def synonym_coverage(output: dict, target: dict) -> float:
    """
    評估指標 3：同義詞覆蓋率

    計算 top-5 結果的平均同義詞數量，歸一化到 [0, 1]（以 10 個同義詞為滿分）。
    """
    results = output.get("results", [])
    if not results:
        return 0.0

    total_synonyms = sum(
        len(qa.get("_enrichment", {}).get("synonyms", []))
        for qa in results
    )
    avg = total_synonyms / len(results)
    return min(avg / 10.0, 1.0)


# ── Run evaluation ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if _LMNR_AVAILABLE:
        evaluate(
            data=_dataset,
            executor=enriched_retrieval_executor,
            evaluators={
                "kw_hit_rate_with_synonyms": kw_hit_rate_with_synonyms,
                "freshness_rank_quality": freshness_rank_quality,
                "synonym_coverage": synonym_coverage,
            },
            group_name="enrichment_quality",
        )
    else:
        # 本地評估模式（不需要 Laminar）
        print("lmnr not installed — running local evaluation\n")
        kw_scores: list[float] = []
        freshness_scores: list[float] = []
        syn_scores: list[float] = []

        for item in _dataset:
            output = enriched_retrieval_executor(item["data"])
            kw = kw_hit_rate_with_synonyms(output, item["target"])
            fr = freshness_rank_quality(output, item["target"])
            sy = synonym_coverage(output, item["target"])
            kw_scores.append(kw)
            freshness_scores.append(fr)
            syn_scores.append(sy)

        n = len(_dataset)
        print(f"Dataset size:              {n}")
        print(f"KW Hit Rate (synonyms):    {sum(kw_scores)/n:.1%}")
        print(f"Freshness Rank Quality:    {sum(freshness_scores)/n:.3f}")
        print(f"Synonym Coverage:          {sum(syn_scores)/n:.3f}")
