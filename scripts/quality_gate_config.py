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


CRUX_PUBLISH_CADENCE_CEILING_HOURS = 168.0  # 7 天
# CrUX History API 自己的發布週期落差上限（不是我們的排程週期、也不是 max_age_hours
# 裡疊加的排程緩衝）。實測基礎：
#   1. KB freshness-threshold-schedule-period-formula-ignores-source-inherent-lag
#      （2026-08-29 首測）：lastDate 相對「現在」的落差在一個發布週期內於 0~7 天間浮動。
#   2. 2026-09-03 現場重測（S4「crux never ran」故障排查）：直接打 CrUX History API
#      （queryHistoryRecord，origin 級，LCP），最新 collectionPeriod 的原始
#      lastDate=2026-08-29；當時對齊後最新桶 hour=2026-08-24（bucket 關閉時間
#      2026-08-31），距離重測當下（2026-09-03）約 75h——與 0~7 天的區間一致，
#      沒有推翻既有測值。
# lag_buffer_hours 只需要覆蓋「CrUX 自己多久才會把某一週的資料放進 API 回應」
# 這一件事（從桶關閉時間算起，桶關閉時間本身已經是該週最晚可能的 lastDate 之後，
# 見下面 cwv_hourly_crux 的 lag_buffer_hours 註解）——不需要疊加排程緩衝，
# 那是 max_age_hours 的責任；兩者疊加會讓 gap 檢查遲鈍到失去意義
# （20 天才開始檢查一條週頻管線，真的漏跑要快一個月才被抓到）。
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
        lag_buffer_hours=1.5,  # 桶關閉後的容忍期（見本檔尾端「lag_buffer_hours 的語意」註解），非「桶起點」算起
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
        # 2026-09-03 修正：原本漏設，吃 default 0.0——等於要求「週一結束、資料立刻要在」，
        # 對一個有 7 天發布週期落差的來源必然誤報（2026-09-03 run 33710475866 實測撞到：
        # gate 在 ingest 把當週資料寫完前 15 秒讀了資料庫，把這次 run 自己正在寫的那一週
        # 誤判成 gap FAIL）。取值 = CRUX_PUBLISH_CADENCE_CEILING_HOURS(168h，見上方常數的
        # 實測依據) + 24h 量測不確定度緩衝（沒有連續多次觀測可取分布，只有兩個時間點的
        # 快照，用常數本身當下限、另加一點餘裕而非直接沿用測到的數字）。**不是**沿用
        # max_age_hours(480h)：那個數字疊加了排程緩衝(~7d)，兩者服務不同目的，
        # 疊加會讓 gap 檢查 20 天才開始檢查一條週頻管線，真的漏跑要快一個月才被抓到。
        lag_buffer_hours=CRUX_PUBLISH_CADENCE_CEILING_HOURS + 24.0,  # 192h
        ingestion_run_table_name="cwv_hourly",  # 與 RUM 共用同一個 table_name（見模組 docstring 缺陷 1）
        degradation=DegradationConfig(
            column="unknown_ratio", mode="ratio_column",
            max_ratio=0.05, min_sample=1, sample_limit=200,
        ),
        schedule_note="max_age_hours 門檻＝來源固有延遲上限(~13d) + 排程緩衝(~7d)，不是排程週期×N——"
                      "CrUX 的 lastDate 相對『現在』本身就有發布延遲，套用『週期×N』公式會對"
                      "健康資料誤報（KB freshness-threshold-schedule-period-formula-ignores-source-inherent-lag，"
                      "2026-08-29 首次實測 240h 門檻在健康資料上 FAIL，校準到 480h 後 PASS）。"
                      "lag_buffer_hours 是另一個獨立的數字，見上方欄位註解，不要混為一談。",
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
        lag_buffer_hours=1.5,  # 同 cwv_hourly_rum，見本檔尾端「lag_buffer_hours 的語意」註解
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

    # ── 4b. GSC Search Analytics — Google 新聞（無排名，page 組）──────
    PipelineConfig(
        key="gsc_googlenews",
        table="gsc_page_daily",  # 一律查視圖，同 gsc_daily_metrics 的理由
        filters=(("search_type", "googleNews"),),
        timestamp_column="date",
        max_age_hours=96 + 48,  # 沿用 gsc_daily_metrics：同一支腳本、同一次 run 內完成，來源延遲同構
        cadence_hours=24,
        cadence_label="daily",
        gap_window_hours=24 * 30,
        lag_buffer_hours=96 + 48,
        # 補充決策（ingestion_run 登記方式）：surface 資訊不進 table_name，維持既有分組相容；
        # googleNews/discover 與 web 共用同一個 ingestion_run_table_name，新鮮度靠 filters
        # 讀資料本身區分（比 run 紀錄可靠，CrUX 前例正是 run 紀錄缺席才看不到停擺）。
        ingestion_run_table_name="gsc_daily_metrics",
        degradation=None,
        degradation_skip_reason=(
            "沿用 gsc_daily_metrics 的判定：device 值域在 ingest 端直接 reject 非法值，"
            "不合法列不會落表，reject 數量未持久化到可查詢欄位。googleNews 只有 page 組"
            "（見 SURFACE_COMBOS，無排名 surface 不送 query 維度），母體比 web 更窄，"
            "沒有額外的降級維度可查，記為已知缺口，理由與 gsc_daily_metrics 相同。"
        ),
        schedule_note="門檻沿用 gsc_daily_metrics：googleNews 與 web 是同一支腳本、"
                      "同一次探測查詢的不同 search_type 分支，來源延遲特性相同。",
    ),

    # ── 4c. GSC Search Analytics — Discover（無排名，page 組）────────
    PipelineConfig(
        key="gsc_discover",
        table="gsc_page_daily",
        filters=(("search_type", "discover"),),
        timestamp_column="date",
        max_age_hours=96 + 48,
        cadence_hours=24,
        cadence_label="daily",
        gap_window_hours=24 * 30,
        lag_buffer_hours=96 + 48,
        ingestion_run_table_name="gsc_daily_metrics",
        degradation=None,
        degradation_skip_reason=(
            "沿用 gsc_daily_metrics 的判定：device 值域在 ingest 端直接 reject 非法值，"
            "不合法列不會落表，reject 數量未持久化到可查詢欄位。discover 只有 page 組"
            "（見 SURFACE_COMBOS，無排名 surface 不送 query 維度），母體比 web 更窄，"
            "沒有額外的降級維度可查，記為已知缺口，理由與 gsc_daily_metrics 相同。"
        ),
        schedule_note="門檻沿用 gsc_daily_metrics：discover 與 web 是同一支腳本、"
                      "同一次探測查詢的不同 search_type 分支，來源延遲特性相同。",
    ),

    # ── 4d. GSC 全站總數（date-only 探測查詢的副產品，非抽樣）────────
    PipelineConfig(
        key="gsc_daily_totals",
        table="gsc_daily_totals",  # 全量母體，與 gsc_page_daily 的抽樣母體不同，不可相加
        filters=(("search_type", "web"),),  # 三個 search_type 共用同一支腳本、同一次 run 寫入，
                                             # 取 web 當代表即可反映「探測查詢本身有沒有在跑」
        timestamp_column="date",
        max_age_hours=96 + 48,  # 與 gsc_daily_metrics 同一個數字：totals 是探測查詢的副產品，
                                  # 探測本身就是 gsc_daily_metrics 每次 run 都會做的第一步
        cadence_hours=24,
        cadence_label="daily",
        gap_window_hours=24 * 30,
        lag_buffer_hours=96 + 48,
        ingestion_run_table_name="gsc_daily_totals",  # write_totals() 另記一列，見補充決策
        degradation=None,
        degradation_skip_reason=(
            "gsc_daily_totals 本身就是全站彙總（date-only 探測查詢的四個 metric 欄位直接落表），"
            "沒有 page/query/device 之類的維度可拆，因此沒有『某個子集被靜默丟棄』這種降級可查——"
            "唯一可能的資料品質問題是整批 0 列，那屬於新鮮度／空段檢查的範圍，不重複用降級規則。"
        ),
        schedule_note="門檻沿用 gsc_daily_metrics：totals 與抽樣列在同一次 run、同一次探測查詢"
                      "內一起寫入（見 ingest_gsc_search_analytics.py write_totals()），延遲特性相同。",
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
# 為什麼 hourly 管線也要有 lag_buffer_hours，以及 lag_buffer_hours 的語意
# ══════════════════════════════════════════════════════════════════════
#
# S3.5 實測撞到兩層問題，兩層都修過，記錄下來避免下一個人重蹈：
#
# 【第一層：為什麼需要 buffer】對 crawl_daily 在 UTC 17:06 跑 check_gaps()，
# 把剛跨過整點、還沒被排程對象寫入的 16:00 那一桶也算進「應該有」，回報成一個
# 空段——但那不是真的空段，是排程本身有延遲：crawl-hourly.yml 排 `15 * * * *`，
# 但 GitHub Actions 排程觸發本身有可觀漂移（實測連續 6 次分別在整點後
# 22/26/23/28/23/28 分觸發，不是準時的 15 分），加上 freshness/gap job 刻意
# 不設 needs:（見 freshness-alert-shipped-inside-the-thing-it-monitors-cannot-see-its-own-absence
# 的教訓，ingest 沒被觸發時這個 job 仍要跑），兩個 job 在同一次排程觸發下是並行
# 起跑，不保證 gap 檢查執行時 ingest 已經寫完最新那一小時。
#
# 【第二層：buffer 的語意曾經算錯】`expected_timestamps()` 列舉的時間點 `t`
# 是桶的**起點**（例如 16:00 桶代表 [16:00,17:00)），第一版拿 `t` 直接跟
# `now - lag_buffer_hours` 比，這讓 `lag_buffer_hours` 裡有整整一段
# （等於 cadence_hours）被「桶本身的寬度」吃掉——buffer=1.25h、cadence=1h 時，
# 桶關閉後**實際容忍的排程延遲只剩 15 分鐘**，而 production 實測（見下）正常
# 延遲是 24–38 分鐘，於是每小時都有一段時間會誤報。這個問題不是「數字沒調對」，
# 是比較的基準點本身選錯了；已在 `expected_timestamps()` 改成比較桶的**關閉
# 時間**（`t + step`），`lag_buffer_hours` 現在字面上就是「桶關閉後容忍多久
# 沒資料」，不再隱含跟 cadence_hours 的換算。
#
# 【實測數據，供之後調整參考】用 ingestion_run 交叉比對（不要直接讀目的表的
# ingested_at 當「首次寫入時間」——crawl_daily 的 upsert 每次都會刷新
# ingested_at，見 KB postgrest-querystring-limit-silently-capped-by-db-max-rows
# 同一輪撞到的姊妹坑；cwv_hourly 因為 ingest_cwv_hourly.py 刻意不把 ingested_at
# 放進 payload 才可信，見該腳本【設計決定 5】）：crawl-hourly.yml 在
# 2026-09-02T09:07 UTC 修掉一個 56% 失敗率的 bug（commit 36bdf59）之後，
# 穩態下「桶關閉 → 第一次成功寫入完成」延遲 7 個樣本落在 0.40–0.63h；
# cwv_hourly（RUM）同期 15 個樣本落在 0.33–0.68h。lag_buffer_hours=1.5h
# 給了約 2.4 倍安全邊際，仍遠短於 max_age_hours=3h 的新鮮度門檻。
#
# 這個 buffer 不是用來蓋掉真正的管線故障——2026-09-01T19:00–20:00 那次真實
# 中斷（修復前，見 crawl_daily 的 09-01T20:00 空段）延遲一度到 13h，那種等級
# 的中斷本來就該被空段檢查抓到，不該靠加大 buffer 藏起來。
