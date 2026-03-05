"""
_eval_laminar.py — Laminar 正式 Eval Run（v2.13，4 層評估框架）

將 golden_retrieval.json 推送至 Laminar Dashboard 作為正式評估資料集。
執行後結果出現在 Laminar Dashboard 的 Evaluations 頁面。

支援兩種模式（--mode）：

  retrieval（預設）— IR 標準指標評估，支援兩個 group：
    retrieval-eval       — Layer 2 IR 標準指標（precision/recall/f1/hit_rate/mrr/ndcg/top1/top5）
    retrieval-enhancement — Layer 3 同義詞增強指標（kw_hit_rate_with_synonyms/synonym_coverage/freshness_rank_quality）

  report — 報告品質評估（group: report-quality-eval）
    評估 output/report_*.md 的結構完整性：
    section_coverage / kb_links / research_cited / overall

使用：
    python scripts/_eval_laminar.py
    python scripts/_eval_laminar.py --top-k 5
    python scripts/_eval_laminar.py --group "retrieval-eval"
    python scripts/_eval_laminar.py --group "retrieval-enhancement"
    python scripts/_eval_laminar.py --mode report

學術依據：
  MRR, Precision@K, Recall@K, F1@K — TREC / IR 標準（Voorhees）
  NDCG@K — Jarvelin & Kekalainen (2002), ACM TOIS
  Synonym Coverage — 本專案自訂（Layer 3 同義詞擴充效益）
  Report Quality — 本專案自訂（ECC 多視角分析框架 v2.13）
"""
from __future__ import annotations

import argparse
import json
import logging
import math
import sys
from pathlib import Path

# 確保 project root 在 import path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# 載入 .env 環境變數
from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

from utils.observability import init_laminar  # type: ignore

logger = logging.getLogger(__name__)

GOLDEN_RETRIEVAL_PATH = ROOT / "output" / "evals" / "golden_retrieval.json"
QA_FINAL_PATH = ROOT / "output" / "qa_final.json"
QA_ENRICHED_PATH = ROOT / "output" / "qa_enriched.json"
REPORTS_DIR = ROOT / "output"

DEFAULT_GROUP = "retrieval-eval"

# ── Report quality constants (mirrors TypeScript report-evaluator.ts) ──────

REPORT_SECTION_MARKERS = ["## 一、", "## 二、", "## 三、", "## 四、", "## 五、", "## 六、"]
REPORT_RESEARCH_KEYWORDS = [
    "Semrush", "GSC", "Backlinko", "First Page Sage",
    "NavBoost", "E-E-A-T", "arxiv",
]
KB_LINK_PATTERN = "/admin/seoInsight/chunk/"


# ── 資料載入 ────────────────────────────────────────────────────────────────


def _load_qas() -> list[dict]:
    path = QA_ENRICHED_PATH if QA_ENRICHED_PATH.exists() else QA_FINAL_PATH
    data = json.loads(path.read_text(encoding="utf-8"))
    return data["qa_database"]


def _load_synonyms() -> dict[str, list[str]]:
    try:
        from utils.synonym_dict import SYNONYMS  # type: ignore
        return SYNONYMS
    except ImportError:
        logger.warning("utils.synonym_dict 不可用，synonym evaluators 將回傳 0")
        return {}


# ── 搜尋函式 ────────────────────────────────────────────────────────────────


def _keyword_search(query: str, qas: list[dict], top_k: int) -> list[dict]:
    """標準關鍵字搜尋（Layer 2 baseline）。"""
    query_lower = query.lower()
    scored: list[tuple[float, dict]] = []
    for qa in qas:
        score = 0.0
        if query_lower in qa.get("question", "").lower():
            score += 1.0
        if query_lower in qa.get("answer", "").lower():
            score += 0.5
        for kw in qa.get("keywords", []):
            if kw.lower() in query_lower or query_lower in kw.lower():
                score += 0.3
        if score > 0:
            scored.append((score, qa))
    scored.sort(key=lambda x: x[0], reverse=True)
    results = [qa for _, qa in scored[:top_k]]
    return [
        {
            "id": qa.get("stable_id", qa.get("id", "")),
            "category": qa.get("category", ""),
            "question": qa.get("question", "")[:120],
        }
        for qa in results
    ]


def _keyword_search_with_synonyms(
    query: str, qas: list[dict], top_k: int, synonyms: dict[str, list[str]]
) -> list[dict]:
    """同義詞展開後的關鍵字搜尋（Layer 3 comparison）。"""
    query_lower = query.lower()
    # 展開 query 中出現的術語的同義詞
    expanded_terms: set[str] = set(query_lower.split())
    for term, syn_list in synonyms.items():
        term_l = term.lower()
        # 正向：術語出現在 query
        if term_l in query_lower:
            expanded_terms.add(term_l)
            expanded_terms.update(s.lower() for s in syn_list)
        # 反向：任何同義詞出現在 query
        for syn in syn_list:
            if syn.lower() in query_lower:
                expanded_terms.add(term_l)
                expanded_terms.update(s.lower() for s in syn_list)
                break

    expanded_query = " ".join(expanded_terms)
    return _keyword_search(expanded_query, qas, top_k)


# ── Layer 2 Evaluators — IR 標準指標 ────────────────────────────────────────


def precision_evaluator(output: list[dict], target: dict) -> float:
    """Precision@K：top-K 中有幾個 category 命中。"""
    expected_cats = set(target.get("expected_categories", []))
    if not output:
        return 0.0
    relevant = sum(1 for qa in output if qa.get("category", "") in expected_cats)
    return relevant / len(output)


def recall_evaluator(output: list[dict], target: dict) -> float:
    """Recall@K：期望的 categories 有幾個被覆蓋。"""
    expected_cats = set(target.get("expected_categories", []))
    if not expected_cats:
        return 1.0
    retrieved_cats = {qa.get("category", "") for qa in output}
    return len(retrieved_cats & expected_cats) / len(expected_cats)


def f1_evaluator(output: list[dict], target: dict) -> float:
    """F1@K：Precision 與 Recall 的調和平均。"""
    p = precision_evaluator(output, target)
    r = recall_evaluator(output, target)
    if p + r == 0:
        return 0.0
    return 2 * p * r / (p + r)


def hit_rate_evaluator(output: list[dict], target: dict) -> float:
    """Hit Rate：top-K 中是否至少有一筆期望 category（0 或 1）。"""
    expected_cats = set(target.get("expected_categories", []))
    for qa in output:
        if qa.get("category", "") in expected_cats:
            return 1.0
    return 0.0


def mrr_evaluator(output: list[dict], target: dict) -> float:
    """MRR：第一筆命中的排名倒數（Mean Reciprocal Rank）。"""
    expected_cats = set(target.get("expected_categories", []))
    for rank, qa in enumerate(output, start=1):
        if qa.get("category", "") in expected_cats:
            return 1.0 / rank
    return 0.0


def ndcg_at_k_evaluator(output: list[dict], target: dict) -> float:
    """NDCG@K：考慮排名位置的累積相關度（Jarvelin & Kekalainen, 2002）。

    graded relevance: 命中 expected_category = 1.0, 否則 = 0.0
    DCG = Σ rel_i / log2(i+1)
    IDCG = 最佳排序下的 DCG（所有命中集中在最前面）
    """
    expected_cats = set(target.get("expected_categories", []))
    if not expected_cats or not output:
        return 1.0 if not expected_cats else 0.0

    # 每個 expected_category 只計算第一次命中，避免同一 category 多筆重複計分
    found_cats: set[str] = set()
    dcg = 0.0
    for rank, qa in enumerate(output, start=1):
        cat = qa.get("category", "")
        if cat in expected_cats and cat not in found_cats:
            dcg += 1.0 / math.log2(rank + 1)
            found_cats.add(cat)
    # IDCG：假設最多 len(expected_cats) 個命中，全部在最前面
    n_perfect = min(len(expected_cats), len(output))
    idcg = sum(1.0 / math.log2(i + 2) for i in range(n_perfect))

    if idcg == 0:
        return 0.0
    return dcg / idcg


def top1_category_match_evaluator(output: list[dict], target: dict) -> float:
    """Top-1 Category Match：第一筆結果的 category 是否在期望分類中。"""
    expected_cats = set(target.get("expected_categories", []))
    if not output:
        return 0.0
    return 1.0 if output[0].get("category", "") in expected_cats else 0.0


def top5_category_coverage_evaluator(output: list[dict], target: dict) -> float:
    """Top-5 Category Coverage：top-5 覆蓋了多少 expected_categories（等同 Recall@K）。

    語意上與 recall_evaluator 相同，但在 Laminar 中以更清楚的名稱呈現。
    """
    return recall_evaluator(output, target)


# ── Layer 3 Evaluators — 同義詞 + 增強指標 ──────────────────────────────────


def synonym_coverage_evaluator(output: list[dict], target: dict) -> float:
    """Synonym Coverage：expected_keywords 有多少比例有 synonym 覆蓋。

    衡量同義詞詞典對本查詢的覆蓋程度——若覆蓋率低，
    表示該查詢的關鍵字擴充空間仍不足。
    """
    expected_kws = target.get("expected_keywords", [])
    if not expected_kws:
        return 1.0
    synonyms = _load_synonyms()
    # 建立所有 synonym 術語集合（key + values）
    all_syn_terms: set[str] = set()
    for key, vals in synonyms.items():
        all_syn_terms.add(key.lower())
        for v in vals:
            all_syn_terms.add(v.lower())
    covered = sum(1 for kw in expected_kws if kw.lower() in all_syn_terms)
    return covered / len(expected_kws)


def kw_hit_rate_with_synonyms_evaluator(output: list[dict], target: dict) -> float:
    """KW Hit Rate with Synonyms：使用同義詞展開後是否命中（與 hit_rate 比較）。

    在 retrieval-enhancement group 中，executor 已改為 synonym-expanded 版本，
    因此直接複用 hit_rate_evaluator 邏輯即可衡量 synonym 擴充後的命中率。
    """
    return hit_rate_evaluator(output, target)


def freshness_rank_quality_evaluator(output: list[dict], target: dict) -> float:
    """Freshness Rank Quality：top-3 結果中是否沒有時效性差的非常綠 Q&A。

    檢查 top-3 結果中，非 evergreen 且 freshness_score < 0.7 的 Q&A 數量。
    越少代表舊文件沒有擠掉新文件，時效性排名品質越好。
    無 enrichment 資料時（freshness_score 缺失）視為時效良好，回傳 1.0。
    """
    if not output:
        return 1.0
    top3 = output[:3]
    stale_in_top3 = 0
    for qa in top3:
        enrichment = qa.get("_enrichment") or {}
        freshness = float(enrichment.get("freshness_score", 1.0))
        evergreen = qa.get("evergreen", True)
        if not evergreen and freshness < 0.7:
            stale_in_top3 += 1
    return 1.0 - (stale_in_top3 / 3.0)


# ── Report Quality Evaluators ────────────────────────────────────────────────


def _load_report_eval_cases() -> list[dict]:
    """載入 output/report_*.md 作為 report eval 測試集。"""
    import re
    report_files = sorted(REPORTS_DIR.glob("report_*.md"), reverse=True)
    if not report_files:
        logger.error("找不到任何 report_*.md 檔案，請先執行報告生成")
        sys.exit(1)

    cases = []
    for fp in report_files[:10]:  # 最多取最近 10 份
        content = fp.read_text(encoding="utf-8")
        # 嘗試從 Meta 區塊抽取日期
        date_match = re.search(r"生成日期：([\d/]+)", content)
        report_date = date_match.group(1) if date_match else fp.stem.replace("report_", "")
        cases.append({
            "data": {"content": content, "filename": fp.name, "date": report_date},
            "target": {"filename": fp.name},
        })

    logger.info("載入 %d 份報告作為 eval cases", len(cases))
    return cases


def report_executor(d: dict) -> str:
    """Report executor — 直接回傳已生成的報告內容（identity function）。"""
    return d["content"]


def report_section_coverage_evaluator(output: str, _target: dict) -> float:
    """Section Coverage：六個段落出現比例（0–1）。"""
    if not output:
        return 0.0
    found = sum(1 for marker in REPORT_SECTION_MARKERS if marker in output)
    return found / len(REPORT_SECTION_MARKERS)


def report_kb_links_evaluator(output: str, _target: dict) -> float:
    """KB Links：報告中是否含知識庫連結（0 or 1）。"""
    if not output:
        return 0.0
    return 1.0 if KB_LINK_PATTERN in output else 0.0


def report_research_cited_evaluator(output: str, _target: dict) -> float:
    """Research Cited：是否引用業界研究關鍵字（0 or 1）。"""
    if not output:
        return 0.0
    return 1.0 if any(kw in output for kw in REPORT_RESEARCH_KEYWORDS) else 0.0


def report_overall_evaluator(output: str, target: dict) -> float:
    """Overall：三個維度平均分數。"""
    sc = report_section_coverage_evaluator(output, target)
    kb = report_kb_links_evaluator(output, target)
    rc = report_research_cited_evaluator(output, target)
    return (sc + kb + rc) / 3


# ── Main ────────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(description="Laminar 正式 Eval Run（v2.13，4 層框架）")
    parser.add_argument(
        "--mode",
        default="retrieval",
        choices=["retrieval", "report"],
        help=(
            "評估模式（預設 'retrieval'）。\n"
            "retrieval: IR 標準指標評估（需要 golden_retrieval.json）\n"
            "report: 報告品質評估（需要 output/report_*.md）"
        ),
    )
    parser.add_argument("--top-k", type=int, default=5, help="Retrieval top-K（僅 retrieval 模式）")
    parser.add_argument(
        "--group",
        default=DEFAULT_GROUP,
        choices=["retrieval-eval", "retrieval-enhancement"],
        help=(
            f"Laminar group name（預設 {DEFAULT_GROUP!r}，僅 retrieval 模式）。\n"
            "retrieval-eval: Layer 2 IR 指標（8 個 evaluators）\n"
            "retrieval-enhancement: Layer 3 synonym+freshness 指標（3 個 evaluators）"
        ),
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    try:
        from lmnr import evaluate  # type: ignore[import]
    except ImportError:
        logger.error("lmnr 未安裝，請執行：pip install lmnr")
        sys.exit(1)

    init_laminar()

    # ── Report mode ─────────────────────────────────────────────────────────
    if args.mode == "report":
        report_cases = _load_report_eval_cases()
        report_group = "report-quality-eval"

        logger.info(
            "開始 Laminar report eval run，%d cases，group=%r",
            len(report_cases), report_group,
        )

        evaluate(
            data=report_cases,
            executor=report_executor,
            evaluators={
                "section_coverage": report_section_coverage_evaluator,
                "kb_links": report_kb_links_evaluator,
                "research_cited": report_research_cited_evaluator,
                "overall": report_overall_evaluator,
            },
            group_name=report_group,
            concurrency_limit=1,
        )

        logger.info("Report eval run 完成，請至 Laminar Dashboard → Evaluations → %r 查看結果", report_group)
        return

    # ── Retrieval mode ───────────────────────────────────────────────────────
    if not GOLDEN_RETRIEVAL_PATH.exists():
        logger.error("golden_retrieval.json 不存在：%s", GOLDEN_RETRIEVAL_PATH)
        sys.exit(1)

    golden_cases = json.loads(GOLDEN_RETRIEVAL_PATH.read_text(encoding="utf-8"))
    if not isinstance(golden_cases, list) or not golden_cases:
        logger.error("golden_retrieval.json 應為非空 JSON array")
        sys.exit(1)

    qas = _load_qas()
    top_k = args.top_k

    logger.info(
        "開始 Laminar eval run，%d cases，top-k=%d，group=%r",
        len(golden_cases), top_k, args.group,
    )

    eval_data = [
        {"data": {"query": c["query"], "top_k": top_k}, "target": c}
        for c in golden_cases
    ]
    # Padding workaround — Laminar SDK span flush bug：
    # 最後 2 筆 OTel span 有時在 shutdown() 前來不及 flush，
    # 補 2 個虛擬 items 確保真正的 golden cases 不在末尾被截斷。
    _padding_target = {"expected_categories": ["__padding__"], "expected_keywords": []}
    eval_data.extend([
        {"data": {"query": "__padding__", "top_k": top_k}, "target": _padding_target},
        {"data": {"query": "__padding__", "top_k": top_k}, "target": _padding_target},
    ])

    if args.group == "retrieval-enhancement":
        synonyms = _load_synonyms()
        logger.info("載入同義詞詞典：%d 個術語", len(synonyms))

        def safe_synonym_executor(d: dict) -> list[dict]:
            try:
                return _keyword_search_with_synonyms(
                    d["query"], qas, d["top_k"], synonyms
                )
            except Exception as exc:
                logger.error("synonym executor 失敗 query=%r: %s", d.get("query"), exc)
                return []

        evaluate(
            data=eval_data,
            executor=safe_synonym_executor,
            evaluators={
                "kw_hit_rate_with_synonyms": kw_hit_rate_with_synonyms_evaluator,
                "synonym_coverage": synonym_coverage_evaluator,
                "freshness_rank_quality": freshness_rank_quality_evaluator,
            },
            group_name=args.group,
            concurrency_limit=1,
        )

    else:
        # retrieval-eval（預設）— Layer 2 完整 IR 指標套件
        def safe_executor(d: dict) -> list[dict]:
            try:
                return _keyword_search(d["query"], qas, d["top_k"])
            except Exception as exc:
                logger.error("executor 失敗 query=%r: %s", d.get("query"), exc)
                return []

        evaluate(
            data=eval_data,
            executor=safe_executor,
            evaluators={
                "precision": precision_evaluator,
                "recall": recall_evaluator,
                "f1": f1_evaluator,
                "hit_rate": hit_rate_evaluator,
                "mrr": mrr_evaluator,
                "ndcg": ndcg_at_k_evaluator,
                "top1_category_match": top1_category_match_evaluator,
                "top5_category_coverage": top5_category_coverage_evaluator,
            },
            group_name=args.group,
            concurrency_limit=1,
        )

    logger.info("Eval run 完成，請至 Laminar Dashboard 查看結果（group=%r）", args.group)


if __name__ == "__main__":
    main()
