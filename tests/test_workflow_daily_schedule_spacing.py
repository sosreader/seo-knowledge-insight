"""回歸測試：每日排程的三段間隔不得被後續改動悄悄吃掉。

背景（2026-09-10）：gsc-url-inspection.yml 的 cron 原本是 07:40 UTC，註解寫著
「錯開 gsc-search-analytics（07:20）避免同時打 Supabase」。這個 20 分鐘的假設在
2026-09-04 把 image／video 加進 gsc-search-analytics 的 matrix 之後就失效了——
SA 的 wall clock 從 8-9 分鐘漲到 22-30 分鐘，最近 6 次排程有 5 次執行區間相交，
而且沒有任何測試會為此變紅。這一支就是那個缺席的測試。

它鎖的不是「時刻等於某個值」（那樣只是把常數抄兩遍），而是三個有理由的不變量：
  1. gsc-url-inspection 必須在 gsc-search-analytics 的實測時長之後才起跑
  2. gsc-url-inspection 必須在 data-quality-watchdog 之前跑完——watchdog 是唯一
     能發現「排程整個沒被觸發」的機制，它得看得到當天的資料
  3. 每段間隔要留得比本 repo 每日 cron 的實測抖動更寬

實測數字的出處寫在各常數上，改動時要一併更新出處而不是只改數字。
"""
from __future__ import annotations

import re
from pathlib import Path

WORKFLOWS_DIR = Path(__file__).resolve().parent.parent / ".github" / "workflows"

# gsc-search-analytics 的實測 wall clock。09-04 加入 image/video 後的穩態排程 run
# 實測 22/25/29/30/30 分鐘（B 頻率審計，2026-09-02..09-08 的 /timing 端點）。取上緣。
GSC_SEARCH_ANALYTICS_RUNTIME_MIN = 30

# 本 repo 每日 cron 的實測觸發抖動：SA 07:20→07:27/07:31、URL inspection
# 07:40→07:44、watchdog 09:30→09:34，即 +4 ~ +11 分鐘。
DAILY_CRON_JITTER_MIN = 11

# 間隔至少要留抖動的兩倍，才不會像 07:40 那個 20 分鐘假設一樣被一次成長吃掉。
MIN_CLEARANCE_MIN = DAILY_CRON_JITTER_MIN * 2


def _daily_cron_minutes(workflow_name: str) -> int:
    """回傳每日 cron 的「當天第幾分鐘」。只認 `M H * * *` 形式。"""
    text = (WORKFLOWS_DIR / workflow_name).read_text(encoding="utf-8")
    matches = [
        m for line in text.splitlines()
        if not line.lstrip().startswith("#")
        for m in re.findall(r"- cron:\s*['\"](\d+)\s+(\d+)\s+\*\s+\*\s+\*['\"]", line)
    ]
    assert len(matches) == 1, f"{workflow_name} 預期剛好一個每日 cron，實際 {matches}"
    minute, hour = matches[0]
    return int(hour) * 60 + int(minute)


def test_url_inspection_starts_after_search_analytics_finishes() -> None:
    sa = _daily_cron_minutes("gsc-search-analytics.yml")
    insp = _daily_cron_minutes("gsc-url-inspection.yml")
    earliest_safe = sa + GSC_SEARCH_ANALYTICS_RUNTIME_MIN + MIN_CLEARANCE_MIN
    assert insp >= earliest_safe, (
        f"gsc-url-inspection 排在 {insp // 60:02d}:{insp % 60:02d} UTC，"
        f"但 gsc-search-analytics {sa // 60:02d}:{sa % 60:02d} 起跑要跑 "
        f"{GSC_SEARCH_ANALYTICS_RUNTIME_MIN} 分鐘，加上 {MIN_CLEARANCE_MIN} 分鐘的"
        f"抖動餘裕最早只能排在 {earliest_safe // 60:02d}:{earliest_safe % 60:02d}——"
        "兩支會同時打 Supabase（2026-09-04 起實測 6 次排程有 5 次相交）。"
    )


def test_url_inspection_finishes_before_the_watchdog_checks() -> None:
    """watchdog 是唯一能發現「排程整個沒被觸發」的機制，得看得到當天資料。"""
    insp = _daily_cron_minutes("gsc-url-inspection.yml")
    watchdog = _daily_cron_minutes("data-quality-watchdog.yml")
    # ingest job 中位 152s + gate step，抓 5 分鐘上緣。
    latest_safe = watchdog - DAILY_CRON_JITTER_MIN - 5
    assert insp <= latest_safe, (
        f"gsc-url-inspection（{insp // 60:02d}:{insp % 60:02d}）跑完可能晚於 "
        f"data-quality-watchdog（{watchdog // 60:02d}:{watchdog % 60:02d}），"
        "watchdog 那天就看不到本管線剛寫進去的資料。"
    )


def test_url_inspection_does_not_collide_with_the_weekly_etl() -> None:
    """etl-and-deploy 是週一 09:00 的 104 分鐘長工作，會對 Supabase 大量 upsert。"""
    text = (WORKFLOWS_DIR / "etl-and-deploy.yml").read_text(encoding="utf-8")
    match = re.search(r"- cron:\s*['\"](\d+)\s+(\d+)\s+\*\s+\*\s+(\d+)['\"]", text)
    assert match, "etl-and-deploy.yml 的 cron 不是預期的每週形式"
    etl_start = int(match.group(2)) * 60 + int(match.group(1))
    insp = _daily_cron_minutes("gsc-url-inspection.yml")
    assert insp + DAILY_CRON_JITTER_MIN + 5 <= etl_start, (
        f"gsc-url-inspection（{insp // 60:02d}:{insp % 60:02d}）可能疊到週一的 "
        f"etl-and-deploy（{etl_start // 60:02d}:{etl_start % 60:02d} 起跑、約 104 分鐘）。"
    )
