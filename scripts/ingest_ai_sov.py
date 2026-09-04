"""
ingest_ai_sov.py — AI 答案 share of voice（SoV）週級量測（S6.2）

對 data/ai_sov_prompts.json 這份固定 panel 的每一條 prompt 問 LLM N 次，
解析回應裡的 citation，記錄 vocus.cc 有沒有被引用、排在第幾位，寫進
ai_sov_response。判讀一律走 migration 024 建的三個週級視圖，不查底表。

用法：
  python scripts/ingest_ai_sov.py                                  # dry-run（會真的呼叫 provider）
  python scripts/ingest_ai_sov.py --provider fake                  # 零成本跑通整條鏈
  python scripts/ingest_ai_sov.py --execute                        # 實際寫入
  python scripts/ingest_ai_sov.py --provider fake --max-prompts 3  # smoke（強制 dry-run）
  python scripts/ingest_ai_sov.py --verify                         # 讀回最新一週的摘要


═══ 這個指標的成熟度（讀之前必看）═══

⚠ **低成熟度指標，單次波動不可解讀。** 三個限制寫在 migration 024 的 catalog
註解裡（那裡才是查資料的人會看到的地方），這裡只重述判讀規則：

  - 只看週級趨勢，且需要 ≥4 週序列才談得上趨勢。
  - 下降時先看 ungrounded_ratio 有沒有同步上升（provider 端沒觸發檢索）。
  - 再用 ai_sov_weekly_domain 做**背離產業判別**：同類內容平台網域是不是
    同步下降。同步＝產業/provider 現象；只有 vocus.cc 掉＝站方獨立訊號。
    方法論出處：reports/2026-05-24-seo-weekly-report-20260522-indexing-recovery.md
    的「AI 引擎背離偵測法」。


═══ 設計決定 ═══

【1. 為什麼先做 OpenAI 一家】
不是因為它最重要，是因為它是目前唯一能用**單一 API 呼叫**同時拿到「答案」與
「這個答案引用了哪些 URL」的一家（Responses API 的 web_search 工具會把
citation 以 url_citation annotation 附在輸出上）。其他家要嘛沒有官方
citation 欄位、要嘛得靠爬使用者介面——那會把一個資料管線變成一個爬蟲
維護專案，而這個指標本身的成熟度還不值得那個成本。
provider 抽象（ai_sov_providers.Provider）已經把邊界劃好，加第二家是
新增一個類別，不動聚合與寫入。是否要加，列為待裁決項。

【2. 為什麼 N=3】
同一個 prompt 問兩次會得到不同的來源組合，這是取樣與檢索端的本質變異。
N 要大到能把「這個 prompt 對我們有沒有機會」與「這一次剛好沒抽到」分開，
又小到每週成本可接受。N=3 的比例只有 0/⅓/⅔/1 四種值——**逐 prompt 看確實太粗**，
但這個指標的判讀單位本來就不是單一 prompt，是 36 個 prompt 的平均：
36 × 3 = 108 個樣本，整體比例的解析度約 1 個百分點，夠用。
N=1 則完全分不開上述兩件事（單次結果就是最終結果）；N=5 讓成本多 67% 換來
整體解析度從 ~1% 到 ~0.8%，不划算。N 由 --repeats / AI_SOV_REPEATS 可調，
**改動它會改變週間可比性**，改了要在報告裡標明從哪一週開始換。

【3. 為什麼是週跑而不是日跑】
日跑的成本是週跑的 7 倍，而換到的解析度是零——這個指標的雜訊尺度大於它的
日間變化尺度（見 N=3 那段的解析度估算）。更實際的理由：日跑會誘使人去讀
單日數字，而單日數字在這裡沒有意義。頻率本身就是一道判讀紀律。

【4. 失敗一律不吞】
provider 呼叫失敗（重試耗盡）不會被記成「這次沒引用」——那會讓 API 故障
偽裝成可見度下降。失敗的 (prompt, repeat) 直接不產生列，計入 failures，
ingestion_run 標 failed，行程以非零碼結束，而且**跳過 sweep_stale**
（見 ai_sov_warehouse 設計決定 3：半套的 run 去掃過期列會刪掉好資料）。

【4b. Fatal 錯誤要整條 run 早停，不是每個 (prompt, repeat) 各自失敗】
決定 4 描述的是「單次呼叫失敗」的處理，前提是失敗彼此獨立（這次超時，
下次可能就好了）。但 ProviderFatalError（額度耗盡／認證失效）不是獨立
事件：一旦第一次遇到，之後 107 次呼叫必然是同一個結果。繼續照決定 4
的邏輯逐一呼叫、逐一記錄失敗，只是把「已知會失敗」的事實拖到跑完整個
panel 才被看見（實測：108 次呼叫、21 分鐘、0 列產出）。因此 run_panel
收到 ProviderFatalError 時立即回傳，不再呼叫 provider——failures 只會有
一筆，rows 保留中止前已成功累積的部分（若有）。下游 _persist 的語意
不變：只要 failures 非空就標 failed、跳過 sweep、非零碼結束。
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ai_sov_panel import PanelPrompt, load_panel, panel_target_domain  # noqa: E402
from ai_sov_providers import (  # noqa: E402
    FakeProvider,
    OpenAIProvider,
    Provider,
    ProviderAnswer,
    ProviderError,
    ProviderFatalError,
    first_target_rank,
    response_digest,
)
import ai_sov_warehouse as warehouse  # noqa: E402

from dotenv import load_dotenv  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

DEFAULT_REPEATS = 3
MAX_REPEATS = 10  # 超過這個值的成本與可比性風險都該先被人看一眼，不該只是打字打錯
DEFAULT_MODEL = "gpt-5.4"
DEFAULT_PROVIDER = "openai"


# ══════════════════════════════════════════════════════════════════════
# 純函式：一次回應 → 一列
# ══════════════════════════════════════════════════════════════════════

def build_row(prompt: PanelPrompt, repeat_idx: int, answer: ProviderAnswer, *,
              provider: str, model: str, week_start: date, run_at: datetime,
              target_domain: str) -> dict:
    """把一次 provider 回應轉成 ai_sov_response 的一列。

    欄位之間的一致性（grounding 對 citation_count、rank 對 cited、
    陣列長度對 citation_count）在 migration 024 有 CHECK 綁死，
    這裡算錯會直接撞牆而不是靜默寫進去——這是刻意的分工。
    """
    citations = answer.citations
    rank = first_target_rank(citations, target_domain)
    return {
        "week_start": week_start.isoformat(),
        "run_at": warehouse.iso_z(run_at),
        "provider": provider,
        "model": model,
        "prompt_id": prompt.id,
        "prompt_theme": prompt.theme,
        "repeat_idx": repeat_idx,
        "grounding": "grounded" if citations else "ungrounded",
        "cited": rank is not None,
        "citation_rank": rank,
        "citation_count": len(citations),
        "cited_urls": [c.url for c in citations],
        "cited_domains": [c.domain for c in citations],
        "response_chars": len(answer.text),
        "response_hash": response_digest(answer.text),
    }


def summarize(rows: list[dict]) -> dict:
    """本地重算週級摘要，供 log 與測試用。

    刻意與 migration 024 的 ai_sov_weekly 視圖用同一套定義（分母是 grounded、
    macro 是各 prompt 比例的平均、全 ungrounded 的 prompt 不參與 macro）——
    兩邊算出不同的數字時，是 SQL 或這裡其中一邊改了而另一邊沒跟上，
    測試會抓到（test_ingest_ai_sov.py 的 macro/pooled 對照）。
    """
    grounded_by_prompt: dict[str, int] = defaultdict(int)
    cited_by_prompt: dict[str, int] = defaultdict(int)
    for row in rows:
        if row["grounding"] == "grounded":
            grounded_by_prompt[row["prompt_id"]] += 1
            if row["cited"]:
                cited_by_prompt[row["prompt_id"]] += 1

    rates = [cited_by_prompt[pid] / n for pid, n in grounded_by_prompt.items() if n]
    grounded = sum(grounded_by_prompt.values())
    cited = sum(cited_by_prompt.values())
    return {
        "responses": len(rows),
        "grounded_responses": grounded,
        "cited_responses": cited,
        "prompts_with_grounded_answer": len(rates),
        "sov_pooled": (cited / grounded) if grounded else None,
        "sov_macro": (sum(rates) / len(rates)) if rates else None,
        "ungrounded_ratio": (1 - grounded / len(rows)) if rows else None,
    }


# ══════════════════════════════════════════════════════════════════════
# 執行 panel
# ══════════════════════════════════════════════════════════════════════

def run_panel(provider: Provider, prompts: tuple[PanelPrompt, ...], *, repeats: int,
              target_domain: str, week_start: date, run_at: datetime,
              ) -> tuple[list[dict], list[str]]:
    """對每條 prompt 問 repeats 次。回傳 (列, 失敗描述)。

    一般失敗（ProviderError）不產生列，記進 failures，繼續跑下一次呼叫
    （設計決定 4）。ProviderFatalError（額度耗盡／認證失效）不一樣：那個
    錯誤對後續呼叫必然重現，因此立即中止整條 run、不再呼叫 provider
    （設計決定 4b），rows/failures 保留中止前已累積的內容。
    """
    rows: list[dict] = []
    failures: list[str] = []
    for prompt in prompts:
        for repeat_idx in range(repeats):
            try:
                answer = provider.answer(prompt.prompt)
            except ProviderFatalError as exc:
                failures.append(f"{prompt.id}#{repeat_idx}: {exc}")
                logger.error("  %s repeat=%d 遇到不可重試錯誤，整條 run 立即中止（設計決定 4b）：%s",
                            prompt.id, repeat_idx, exc)
                return rows, failures
            except ProviderError as exc:
                failures.append(f"{prompt.id}#{repeat_idx}: {exc}")
                logger.error("  %s repeat=%d 失敗：%s", prompt.id, repeat_idx, exc)
                continue
            rows.append(build_row(
                prompt, repeat_idx, answer, provider=provider.name, model=provider.model,
                week_start=week_start, run_at=run_at, target_domain=target_domain,
            ))
    return rows, failures


def resolve_provider(name: str, model: str, target_domain: str) -> Provider:
    if name == "fake":
        return FakeProvider(model=model if model != DEFAULT_MODEL else "fake-1",
                            target_domain=target_domain)
    if name == "openai":
        return OpenAIProvider(api_key=os.environ.get("OPENAI_API_KEY", ""), model=model)
    raise ProviderError(f"未知的 provider：{name}")


def _log_summary(rows: list[dict], failures: list[str]) -> None:
    stats = summarize(rows)
    logger.info("  回應 %d 列（grounded %d、引用 %d）",
                stats["responses"], stats["grounded_responses"], stats["cited_responses"])
    for label in ("sov_macro", "sov_pooled", "ungrounded_ratio"):
        value = stats[label]
        logger.info("  %-18s %s", label, "n/a" if value is None else f"{value:.4f}")
    if failures:
        logger.error("  失敗 %d 次（不計入任何比例，見設計決定 4）", len(failures))


# ══════════════════════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════════════════════

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AI 答案 share of voice 週級量測")
    parser.add_argument("--execute", action="store_true", help="實際寫入 Supabase（預設 dry-run）")
    parser.add_argument("--provider", default=os.environ.get("AI_SOV_PROVIDER", DEFAULT_PROVIDER),
                        choices=["openai", "fake"])
    parser.add_argument("--model", default=os.environ.get("AI_SOV_MODEL", DEFAULT_MODEL))
    parser.add_argument("--repeats", type=int, default=int(os.environ.get("AI_SOV_REPEATS", DEFAULT_REPEATS)))
    parser.add_argument("--max-prompts", type=int, default=0,
                        help="只跑前 N 條 prompt（smoke 用）。會讓 panel 不完整，因此強制 dry-run")
    parser.add_argument("--verify", action="store_true", help="讀回最新一週的摘要，不呼叫 provider")
    return parser.parse_args()


def _validate_args(args: argparse.Namespace) -> None:
    if not 1 <= args.repeats <= MAX_REPEATS:
        raise SystemExit(f"--repeats 需在 1..{MAX_REPEATS}，實得 {args.repeats}")
    if args.max_prompts and args.execute:
        # 半套的 panel 寫進去會讓該週的分母與其他週不可比，而且沒有任何訊號。
        raise SystemExit("--max-prompts 只供 smoke 使用，不可與 --execute 併用")


def _verify() -> int:
    week = warehouse.latest_week_start()
    if week is None:
        logger.error("FAIL：ai_sov_response 是空的，管線從未成功寫入。")
        return 1
    rows = warehouse.select_all(
        f"/rest/v1/ai_sov_weekly?select=*&week_start=eq.{week.isoformat()}")
    logger.info("最新週桶 %s，聚合列 %d 筆", week.isoformat(), len(rows))
    for row in rows:
        logger.info("  %s/%s responses=%s grounded=%s sov_macro=%s ungrounded_ratio=%s",
                    row.get("provider"), row.get("model"), row.get("responses"),
                    row.get("grounded_responses"), row.get("sov_macro"), row.get("ungrounded_ratio"))
    return 0 if rows else 1


def _persist(rows: list[dict], failures: list[str], week_start: date, run_at: datetime) -> int:
    run_id = warehouse.start_run(
        datetime.combine(week_start, datetime.min.time(), tzinfo=timezone.utc),
        datetime.combine(week_start + timedelta(days=7), datetime.min.time(), tzinfo=timezone.utc),
    )
    succeeded, write_failed = warehouse.upsert_rows(rows, run_at)
    if failures or write_failed:
        warehouse.finish_run(run_id, "failed", succeeded)
        logger.error("寫入 %d 列，provider 失敗 %d 次、寫入失敗 %d 列；"
                     "跳過 sweep_stale（半套的 run 去掃過期列會刪掉好資料）",
                     succeeded, len(failures), write_failed)
        return 1
    warehouse.sweep_stale(week_start, run_at)
    warehouse.finish_run(run_id, "success", succeeded)
    logger.info("寫入 %d 列，ingestion_run 標記 success。", succeeded)
    return 0


def main() -> None:
    args = _parse_args()
    _validate_args(args)
    if args.verify:
        sys.exit(_verify())

    target_domain = panel_target_domain()
    prompts = load_panel()
    if args.max_prompts:
        prompts = prompts[: args.max_prompts]
        logger.warning("只跑前 %d 條 prompt（smoke 模式，強制 dry-run）", len(prompts))

    run_at = datetime.now(timezone.utc)
    week_start = warehouse.week_start_for(run_at)
    try:
        provider = resolve_provider(args.provider, args.model, target_domain)
    except ProviderError as exc:
        # 明確失敗，不靜默退回 FakeProvider——那會寫進一整週看起來正常、
        # 實際上完全捏造的資料，而且沒有任何訊號能事後分辨。
        raise SystemExit(f"無法建立 provider：{exc}") from exc
    logger.info("provider=%s model=%s prompts=%d repeats=%d week_start=%s",
                provider.name, provider.model, len(prompts), args.repeats, week_start.isoformat())

    rows, failures = run_panel(provider, prompts, repeats=args.repeats,
                               target_domain=target_domain, week_start=week_start, run_at=run_at)
    _log_summary(rows, failures)

    if not args.execute:
        logger.info("[DRY RUN] 未寫入任何資料；加 --execute 才會寫入 %d 列。", len(rows))
        sys.exit(1 if failures else 0)
    sys.exit(_persist(rows, failures, week_start, run_at))


if __name__ == "__main__":
    main()
