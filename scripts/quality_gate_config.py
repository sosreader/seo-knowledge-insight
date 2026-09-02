"""
quality_gate_config.py — 五條 warehouse 管線的品質門檻設定（S3.5）

被 scripts/data_quality_gate.py 使用。本檔只放**設定與純資料結構**，不含任何
會發出 HTTP 請求的程式碼——這樣單元測試可以直接 import PIPELINES 驗證設定本身
的一致性，不需要 mock 網路。

═══ 為什麼要拆成獨立檔案 ═══

data_quality_gate.py 本身（三類檢查 + reap + CLI）已經逼近 800 行門檻，
五條管線的設定各自帶大段「為什麼門檻設這個值」的說明，混在同一檔會讓兩者
都讀不下去。這個拆分沿用本 repo已有的慣例——crawl_warehouse.py 之於
ingest_crawl_hourly.py 就是同一種「共用存取/設定層獨立成檔」的做法。

═══ 核心設計：檢查的對象是「管線」不是「表」═══

cwv_hourly 這張表同時裝著 RUM（逐小時）與 CrUX（逐週）兩條管線的資料
（source 欄位區分）。任何「以表為單位」的新鮮度檢查在 RUM 持續寫入時永遠是
綠燈，即使 CrUX 那個維度已經停擺——這正是 S3.5 實測到的缺陷 1。所以每個
PipelineConfig 對應的是**一條管線**（一個 workflow、一個排程），不是一張表；
一張表可以被多個 PipelineConfig 引用，各自帶自己的 filters。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Mapping


def _parse_iso(value: str) -> datetime:
    """Parse 一個 ISO 時間戳或純日期字串，一律回傳 tz-aware（UTC）。

    PostgREST 的 DATE 欄位（例如 gsc_page_daily.date）回傳的是不帶時間、
    不帶時區的純日期字串（"2026-08-30"），fromisoformat 會回傳 naive
    datetime——與其他欄位回傳的 tz-aware 時間戳混在一起相減會直接 TypeError。
    """
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _standard_extractor(timestamp_column: str) -> Callable[[Mapping], datetime]:
    """大多數管線：時間戳就是某一欄，直接 parse。"""
    def _extract(row: Mapping) -> datetime:
        return _parse_iso(row[timestamp_column])
    return _extract


def _crawl_daily_extractor(row: Mapping) -> datetime:
    """crawl_daily 沒有單一時間戳欄位，是 date（DATE）+ hour（0-23 整數）兩欄合成。

    做法沿用 scripts/crawl_warehouse.py 的 latest_bucket_hour()——同一份邏輯，
    這裡重寫一次是因為那邊回傳的是「最新一筆」，這裡要能對任意一列做同樣的合成。
    """
    return _parse_iso(row["date"]).replace(hour=int(row["hour"]), tzinfo=timezone.utc)


@dataclass(frozen=True)
class DegradationConfig:
    """第三類檢查：靜默降級。

    兩種模式：
      - "ratio_column"：目的表已經直接存了一個 0~1 的比例欄位（例如 cwv_hourly
        的 unknown_ratio，寫入當下就算好了），直接讀最近 N 列的值。
      - "fallback_value"：目的表的某個維度欄位有一個代表「無法分類/未知」的
        固定值（例如 crawl_daily.ua_group='other-bot'），比例 = 該值的列數
        （或加權欄位加總）÷ 全部列數（或加總）。
    """
    column: str
    mode: str  # "ratio_column" | "fallback_value"
    max_ratio: float
    min_sample: int
    sample_limit: int = 500
    fallback_value: str | None = None
    weight_column: str | None = None  # fallback_value 模式下可選：用這欄加總取代數列數


@dataclass(frozen=True)
class PipelineConfig:
    key: str                        # 唯一識別，例如 "cwv_hourly_crux"
    table: str                      # 查詢用的表或視圖（gsc 系列一律指向視圖）
    filters: tuple[tuple[str, str], ...]  # 額外的 eq 篩選，例如 (("source", "crux"),)
    max_age_hours: float            # 新鮮度門檻（第一類檢查）
    cadence_hours: float            # 預期的寫入週期，決定第二類檢查怎麼列舉「應該有」的時間點
    cadence_label: str              # 人類可讀的週期描述，用於報表
    ingestion_run_table_name: str   # ingestion_run.table_name 的值，供第三類「殘留 running」分組
    schedule_note: str              # 為什麼門檻設這個值（一句話，供 CLI/報表印出）
    timestamp_column: str | None = None
    extractor: Callable[[Mapping], datetime] | None = None
    select_columns: tuple[str, ...] = ()
    gap_window_hours: float | None = None   # None = 不做第二類檢查（見 gap_skip_reason）
    gap_skip_reason: str | None = None
    lag_buffer_hours: float = 0.0    # 掃描空段時，忽略「現在 - 這個值」以內的時間點（來源固有延遲）
    degradation: DegradationConfig | None = None
    degradation_skip_reason: str | None = None

    def resolved_extractor(self) -> Callable[[Mapping], datetime]:
        if self.extractor is not None:
            return self.extractor
        if self.timestamp_column is None:
            raise ValueError(f"{self.key}: 缺少 timestamp_column 或 extractor")
        return _standard_extractor(self.timestamp_column)

    def resolved_select_columns(self) -> tuple[str, ...]:
        if self.select_columns:
            return self.select_columns
        if self.timestamp_column is None:
            raise ValueError(f"{self.key}: 缺少 select_columns 或 timestamp_column")
        return (self.timestamp_column,)


# ══════════════════════════════════════════════════════════════════════
# 五條管線
# ══════════════════════════════════════════════════════════════════════

PIPELINES: tuple[PipelineConfig, ...] = (

    # ── 1. CWV RUM（Loki 逐小時聚合）────────────────────────────────
    PipelineConfig(
        key="cwv_hourly_rum",
        table="cwv_hourly",
        filters=(("source", "rum"),),
        timestamp_column="hour",
        max_age_hours=3,  # 排程週期 1h 的 3 倍；來源 Loki retention 168h，見 ingest_cwv_hourly.py
        cadence_hours=1,
        cadence_label="hourly",
        gap_window_hours=24,
        lag_buffer_hours=1.25,  # 見「排程本身的 cron offset」註解（本檔尾端），避免剛跨過整點就誤報
        ingestion_run_table_name="cwv_hourly",
        degradation=DegradationConfig(
            column="unknown_ratio", mode="ratio_column",
            max_ratio=0.05, min_sample=1, sample_limit=200,
        ),
        schedule_note="門檻＝排程週期(1h)×3。RUM 時間戳跟著壁鐘走（無固有來源延遲），"
                      "公式適用見 KB freshness-threshold-schedule-period-formula-ignores-source-inherent-lag。",
    ),

    # ── 2. CWV CrUX（Google CrUX History API，週序列）───────────────
    PipelineConfig(
        key="cwv_hourly_crux",
        table="cwv_hourly",
        filters=(("source", "crux"),),
        timestamp_column="hour",
        max_age_hours=24 * 20,  # 480h：來源固有延遲上限(~13d) + 排程緩衝，KB 已實測校準過
        cadence_hours=24 * 7,
        cadence_label="weekly",
        gap_window_hours=24 * 56,  # 掃 8 週；若管線上線不滿 8 週，掃描下限會被目前資料的最早時間戳墊高
        ingestion_run_table_name="cwv_hourly",  # 與 RUM 共用同一個 table_name（見模組 docstring 缺陷 1）
        degradation=DegradationConfig(
            column="unknown_ratio", mode="ratio_column",
            max_ratio=0.05, min_sample=1, sample_limit=200,
        ),
        schedule_note="門檻＝來源固有延遲上限(~13d) + 排程緩衝(~7d)，不是排程週期×N——"
                      "CrUX 的 lastDate 相對『現在』本身就有發布延遲，套用『週期×N』公式會對"
                      "健康資料誤報（KB freshness-threshold-schedule-period-formula-ignores-source-inherent-lag，"
                      "2026-08-29 首次實測 240h 門檻在健康資料上 FAIL，校準到 480h 後 PASS）。",
    ),

    # ── 3. Crawler 逐小時聚合（Loki）─────────────────────────────────
    PipelineConfig(
        key="crawl_daily",
        table="crawl_daily",
        filters=(),
        extractor=_crawl_daily_extractor,
        select_columns=("date", "hour"),
        max_age_hours=3,
        cadence_hours=1,
        cadence_label="hourly",
        gap_window_hours=24,
        lag_buffer_hours=1.25,  # 同 cwv_hourly_rum，見本檔尾端「排程本身的 cron offset」註解
        ingestion_run_table_name="crawl_daily",
        degradation=DegradationConfig(
            column="ua_group", mode="fallback_value", fallback_value="other-bot",
            weight_column="request_count",
            max_ratio=0.05, min_sample=1000, sample_limit=5000,
        ),
        schedule_note="門檻＝排程週期(1h)×3，時間戳跟著壁鐘走。降級檢查看 ua_group='other-bot'"
                      "（過濾樣式命中泛用 bot 標記但無法歸類到具名分群的殘餘桶，"
                      "見 scripts/crawl_taxonomy.py classify() 的 docstring）佔請求數的比例。",
    ),

    # ── 4. GSC Search Analytics（頁面×裝置、關鍵字×裝置）────────────
    PipelineConfig(
        key="gsc_daily_metrics",
        table="gsc_page_daily",  # 一律查視圖，見任務書「gsc_daily_metrics 底表…會得到約兩倍假數字」
        filters=(),
        timestamp_column="date",
        max_age_hours=96 + 48,  # 144h：GSC 官方 2-3 天延遲 + 排程緩衝，既有腳本已用此值
        cadence_hours=24,
        cadence_label="daily",
        gap_window_hours=24 * 30,
        lag_buffer_hours=96 + 48,  # 與新鮮度門檻同一個數字：門檻已經編碼了「來源延遲多久算正常」，
                                    # 空段掃描沿用同一個容忍窗，不重新發明一個數字
        ingestion_run_table_name="gsc_daily_metrics",
        degradation=None,
        degradation_skip_reason=(
            "live-verified 2026-09-03：device 值域在 ingest 端直接 reject 非法值"
            "（DEVICE_MAP 只認 mobile/tablet/desktop，_reject() 見 ingest_gsc_search_analytics.py），"
            "不合法列不會落表、也沒有 sentinel 桶留在 gsc_daily_metrics 裡；reject 數量目前只印在"
            "執行 log，未持久化到任何可查詢欄位（ingestion_run 無 error/reject 欄位）。本管線暫無"
            "可查的靜默降級維度，記為已知缺口（不是本次 gate 略過不做）——若要補上，需要先讓"
            "ingest 腳本把 reject 統計寫進 ingestion_run（例如新增 metadata jsonb 欄位），超出本次"
            "『統一既有檢查』的範圍，建議另立 step。"
        ),
        schedule_note="門檻沿用既有腳本 96+48h；來源延遲 2-3 天為官方 typically 用語，"
                      "見 KB probe-source-for-available-dates-instead-of-hardcoding-publication-lag——"
                      "本檔不重新硬編延遲天數，直接沿用既有腳本已校準過的門檻常數。",
    ),

    # ── 5. GSC URL Inspection（配額守門抽樣）─────────────────────────
    PipelineConfig(
        key="gsc_url_inspection",
        table="gsc_url_inspection",
        filters=(),
        timestamp_column="inspected_at",
        max_age_hours=24 * 4,
        cadence_hours=24,
        cadence_label="daily(quota-gated)",
        gap_window_hours=None,
        gap_skip_reason=(
            "此管線每日配額有限，『當日配額一開始就不夠 → 不查任何 URL → 0 筆寫入』是文件化的"
            "合法成功狀態之一（見 ingest_gsc_url_inspection.py 模組 docstring「0 筆的三種樣貌」），"
            "不是資料缺口。逐日掃『是否有列』會把合法的 0-列日誤判成空段。新鮮度檢查"
            "（max_age_hours=96h）已經涵蓋『作業真的停擺』這個情境，此處不重複用一個"
            "會誤報的規則去涵蓋同一件事。"
        ),
        ingestion_run_table_name="gsc_url_inspection",
        degradation=DegradationConfig(
            column="indexing_state", mode="fallback_value",
            fallback_value="INDEXING_STATE_UNSPECIFIED",
            max_ratio=0.5, min_sample=10, sample_limit=500,
        ),
        schedule_note="門檻沿用既有腳本 24*4h。降級檢查看 indexing_state="
                      "'INDEXING_STATE_UNSPECIFIED'（migration 015 定義的官方 5 值 enum 之一，"
                      "Google 自己的『不知道』狀態）佔比；live-verified 2026-09-03 目前 20 筆中"
                      "4 筆（20%）為此值，門檻設 50% 是因為樣本量小（配額限制）雜訊本來就高，"
                      "50% 才不會對現況誤報，同時仍能抓到『驗證整批失效』這種量級的異常。",
    ),
)

PIPELINES_BY_KEY: dict[str, PipelineConfig] = {p.key: p for p in PIPELINES}

# 供第三類檢查（殘留 running）使用：ingestion_run 裡實際出現過的 table_name 全集，
# 不只限於上面 5 條管線各自宣告的 ingestion_run_table_name——quota 分類帳
# （gsc_url_inspection_quota）等輔助紀錄也共用同一張表，混進同一個檢查沒有壞處
# （它的寫入模式是「打完 API 立刻 INSERT status=success」，天生不會卡在 running，
#  見 ingest_gsc_url_inspection.py record_quota_usage()）。
STALE_RUNNING_THRESHOLD_HOURS_BY_TABLE: dict[str, float] = {}
for _p in PIPELINES:
    _existing = STALE_RUNNING_THRESHOLD_HOURS_BY_TABLE.get(_p.ingestion_run_table_name)
    _candidate = 6.0 if _p.cadence_hours <= 1 else 24.0
    if _existing is None or _candidate < _existing:
        STALE_RUNNING_THRESHOLD_HOURS_BY_TABLE[_p.ingestion_run_table_name] = _candidate
DEFAULT_STALE_RUNNING_THRESHOLD_HOURS = 24.0  # 落在上面字典以外的 table_name（例如 quota 分類帳）

# ══════════════════════════════════════════════════════════════════════
# 為什麼 hourly 管線也要有 lag_buffer_hours（不是只有 GSC 這種有「來源固有延遲」的才需要）
# ══════════════════════════════════════════════════════════════════════
#
# S3.5 實測撞到：對 crawl_daily 在 UTC 17:06 跑 check_gaps()，把剛跨過整點、
# 還沒被排程對象寫入的 16:00 那一桶也算進「應該有」，回報成一個空段——但那不是
# 真的空段，只是排程本身有 cron offset：crawl-hourly.yml 排在整點後第 15 分鐘
# 才觸發（`15 * * * *`），加上 freshness/gap job 刻意不設 needs:（見
# freshness-alert-shipped-inside-the-thing-it-monitors-cannot-see-its-own-absence
# 的教訓，ingest 沒被觸發時這個 job 仍要跑），兩個 job 在同一次排程觸發下是並行
# 起跑，不保證 ingest 已經寫完最新那一小時。
#
# RUM/crawler 這類「時間戳跟著壁鐘走」的來源雖然沒有 GSC 那種資料源頭延遲，
# 仍然有這個排程本身的延遲——lag_buffer_hours=1.25h 給 cron offset(<=15min)
# 與執行時間留足夠餘裕，同時遠短於 max_age_hours=3h 的新鮮度門檻（空段檢查
# 理應比「整條管線死了」的新鮮度告警更早注意到單一桶缺失，門檻不能反而更寬鬆）。
