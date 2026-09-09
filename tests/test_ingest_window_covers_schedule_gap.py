"""回歸測試：抓取視窗必須大到讓相鄰兩次執行的覆蓋區間不留空洞。

背景（2026-09-10）：crawl-hourly 與 cwv-hourly 從每小時降頻到每 6 小時，
`--backfill-hours` 從 2 提高到 14。這條「視窗 × 頻率」的不變式在降頻之前
**沒有任何測試守著**——`--backfill-hours` 的值、cron 的頻率、以及品質 gate 的
新鮮度門檻是三個檔案裡的三個獨立數字，改其中一個而忘了另外兩個不會有任何東西變紅，
而代價是來源 Loki 只有 168h retention、沒有第二資料源，漏掉的小時**永久遺失**。

這一支就是那個缺席的測試。它鎖的是關係式，不是數字：

    W >= floor(2F + D) + 1

  W = --backfill-hours（單次抓取視窗，完整小時數）
  F = 排程間隔（由 workflow 的 cron 反推，不是抄常數）
  D = GitHub Actions schedule trigger 的超額延遲上限（實測 0.73h）

為什麼是 floor()+1 而不是連續的 2F+D：視窗端點是**截到整點**的。一次執行在 t
覆蓋 complete_hours(t, W) = [H(t)-W, H(t)-1]，下一次在 t' 不留空洞的條件是
H(t')-W <= H(t)，即 W >= H(t')-H(t)；而 H(t')-H(t) 在最壞的分鐘對齊下
（t 落在 :59、t' 落在下一格的 :00 剛過）可達 floor(t'-t)+1。
`test_discrete_bound_matches_brute_force_simulation` 用暴力模擬驗這條公式本身。

為什麼是 2F 而不是 F：要容忍**完整漏跑一次**而不需要人介入。只滿足連續性
（W >= floor(F+D)+1）的話，漏跑一次就留下永久空洞，得靠 watchdog 告警 +
手動 --backfill-until 補。降頻前的 F=1/W=2 正是只滿足連續性的設定。
"""
from __future__ import annotations

import math
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts import ingest_crawl_hourly as crawl  # noqa: E402
from scripts import ingest_cwv_hourly as cwv  # noqa: E402
from scripts.quality_gate_config import PIPELINES_BY_KEY  # noqa: E402

WORKFLOWS_DIR = Path(__file__).resolve().parent.parent / ".github" / "workflows"

# 被測的兩條管線：(workflow 檔名, 腳本模組, quality gate 的 pipeline key)
PIPELINES = [
    ("crawl-hourly.yml", crawl, "crawl_daily"),
    ("cwv-hourly.yml", cwv, "cwv_hourly_rum"),
]
PIPELINE_IDS = [name for name, _, _ in PIPELINES]


# ══════════════════════════════════════════════════════════════════════
# 從 workflow 反推排程，不抄常數
# ══════════════════════════════════════════════════════════════════════

def _read_workflow(name: str) -> str:
    return (WORKFLOWS_DIR / name).read_text(encoding="utf-8")


def _cron_fire_hours(workflow_name: str) -> list[int]:
    """回傳該 workflow 每天觸發的整點小時清單（由 cron 解析，去掉註解行）。

    只支援 `M H[,H...] * * *` 這一種形式——本 repo 的降頻管線都長這樣。
    有人改成 `*/6` 或多個 cron entry 時這裡會直接 fail，那是刻意的：
    新形式要先想清楚 F 怎麼算，不能默默沿用舊斷言。
    """
    text = _read_workflow(workflow_name)
    matches = [
        m for line in text.splitlines()
        if not line.lstrip().startswith("#")
        for m in re.findall(r"- cron:\s*['\"](\d+)\s+([\d,]+)\s+\*\s+\*\s+\*['\"]", line)
    ]
    assert len(matches) == 1, f"{workflow_name} 預期剛好一個 `M H,... * * *` cron，實際 {matches}"
    _minute, hours = matches[0]
    return sorted(int(h) for h in hours.split(","))


def _schedule_interval_hours(workflow_name: str) -> int:
    """排程間隔 F = 相鄰兩次觸發的最大間隔（含跨日繞回）。

    取**最大**而不是平均：不變式必須對最疏的那一段成立。
    """
    fire_hours = _cron_fire_hours(workflow_name)
    assert fire_hours, f"{workflow_name} 沒有解析到觸發小時"
    wrapped = fire_hours + [fire_hours[0] + 24]
    return max(b - a for a, b in zip(wrapped, wrapped[1:]))


def _workflow_backfill_default(workflow_name: str) -> int:
    """workflow 實際送給腳本的 --backfill-hours 預設值。

    刻意讀 `BACKFILL_HOURS: ${{ ... || 'N' }}` 那個 env 的 fallback，而不是讀
    workflow_dispatch input 的 `default:`——排程觸發時 inputs 是空的，真正生效的
    是 `||` 右邊那個值。這兩個數字不同步過（改了 input default 卻沒改 env）
    正是這條斷言要擋的東西。
    """
    text = _read_workflow(workflow_name)
    match = re.search(r"BACKFILL_HOURS:\s*\$\{\{[^}]*\|\|\s*'(\d+)'\s*\}\}", text)
    assert match, f"{workflow_name} 找不到 BACKFILL_HOURS 的 env fallback 值"
    return int(match.group(1))


def _required_window(interval_hours: float, excess_delay_hours: float,
                     *, tolerate_one_miss: bool = True) -> int:
    """W 的下限：floor(2F + D) + 1（容忍漏跑一次）或 floor(F + D) + 1（僅連續性）。"""
    span = (2 if tolerate_one_miss else 1) * interval_hours + excess_delay_hours
    return math.floor(span) + 1


# ══════════════════════════════════════════════════════════════════════
# 公式本身：用暴力模擬驗 floor()+1 這個離散上界是對的
# ══════════════════════════════════════════════════════════════════════

class TestDiscreteBound:
    """先證明公式，再拿公式去驗設定——否則只是把同一個假設抄兩遍。"""

    @pytest.mark.parametrize("interval", [1, 4, 6, 8, 11, 12])
    def test_discrete_bound_matches_brute_force_simulation(self, interval: int) -> None:
        """對所有分鐘對齊窮舉，最大的 H(t')-H(t) 應該剛好等於 floor(2F+D)+1。"""
        delay = crawl.SCHEDULE_EXCESS_DELAY_HOURS
        gap = timedelta(hours=2 * interval + delay)
        worst = 0
        for minute in range(60):
            start = datetime(2026, 9, 10, 12, minute, tzinfo=timezone.utc)
            spanned = (crawl.truncate_to_hour(start + gap)
                       - crawl.truncate_to_hour(start))
            worst = max(worst, int(spanned.total_seconds() // 3600))
        assert worst == _required_window(interval, delay), (
            f"F={interval}h：模擬出來的最壞跨度 {worst}h 與公式 "
            f"{_required_window(interval, delay)}h 不一致，公式該重推了。"
        )

    def test_continuous_form_undercounts_when_the_span_lands_on_a_whole_hour(self) -> None:
        """連續式 ceil(2F+D) 只在 2F+D 不是整數時才等於離散式，等於時會少算一小時。

        目前 D=0.73、F 是整數，所以 2F+D 永遠不是整數、兩式恰好同值——很容易
        以為可以互換。但 D 是一個**實測值**，下次重新量測若得到 1.0 這種整數
        （或有人把 F 改成 0.5h），ceil 就會少算一小時而 floor()+1 不會。
        少算一小時的後果是每次排程都在視窗邊界留一個空洞，而且不會有錯誤訊號。
        """
        delay_landing_on_whole_hour = 1.0
        for interval in (4, 6, 8):
            span = 2 * interval + delay_landing_on_whole_hour
            assert span == int(span), "這個案例要的就是 2F+D 剛好是整數"
            assert _required_window(interval, delay_landing_on_whole_hour) == math.ceil(span) + 1, (
                "2F+D 是整數時，離散式應該比 ceil 多一小時"
            )

        # 而在目前的實測 D 之下，兩式同值——留下這條讓人知道現況不是巧合而是已驗過的。
        delay = crawl.SCHEDULE_EXCESS_DELAY_HOURS
        assert delay != int(delay), "D 若被改成整數，上面那個少算一小時的情境就會生效"
        assert all(
            math.ceil(2 * f + delay) == _required_window(f, delay)
            for f in range(1, 13)
        )


# ══════════════════════════════════════════════════════════════════════
# 主不變式
# ══════════════════════════════════════════════════════════════════════

class TestWindowCoversScheduleGap:

    @pytest.mark.parametrize("workflow,module,_key", PIPELINES, ids=PIPELINE_IDS)
    def test_window_tolerates_one_completely_missed_run(
        self, workflow: str, module, _key: str
    ) -> None:
        interval = _schedule_interval_hours(workflow)
        window = _workflow_backfill_default(workflow)
        required = _required_window(interval, module.SCHEDULE_EXCESS_DELAY_HOURS)
        assert window >= required, (
            f"{workflow}：排程每 {interval}h 一次，但 --backfill-hours 只有 {window}h。"
            f"完全漏跑一次之後下一輪補不回缺口（需要 >= {required}h）——"
            f"來源 Loki 只有 {module.LOKI_RETENTION_HOURS}h retention 且無第二資料源，"
            "這種空洞是永久的。"
        )

    @pytest.mark.parametrize("workflow,module,_key", PIPELINES, ids=PIPELINE_IDS)
    def test_window_is_within_the_scripts_hard_cap(
        self, workflow: str, module, _key: str
    ) -> None:
        """視窗不能超過腳本自己的跨度上限，否則排程每次都會 exit 2。"""
        window = _workflow_backfill_default(workflow)
        assert window <= module.MAX_BACKFILL_HOURS, (
            f"{workflow} 送 --backfill-hours {window}，超過 "
            f"{module.__name__}.MAX_BACKFILL_HOURS={module.MAX_BACKFILL_HOURS}，"
            "resolve_hours() 會直接 ValueError。"
        )

    @pytest.mark.parametrize("workflow,module,_key", PIPELINES, ids=PIPELINE_IDS)
    def test_simulated_runs_leave_no_hole_even_with_a_missed_run(
        self, workflow: str, module, _key: str
    ) -> None:
        """端到端模擬：每輪吃滿超額延遲，且週期性完全漏跑一次，覆蓋仍必須連續。

        直接呼叫 production 的 complete_hours()，不重寫一份視窗計算——
        重寫的話這個測試驗的是測試自己的假設，不是那支程式。
        """
        interval = _schedule_interval_hours(workflow)
        window = _workflow_backfill_default(workflow)
        step = timedelta(hours=interval + module.SCHEDULE_EXCESS_DELAY_HOURS)

        moment = datetime(2026, 9, 10, 0, 5, tzinfo=timezone.utc)
        newest_covered: datetime | None = None
        holes: list[datetime] = []
        for index in range(200):
            if index % 7 == 3:          # 每 7 輪整個漏跑一次
                moment += step
                continue
            hours = module.complete_hours(moment, window)
            if newest_covered is not None and hours[0] > newest_covered + timedelta(hours=1):
                holes.append(newest_covered + timedelta(hours=1))
            newest_covered = max(newest_covered or hours[-1], hours[-1])
            moment += step

        assert not holes, (
            f"{workflow}：模擬 200 輪（每 7 輪漏跑一次、每輪吃滿 "
            f"{module.SCHEDULE_EXCESS_DELAY_HOURS}h 超額延遲）出現 {len(holes)} 個空洞，"
            f"最早在 {holes[0].isoformat()}。"
        )

    @pytest.mark.parametrize("workflow,module,_key", PIPELINES, ids=PIPELINE_IDS)
    def test_script_constants_agree_with_the_workflow(
        self, workflow: str, module, _key: str
    ) -> None:
        """腳本裡的 F 與預設視窗必須跟 workflow 對得上。

        這兩個數字分屬 .py 與 .yml，沒有這條斷言就會各自漂移——而新鮮度門檻是
        從腳本的 SCHEDULE_INTERVAL_HOURS 推出來的，漂了會在資料健康時誤報。
        """
        assert module.SCHEDULE_INTERVAL_HOURS == _schedule_interval_hours(workflow), (
            f"{module.__name__}.SCHEDULE_INTERVAL_HOURS="
            f"{module.SCHEDULE_INTERVAL_HOURS} 與 {workflow} 的 cron 反推值不符。"
        )
        assert module.DEFAULT_LOOKBACK_HOURS == _workflow_backfill_default(workflow), (
            f"{module.__name__}.DEFAULT_LOOKBACK_HOURS="
            f"{module.DEFAULT_LOOKBACK_HOURS} 與 {workflow} 送的 "
            f"BACKFILL_HOURS 預設值不符。"
        )


# ══════════════════════════════════════════════════════════════════════
# 品質 gate 的門檻也綁著頻率
# ══════════════════════════════════════════════════════════════════════

class TestQualityGateThresholdsTrackTheSchedule:

    @pytest.mark.parametrize("workflow,module,key", PIPELINES, ids=PIPELINE_IDS)
    def test_freshness_threshold_covers_the_worst_case_age(
        self, workflow: str, module, key: str
    ) -> None:
        """最壞 age = 桶寬(1h) + 執行落點(1h) + F + D + L。

        前兩項與排程週期無關、常被漏算——「排程週期 × N」這個公式就是漏了它們，
        在資料健康時誤報（見 ingest_gsc_search_analytics.py 同名常數的註解）。
        """
        worst_case = (
            1 + 1
            + module.SCHEDULE_INTERVAL_HOURS
            + module.SCHEDULE_EXCESS_DELAY_HOURS
            + module.WRITE_LAG_HOURS
        )
        pipeline = PIPELINES_BY_KEY[key]
        assert pipeline.max_age_hours >= worst_case, (
            f"{key}: max_age_hours={pipeline.max_age_hours}h 蓋不住 {worst_case:.2f}h。"
        )
        assert module.FRESHNESS_MAX_AGE_HOURS >= worst_case, (
            f"{module.__name__}.FRESHNESS_MAX_AGE_HOURS="
            f"{module.FRESHNESS_MAX_AGE_HOURS}h 蓋不住 {worst_case:.2f}h。"
        )

    @pytest.mark.parametrize("workflow,module,key", PIPELINES, ids=PIPELINE_IDS)
    def test_lag_buffer_covers_the_wait_for_the_next_run(
        self, workflow: str, module, key: str
    ) -> None:
        """lag_buffer 的語意是「桶關閉後容忍多久沒資料」。

        桶 [T, T+1h) 在 T+1h 關閉，最早由 t >= T+1h 的那次執行寫入；
        從任一時刻起算下一次觸發最遠 F + D，再加寫入延遲 L。
        """
        required = (module.SCHEDULE_INTERVAL_HOURS
                    + module.SCHEDULE_EXCESS_DELAY_HOURS
                    + module.WRITE_LAG_HOURS)
        pipeline = PIPELINES_BY_KEY[key]
        assert pipeline.lag_buffer_hours >= required, (
            f"{key}: lag_buffer_hours={pipeline.lag_buffer_hours}h < {required:.2f}h，"
            "最近幾個桶會在下一輪還沒跑到時就被判成空段（健康資料誤報）。"
        )

    @pytest.mark.parametrize("workflow,module,key", PIPELINES, ids=PIPELINE_IDS)
    def test_gap_window_still_leaves_a_day_of_buckets_to_check(
        self, workflow: str, module, key: str
    ) -> None:
        """實際被檢查的是 [now-gap_window, now-lag_buffer]，lag_buffer 變大會把它吃掉。"""
        pipeline = PIPELINES_BY_KEY[key]
        checked_span = pipeline.gap_window_hours - pipeline.lag_buffer_hours
        assert checked_span >= 20, (
            f"{key}: gap_window({pipeline.gap_window_hours}h) − "
            f"lag_buffer({pipeline.lag_buffer_hours}h) = {checked_span}h，"
            "空段檢查的有效跨度不到一天了，把 gap_window 一起調大。"
        )

    @pytest.mark.parametrize("workflow,module,key", PIPELINES, ids=PIPELINE_IDS)
    def test_cadence_stays_hourly_because_the_data_is_still_hourly(
        self, workflow: str, module, key: str
    ) -> None:
        """cadence_hours 是「資料點該有多密」，不是「排程多久跑一次」。

        降頻只改抓取頻率，寫進去的仍是逐小時的桶（BUCKET == "1h"），每小時都該有列。
        跟著排程改成 6 會有兩個後果：_floor_to_cadence() 只認 1/24/168，傳 6 直接
        ValueError 讓 gate 每次執行都掛；就算補上支援，空段檢查也只會抽查每 6 小時
        一個點，6 小時裡缺 5 個都驗得過。
        """
        assert module.BUCKET == "1h"
        assert PIPELINES_BY_KEY[key].cadence_hours == 1, (
            f"{key}: cadence_hours 被改成 "
            f"{PIPELINES_BY_KEY[key].cadence_hours}——它跟著的是資料粒度，不是排程頻率。"
        )

    @pytest.mark.parametrize("workflow,module,key", PIPELINES, ids=PIPELINE_IDS)
    def test_cadence_is_a_value_the_gate_can_actually_floor(
        self, workflow: str, module, key: str
    ) -> None:
        """直接呼叫 _floor_to_cadence 驗它不會 ValueError——這是上一條的第一個後果。"""
        from scripts.data_quality_gate import _floor_to_cadence

        _floor_to_cadence(datetime(2026, 9, 10, 14, 37, tzinfo=timezone.utc),
                          PIPELINES_BY_KEY[key].cadence_hours)


# ══════════════════════════════════════════════════════════════════════
# 兩支管線之間的錯開
# ══════════════════════════════════════════════════════════════════════

def test_the_two_loki_pipelines_stay_staggered() -> None:
    """crawl 與 cwv 查同一個 Loki，降頻後單次掃描量變大，錯開的必要性更高。

    降頻前名目錯開 10 分鐘，被 GitHub 排程抖動（實測 +44 分）壓成中位 3.5 分鐘。
    降頻後 crawl 單次約 10.6 分鐘（W=14、每小時約 46s），錯開必須寬於它的執行時間。
    """
    crawl_minute = int(re.search(r"- cron:\s*'(\d+)\s+[\d,]+",
                                 _read_workflow("crawl-hourly.yml")).group(1))
    cwv_minute = int(re.search(r"- cron:\s*'(\d+)\s+[\d,]+",
                               _read_workflow("cwv-hourly.yml")).group(1))
    assert _cron_fire_hours("crawl-hourly.yml") == _cron_fire_hours("cwv-hourly.yml"), (
        "兩支排在不同的整點時，下面的分鐘差比較就沒有意義了，改斷言。"
    )
    # crawl 是長的那支（W=14 約 634s ≈ 10.6 分鐘），要排在前面。
    assert crawl_minute < cwv_minute, "crawl 是長的那支，應排在 cwv 之前"
    assert cwv_minute - crawl_minute >= 25, (
        f"crawl(:{crawl_minute:02d}) 與 cwv(:{cwv_minute:02d}) 只錯開 "
        f"{cwv_minute - crawl_minute} 分鐘，短於 crawl 的實測執行時間（約 10.6 分鐘）"
        "加上排程抖動的餘裕。"
    )


def test_hourly_pipelines_avoid_the_daily_cron_band() -> None:
    """0/6/12/18 這組整點是挑過的：其他組都會撞到既有的每日／週排程。

    這裡不逐一重貼每支 workflow 的 cron（那是把常數抄兩遍），只鎖住
    「不要排進每日忙碌時段」這個結論——07:20 gsc-search-analytics（跑 30 分鐘）、
    08:20 gsc-url-inspection、09:30 data-quality-watchdog、週一 09:00 起
    etl-and-deploy（約 104 分鐘，跑到約 10:44）。
    """
    busy_hours = {7, 8, 9, 10}
    for workflow in ("crawl-hourly.yml", "cwv-hourly.yml"):
        collisions = set(_cron_fire_hours(workflow)) & busy_hours
        assert not collisions, (
            f"{workflow} 排在 {sorted(collisions)} 點，落在每日排程的忙碌時段 "
            f"{sorted(busy_hours)}（gsc-search-analytics / gsc-url-inspection / "
            "data-quality-watchdog / 週一 etl-and-deploy）。"
        )
