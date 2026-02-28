#!/usr/bin/env python3
"""
Provider 輸出比較評估工具

功能：
- 對同一 prompt + 數據，比較不同 AI provider 輸出的洞察品質
- 使用 LLM-as-Judge 評估三個維度（grounding、actionability、relevance）
- 同時檢查 required_topics 覆蓋率（字串匹配）
- 產出 Markdown 比較表 output/provider_comparison_<date>.md

用法：
    # 自動掃描 output/provider_*.md
    python scripts/compare_providers.py

    # 指定特定檔案
    python scripts/compare_providers.py \\
        --files output/provider_chatgpt_gpt52_20260228.md \\
                output/provider_gemini_research_20260228.md \\
                output/provider_claude_sonnet46_20260228.md

    # 指定 golden case 檔案
    python scripts/compare_providers.py --golden eval/golden_seo_analysis.json

    # 使用特定 judge model
    python scripts/compare_providers.py --judge-model gpt-5-mini
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
from openai import OpenAI
from utils.observability import flush_laminar, init_laminar, observe


# ──────────────────────────────────────────────────────
# 常數
# ──────────────────────────────────────────────────────

DEFAULT_GOLDEN_PATH = "eval/golden_seo_analysis.json"
DEFAULT_OUTPUT_DIR = "output"

JUDGE_SYSTEM_PROMPT = """\
你是 SEO 分析報告品質評審員。
評估分析報告的三個維度，每個維度給 1~5 分：

1. grounding（數據接地性）：所有提到的數字、百分比、趨勢是否忠實反映原始數據？有無捏造或誇大數字？
   - 5 分：所有數字均可在數據中找到，無誇大
   - 3 分：大部分正確，少數輕微誇大或省略
   - 1 分：存在與原始數據不符的數字或結論

2. actionability（可執行性）：提出的建議是否具體可執行？是否有明確的行動步驟？
   - 5 分：每個建議都有明確的行動步驟（如「拉出 CTR 跌幅 > 15% 且曝光 > 10 萬的 query 清單」）
   - 3 分：部分建議具體，部分停留在方向層面
   - 1 分：全為缺乏操作性的空泛建議

3. relevance（相關性與聚焦度）：分析是否緊扣 SEO 診斷主題？是否偏題至無關話題？
   - 5 分：完全聚焦在 SEO 診斷，每個洞察都有明確的 SEO 邏輯
   - 3 分：主要聚焦，但有部分不必要的離題或背景填充
   - 1 分：大量篇幅偏題至不直接相關的主題

每個維度的 reason 欄位必須填寫（不得為空字串），用 1–3 句話說明評分理由，引用報告中的具體例子。
只回答 JSON 格式。\
"""


# ──────────────────────────────────────────────────────
# 工具函式
# ──────────────────────────────────────────────────────

def _client(judge_model: str | None = None) -> tuple[OpenAI, str]:
    """回傳 (OpenAI client, model_name)"""
    model = judge_model or getattr(config, "EVAL_JUDGE_MODEL", "gpt-5-mini")
    return OpenAI(api_key=config.OPENAI_API_KEY), model


def _provider_label(path: Path) -> str:
    """從檔名提取 provider 標籤，例如 provider_chatgpt_gpt52_20260228 → chatgpt_gpt52"""
    name = path.stem  # provider_chatgpt_gpt52_20260228
    parts = name.split("_")
    # 移除首個 "provider" 和最後的日期（8 位數字）
    inner = [p for p in parts[1:] if not (len(p) == 8 and p.isdigit())]
    return "_".join(inner) if inner else name


def _check_required_topics(
    content: str,
    topics: list[str],
    aliases: dict[str, list[str]] | None = None,
) -> dict:
    """
    檢查 required_topics 在 content 中的覆蓋率。
    aliases：{topic: [alias1, alias2, ...]}，命中任一 alias 即視為覆蓋。
    """
    content_lower = content.lower()
    aliases = aliases or {}
    hits = []
    missed = []
    for t in topics:
        candidates = [t] + aliases.get(t, [])
        if any(c.lower() in content_lower for c in candidates):
            hits.append(t)
        else:
            missed.append(t)
    coverage = len(hits) / len(topics) if topics else 1.0
    return {
        "coverage": round(coverage, 2),
        "hits": hits,
        "missed": missed,
    }


@observe(name="provider_llm_judge")
def _llm_judge(
    content: str,
    golden_case: dict,
    client: OpenAI,
    model: str,
) -> dict:
    """用 LLM 評審單份 provider 報告，回傳三維度分數。"""
    data_snapshot = golden_case.get("data_snapshot", "")
    description = golden_case.get("description", "")
    criteria = golden_case.get("evaluation_criteria", {})

    # 評估準則補充說明
    criteria_note = ""
    if criteria:
        g = criteria.get("grounding", "")
        a = criteria.get("actionability", "")
        r = criteria.get("relevance", "")
        criteria_note = (
            f"\n\n評估準則細節：\n"
            f"- grounding：{g}\n"
            f"- actionability：{a}\n"
            f"- relevance：{r}"
        )

    user_msg = (
        f"任務說明：{description}\n"
        f"原始數據快照：{data_snapshot}"
        f"{criteria_note}\n\n"
        f"--- 待評估的分析報告（前 5000 字）---\n{content[:5000]}"
    )

    last_error: str = "未知錯誤"
    for attempt in range(2):  # 最多重試 1 次（推理模型偶爾耗盡 completion tokens）
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
                    {"role": "user", "content": user_msg},
                ],
                # NOTE: 不使用 response_format 約束，推理模型（reasoning tokens）在
                # json_schema / json_object 模式下會回傳空 content；直接解析文字 JSON 即可
                max_completion_tokens=4096,
            )
            raw = resp.choices[0].message.content
            if not raw or not raw.strip():
                last_error = "LLM 回傳空內容"
                if attempt == 0:
                    time.sleep(1)  # 短暫等待後重試
                    continue
                break
            # 支援模型將 JSON 包在 markdown code block 中的情況
            text = raw.strip()
            if text.startswith("```"):
                code_lines = text.splitlines()
                text = "\n".join(
                    line for line in code_lines
                    if not line.strip().startswith("```")
                ).strip()
            return json.loads(text)
        except Exception as exc:
            last_error = str(exc)
            if attempt == 0:
                time.sleep(1)
                continue
            break
    return {"error": f"{last_error}（重試後仍然）"}


# ──────────────────────────────────────────────────────
# 核心評估
# ──────────────────────────────────────────────────────

@observe(name="compare_evaluate_providers")
def evaluate_providers(
    provider_files: list[Path],
    golden_case: dict,
    judge_model: str | None = None,
) -> list[dict]:
    """
    對每個 provider 檔案執行評估：
    1. required_topics 覆蓋率（字串匹配，免費）
    2. LLM-as-Judge（grounding + actionability + relevance）

    回傳每個 provider 的評估結果清單。
    """
    client, model = _client(judge_model)
    required_topics = golden_case.get("required_topics", [])
    results = []

    for path in provider_files:
        label = _provider_label(path)
        print(f"  評估: {label} ...")

        content = path.read_text(encoding="utf-8")

        # Step 1: required_topics 覆蓋率
        aliases = golden_case.get("topic_aliases", {})
        topic_check = _check_required_topics(content, required_topics, aliases)

        # Step 2: LLM-as-Judge
        llm_scores = _llm_judge(content, golden_case, client, model)

        entry: dict = {
            "provider": label,
            "file": str(path),
            "char_count": len(content),
            "topic_coverage": topic_check["coverage"],
            "topics_hit": topic_check["hits"],
            "topics_missed": topic_check["missed"],
        }

        if "error" in llm_scores:
            print(f"    ⚠️  LLM judge 錯誤: {llm_scores['error']}")
            entry["error"] = llm_scores["error"]
            entry["grounding"] = None
            entry["actionability"] = None
            entry["relevance"] = None
            entry["avg_score"] = None
            entry["overall_comment"] = ""
        else:
            g = llm_scores.get("grounding", {})
            a = llm_scores.get("actionability", {})
            r = llm_scores.get("relevance", {})
            scores = [
                s for s in [g.get("score"), a.get("score"), r.get("score")]
                if isinstance(s, (int, float))
            ]
            avg = round(sum(scores) / len(scores), 2) if scores else None
            entry.update({
                "grounding": g,
                "actionability": a,
                "relevance": r,
                "avg_score": avg,
                "overall_comment": llm_scores.get("overall_comment", ""),
            })

        results.append(entry)
        time.sleep(0.5)

    return results


# ──────────────────────────────────────────────────────
# 報告生成
# ──────────────────────────────────────────────────────

def _score_cell(dim: dict | None) -> str:
    if dim is None:
        return "N/A"
    if isinstance(dim, dict) and "score" in dim:
        return str(dim["score"])
    return "N/A"


def generate_comparison_report(
    results: list[dict],
    golden_case: dict,
    judge_model: str,
) -> str:
    """產生 Markdown 格式的比較報告"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    case_id = golden_case.get("id", "unknown")
    description = golden_case.get("description", "")
    data_snapshot = golden_case.get("data_snapshot", "")
    required_topics = golden_case.get("required_topics", [])

    lines = [
        f"# AI Provider 輸出品質比較報告\n",
        f"- 測試案例：{case_id}",
        f"- 案例說明：{description}",
        f"- 數據快照：{data_snapshot}",
        f"- Judge 模型：{judge_model}",
        f"- 評估日期：{now}",
        f"- 必要主題（{len(required_topics)}）：{', '.join(required_topics)}",
        "",
    ]

    # ── 總覽表 ──
    lines.append("## 綜合評分總覽\n")
    lines.append("| Provider | 主題覆蓋率 | Grounding | Actionability | Relevance | 平均分 |")
    lines.append("|----------|-----------|-----------|---------------|-----------|--------|")

    # 依平均分排序（None 排最後）
    sorted_results = sorted(
        results,
        key=lambda r: r.get("avg_score") or 0,
        reverse=True,
    )

    for r in sorted_results:
        topic_pct = f"{r['topic_coverage']:.0%}"
        g = _score_cell(r.get("grounding"))
        a = _score_cell(r.get("actionability"))
        rv = _score_cell(r.get("relevance"))
        avg = r.get("avg_score")
        avg_str = f"**{avg}**" if avg and avg >= 4.0 else (str(avg) if avg else "N/A")
        lines.append(
            f"| {r['provider']} | {topic_pct} | {g} | {a} | {rv} | {avg_str} |"
        )

    lines.append("")

    # ── 各 provider 詳細說明 ──
    lines.append("## 各 Provider 詳細評鑑\n")

    for r in sorted_results:
        label = r["provider"]
        lines.append(f"### {label}\n")
        lines.append(f"- 字數：{r['char_count']:,} 字元")
        lines.append(f"- 主題覆蓋率：{r['topic_coverage']:.0%}")

        if r.get("topics_missed"):
            lines.append(f"- 缺少主題：{', '.join(r['topics_missed'])}")
        if r.get("topics_hit"):
            lines.append(f"- 覆蓋主題：{', '.join(r['topics_hit'])}")

        if r.get("error"):
            lines.append(f"- **錯誤**：{r['error']}")
        else:
            g = r.get("grounding") or {}
            a = r.get("actionability") or {}
            rv = r.get("relevance") or {}
            lines.append(f"\n**Grounding（{g.get('score', 'N/A')}/5）**：{g.get('reason', '')}")
            lines.append(f"\n**Actionability（{a.get('score', 'N/A')}/5）**：{a.get('reason', '')}")
            lines.append(f"\n**Relevance（{rv.get('score', 'N/A')}/5）**：{rv.get('reason', '')}")
            if r.get("overall_comment"):
                lines.append(f"\n**總體評語**：{r['overall_comment']}")

        lines.append("")

    # ── 結論 ──
    if sorted_results and sorted_results[0].get("avg_score"):
        winner = sorted_results[0]
        lines.append("## 結論\n")
        lines.append(
            f"在此次測試的 {len(results)} 個 provider 中，**{winner['provider']}** "
            f"以平均分 **{winner['avg_score']}/5** 表現最佳。"
        )

        # 列出各個 provider 最強的維度
        dim_labels = {
            "grounding": "Grounding",
            "actionability": "Actionability",
            "relevance": "Relevance",
        }
        lines.append("")
        lines.append("各維度最佳 provider：")
        for dim_key, dim_name in dim_labels.items():
            best_for_dim = max(
                (r for r in sorted_results if r.get(dim_key) and isinstance(r[dim_key], dict)),
                key=lambda r: r[dim_key].get("score", 0),
                default=None,
            )
            if best_for_dim:
                score = best_for_dim[dim_key]["score"]
                lines.append(f"- **{dim_name}**：{best_for_dim['provider']}（{score}/5）")

    return "\n".join(lines)


# ──────────────────────────────────────────────────────
# CLI 入口
# ──────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="比較多個 AI provider 的 SEO 分析輸出品質"
    )
    parser.add_argument(
        "--files",
        nargs="+",
        type=str,
        default=None,
        help="指定要比較的 provider 檔案（預設自動掃描 output/provider_*.md）",
    )
    parser.add_argument(
        "--golden",
        type=str,
        default=DEFAULT_GOLDEN_PATH,
        help=f"Golden case 檔案路徑（預設 {DEFAULT_GOLDEN_PATH}）",
    )
    parser.add_argument(
        "--case-id",
        type=str,
        default="",
        help="若 golden 檔案有多個 case，指定要用哪個 id（預設用第一個）",
    )
    parser.add_argument(
        "--judge-model",
        type=str,
        default="",
        help="LLM Judge 模型名稱（預設使用 config.EVAL_JUDGE_MODEL）",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="",
        help="輸出報告路徑（預設 output/provider_comparison_<date>.md）",
    )
    args = parser.parse_args()

    root = config.ROOT_DIR

    # ── 載入 golden case ──
    golden_path = Path(args.golden)
    if not golden_path.is_absolute():
        golden_path = root / golden_path
    if not golden_path.exists():
        print(f"❌ 找不到 golden 檔案：{golden_path}")
        sys.exit(1)

    golden_cases = json.loads(golden_path.read_text(encoding="utf-8"))
    if not golden_cases:
        print("❌ golden 檔案為空")
        sys.exit(1)

    if args.case_id:
        matching = [c for c in golden_cases if c.get("id") == args.case_id]
        if not matching:
            print(f"❌ 找不到 case_id={args.case_id}")
            sys.exit(1)
        golden_case = matching[0]
    else:
        golden_case = golden_cases[0]

    print(f"✅ 使用 golden case: {golden_case['id']}")
    print(f"   {golden_case.get('description', '')}")

    # ── 找出 provider 檔案 ──
    if args.files:
        # 建立新 list，避免在迭代過程中 mutation 原 list 造成跳過或取錯 index
        provider_files = [
            Path(f) if Path(f).is_absolute() else root / f
            for f in args.files
        ]
    else:
        output_dir = root / DEFAULT_OUTPUT_DIR
        provider_files = sorted(output_dir.glob("provider_*.md"))

    if not provider_files:
        print("❌ 找不到任何 provider 檔案（output/provider_*.md）")
        sys.exit(1)

    # 過濾掉不存在的檔案
    existing = [f for f in provider_files if f.exists()]
    if missing := [f for f in provider_files if not f.exists()]:
        print(f"⚠️  以下檔案不存在，已跳過：{[str(f) for f in missing]}")
    provider_files = existing

    print(f"\n📋 待比較 provider 數：{len(provider_files)}")
    for pf in provider_files:
        print(f"   - {pf.name}")

    # ── 執行評估 ──
    init_laminar()
    judge_model = args.judge_model or getattr(config, "EVAL_JUDGE_MODEL", "gpt-5-mini")
    print(f"\n🔍 開始評估（Judge: {judge_model}）...")
    try:
        results = evaluate_providers(provider_files, golden_case, judge_model)
    finally:
        flush_laminar()

    # ── 產出報告 ──
    report_md = generate_comparison_report(results, golden_case, judge_model)

    if args.output:
        out_path = Path(args.output)
        if not out_path.is_absolute():
            out_path = root / out_path
    else:
        today = datetime.now().strftime("%Y%m%d")
        out_path = root / DEFAULT_OUTPUT_DIR / f"comparison_report_{today}.md"

    out_path.write_text(report_md, encoding="utf-8")
    print(f"\n✅ 報告已儲存：{out_path.relative_to(root)}")

    # ── 印出總覽 ──
    print("\n" + "=" * 60)
    print("📊 比較結果總覽")
    print("=" * 60)
    sorted_results = sorted(
        results, key=lambda r: r.get("avg_score") or 0, reverse=True
    )
    header = f"{'Provider':<30} {'主題覆蓋':>8} {'Grnd':>6} {'Actn':>6} {'Rlvn':>6} {'Avg':>6}"
    print(header)
    print("-" * 60)
    for r in sorted_results:
        g = _score_cell(r.get("grounding"))
        a = _score_cell(r.get("actionability"))
        rv = _score_cell(r.get("relevance"))
        cov = f"{r['topic_coverage']:.0%}"
        avg = str(r.get("avg_score") or "N/A")
        print(f"{r['provider']:<30} {cov:>8} {g:>6} {a:>6} {rv:>6} {avg:>6}")


if __name__ == "__main__":
    main()
