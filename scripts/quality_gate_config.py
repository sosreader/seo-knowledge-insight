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


GSC_PROPERTY = "https://vocus.cc/"
# 來源：scripts/gsc_surfaces.py 的 PROPERTY 常數（ingest 端寫入時用的同一個值）。
# 本檔刻意不 import gsc_surfaces（那個模組是 ingest pipeline 的一部分，維持本檔
# 「只放設定與純資料結構、零外部依賴」的既有原則，見模組 docstring），改成複製
# 這個值——`select distinct property from gsc_daily_totals` 目前只有這一個值，
# 兩邊要保持一致，改動一邊記得改另一邊。
#
# 為什麼要在 gsc_* 管線的 filters 帶上這個值：run 33863653352／run 33863650667
# 都撞過 57014。EXPLAIN ANALYZE 實測 gsc_daily_metrics_dim_uniq
# (property, search_type, date, page, query, device, country) 只要查詢帶
# property 就會被 planner 選上（Index Only Scan／Index Scan，個位數毫秒）；
# 沒帶 property 時 planner 會挑錯索引（gsc_daily_metrics_page_date_idx）做
# 近全表掃描，11–33 秒。不是語意窄化——這張表目前只有一個 property，
# 加這個 filter 不改變任何一條管線原本篩出來的列集合，純粹是讓 planner
# 找到對的索引。

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
    # lag_buffer_hours：掃描空段時，忽略「現在 - 這個值」以內的時間點（來源固有延遲）。
    #
    # 2026-09-03 改成必填（無 default）——原本 default 0.0，cwv_hourly_crux 漏填吃到
    # 這個 default，等於要求「週期一結束、資料立刻要在」，對一個有 7 天發布延遲的
    # 來源必然誤報（run 33710475866 實測撞到）。事後稽核時發現另一個問題：
    # gsc_url_inspection「沒有這一行」是不是「刻意判斷用不到」，光看程式碼分不出來——
    # 「欄位不存在」與「刻意不設」在 default 值制度下長得一模一樣。
    #
    # 拿掉 default 逼每條管線顯式填一個值，把這個歧義解掉：管線若不需要這個緩衝
    # （例如 gap_window_hours=None，整個空段檢查都 SKIP），一樣要填 0.0，但**旁邊
    # 附一行理由**——「填了 0.0 且說明為什麼」與「沒填」不會再同形。
    # 不用額外的 sentinel 常數（例如 LAG_NOT_APPLICABLE）：Python 的必填欄位本身
    # 就是型別系統能表達的最小承諾，建構時漏填會直接 TypeError，比用一個「看起來
    # 像數值但其實是哨兵」的常數更不容易被誤用成正常值算進運算裡。
    lag_buffer_hours: float
    timestamp_column: str | None = None
    extractor: Callable[[Mapping], datetime] | None = None
    select_columns: tuple[str, ...] = ()
    gap_window_hours: float | None = None   # None = 不做第二類檢查（見 gap_skip_reason）
    gap_skip_reason: str | None = None
    # gap_probe_per_point：空段檢查改用「每個預期時間點各發一次 limit=1 探測」，
    # 而不是預設的「把掃描窗內所有列抓回來再取 distinct 時間戳」。
    #
    # 為什麼需要這個開關：預設路徑用 Range header 每頁 1000 列翻到底，只為了得到
    # 一組 distinct 的日期。表小的時候沒差，表大的時候是災難——2026-09-03 16:03
    # 的 watchdog run 33776287535 就是這樣掛的：gsc_page_daily 是視圖
    # （WHERE page <> gsc_page_not_requested() + NULLIF(position,0)），底表
    # gsc_daily_metrics 光 web 就有約 99 萬列，30 天窗要翻約 1,000 頁，而 PostgREST
    # 的深 OFFSET 分頁在視圖上每一頁都要重算一次，必然撞 statement_timeout（57014）。
    # 同日 09:34 的排程 run 還勉強 PASS，480 天回填後就再也過不了——是結構性問題，
    # 不是偶發抖動，所以解法不是加大 timeout 而是換查詢形狀。
    #
    # 逐點探測的成本是「預期時間點數」次請求（30 天日頻 = 31 次），每次只取 1 列，
    # 不做 OFFSET，跟表多大無關。只對真的需要的管線 opt-in：小表走原路徑（一次
    # 請求就抓完）比發 N 次請求便宜，沒必要一起換。
    gap_probe_per_point: bool = False
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
        # 「× 3」聽起來的安全邊際比實際的小——見 crawl_daily 同一個常數旁的完整
        # 實測數字（GitHub Actions schedule trigger 本身的 jitter，不是這條管線
        # 特有的），這裡不重複貼一次，只留指標。2026-09-03 team-lead 實測。
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
        # 「排程週期(1h) × 3」這個公式假設週期是準的——GitHub Actions 的 schedule
        # trigger 不是。2026-09-03 team-lead 實測 crawl-hourly.yml（cron 15 * * * *）
        # 最近 20 次 schedule 觸發（09-02 07:28..09-03 03:22）：
        #   相鄰間隔(分)：64 55 59 57 73 50 60 62 60 55 67 51 65 56 61 58 98 39 104
        #   實際觸發分鐘：20 21 22 23 25 26 28 30 33 36 38 59（名目 :15，最遲晚 44 分）
        #   2 次接近雙倍間隔（98、104 分）——不是漏跑（20 次觸發對 ~20 小時，
        #   總數對得上），是某一拍被 GitHub 往後推、下一拍補回來。
        # 疊上實測寫入延遲（0.40–0.63h，見本檔尾端「lag_buffer_hours 的語意」）：
        # 最壞情況 ≈ 104min + 38min ≈ 2.4h，離 max_age_hours=3h 只剩 ~0.6h 餘裕，
        # 比「3 倍」聽起來的安全邊際窄得多。**目前沒有實際誤報，先不調**——
        # 這行只是把「有效週期不是 1h」這個事實寫下來，下次有人真的要調這個
        # 門檻時，判準跟 cwv_hourly_crux 的 lag_buffer_hours 一樣：從這組實測
        # 分布反推，不要憑印象；調了要補 regression test 鎖語意
        # （例如「門檻需覆蓋實測到的最大 schedule 間隔 + 寫入延遲 + 安全邊際」），
        # 不要鎖魔術數字。cwv_hourly_rum（cron 5 * * * *）受同一個平台行為
        # 影響，數字量級相同（team-lead／pipeline-outages 2026-09-03 各自
        # 獨立驗證過），這裡不重複貼一次。
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
        # 只帶 property，不帶 search_type：property 是查詢效率的 filter，不是語意窄化——
        # 這張表目前只有一個 property（GSC_PROPERTY 註解），帶不帶都是同一批列，差別只在
        # planner 選不選得到 gsc_daily_metrics_dim_uniq（見 GSC_PROPERTY 欄位註解，
        # run 33863650667）。**刻意不加** search_type 篩選：維持既有語意——任一 surface
        # 當天有列就算那天有資料。加了 search_type 篩選會把語意從「GSC ingest 那天有沒有
        # 跑」偷換成「web surface 那天有沒有列」，是另一個檢查，不在本次範圍。
        filters=(("property", GSC_PROPERTY),),
        timestamp_column="date",
        max_age_hours=96 + 48,  # 144h：GSC 官方 2-3 天延遲 + 排程緩衝，既有腳本已用此值
        cadence_hours=24,
        cadence_label="daily",
        gap_window_hours=24 * 30,
        # 逐點探測：本管線是五條裡唯一大到會讓「整窗抓回來」撞 statement_timeout 的，
        # 見 PipelineConfig.gap_probe_per_point 的欄位註解（run 33776287535）。
        gap_probe_per_point=True,
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
        # property 排在 search_type 前面，對齊 gsc_daily_metrics_dim_uniq(property,
        # search_type, ...) 的欄位順序與 EXPLAIN 實測用的查詢寫法（見 GSC_PROPERTY 註解）；
        # PostgREST querystring 順序不影響 planner 選索引，這裡純粹是可讀性。
        filters=(("property", GSC_PROPERTY), ("search_type", "googleNews")),
        timestamp_column="date",
        max_age_hours=96 + 48,  # 沿用 gsc_daily_metrics：同一支腳本、同一次 run 內完成，來源延遲同構
        cadence_hours=24,
        cadence_label="daily",
        # lag_buffer_hours 用不到：gap_window_hours=None 讓整個第二類檢查（空段）SKIP，
        # 這個值只有 check_gaps() 會讀，填 0.0 是滿足型別要求（見上方欄位註解），
        # 不是「這條管線剛好緩衝需求是 0」——理由見下方 gap_skip_reason。
        lag_buffer_hours=0.0,
        gap_window_hours=None,
        gap_skip_reason=(
            "review S4.1 SF-2（2026-09-03）：googleNews 是無排名 surface，曝光本質斷續——"
            "ingest 端只抓探測到有資料的日期（resolve_targets → dates_from_totals），某天"
            "vocus.cc 沒有 googleNews 曝光時，那天在 gsc_page_daily 就是合法的『沒有列』，"
            "不是管線故障。gap_window_hours 掃 30 天窗內『是否每天都有列』會把這種本來就"
            "沒曝光的日子當成空段，連紅 30 天直到滑出窗外——這不是機率事件，是曝光模式的"
            "必然結果。web 每天都有搜尋流量、不會遇到這個誤判，沿用它的 gap 設定在此不成立。"
            "新鮮度檢查（max_age_hours=144h）已涵蓋『作業真的停擺』，此處不重複用一個"
            "會誤報的規則去涵蓋同一件事；is_position_valid()/022 CHECK 仍保證單列品質。"
        ),
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

    # ── 4b-2/4b-3. GSC Search Analytics — 圖片／影片（有排名，page＋query 組）──
    # 2026-09-04 補：S3.6 一致性驗證發現 image／video 從未進 warehouse——
    # SURFACE_COMBOS 早就支援（見 gsc_surfaces.py，兩者都是 (COMBO_PAGE, COMBO_QUERY)，
    # 與 web／news 同構，不是 NO_RANKING_SURFACES），只差排程沒排進去，兩格因此不可比。
    # 併入排程後補這兩條獨立 gate，理由與 gsc_googlenews 相同：gsc_daily_metrics
    # 不帶 filter，web 每天在寫會蓋掉 image／video 自己停擺的訊號。
    PipelineConfig(
        key="gsc_image",
        table="gsc_page_daily",  # 一律查視圖，同 gsc_daily_metrics 的理由
        # property 排在 search_type 前面，理由同 gsc_googlenews；run 33863650667 撞 57014，
        # EXPLAIN 實測不帶 property 時 freshness 查詢（search_type=eq.video 那個形狀，
        # image 同構）要 26–33 秒，帶了只要個位數毫秒（見 GSC_PROPERTY 註解）。
        filters=(("property", GSC_PROPERTY), ("search_type", "image")),
        timestamp_column="date",
        max_age_hours=96 + 48,  # 沿用 gsc_daily_metrics：同一支腳本、同一次 run 內完成，來源延遲同構
        cadence_hours=24,
        cadence_label="daily",
        # lag_buffer_hours 用不到：gap_window_hours=None 讓整個第二類檢查（空段）SKIP，
        # 這個值只有 check_gaps() 會讀，填 0.0 是滿足型別要求（見上方欄位註解），
        # 不是「這條管線剛好緩衝需求是 0」——理由見下方 gap_skip_reason。
        lag_buffer_hours=0.0,
        gap_window_hours=None,
        gap_skip_reason=(
            "跟 googleNews/discover 的『不支援排名維度』不是同一個成因——image 是有排名的"
            "surface（SURFACE_COMBOS 給了 page＋query 兩組，與 web 同構），不放寬排名檢查。"
            "改採保守預設是因為 image 在 2026-09-04 之前 warehouse 從未 ingest 過"
            "（S3.6 一致性驗證，`.verification/2026-08-29-seo-capability/S3.6-parallel-comparison.md`"
            " G38），沒有任何 live 資料能確認它每天是否連續有曝光——舊 GSC UI 報告只有"
            "08-13~08-19 一週總點擊 20,767（量級上其實高於 news 的 934，並非『流量遠小於"
            "web／news』，這點不能假設），但那是週彙總，看不出逐日是否連續。ingest 端只抓"
            "探測到有資料的日期（resolve_targets → dates_from_totals），若哪天真的沒有 image"
            "曝光，那天在 gsc_page_daily 合法地『沒有列』，不是管線故障；gap_window_hours 掃"
            "30 天窗內『是否每天都有列』一旦命中這種日子就會連紅 30 天直到滑出窗外，且在"
            "資料還沒開始累積的頭幾週最容易誤報。在有實測的逐日分佈之前，比照 googleNews／"
            "discover 的保守做法先跳過空段檢查；新鮮度檢查（max_age_hours=144h）已涵蓋"
            "『作業真的停擺』。待累積數週資料後應回頭用實測分佈重新評估是否該開回 gap 檢查"
            "（而非放著永遠 SKIP）——這是本次沒做、留給下一輪的 follow-up。"
        ),
        # 補充決策同 gsc_googlenews：surface 資訊不進 table_name，維持既有分組相容；
        # 新鮮度靠 filters 讀資料本身區分。
        ingestion_run_table_name="gsc_daily_metrics",
        degradation=None,
        degradation_skip_reason=(
            "沿用 gsc_daily_metrics 的判定：device 值域在 ingest 端直接 reject 非法值，"
            "不合法列不會落表，reject 數量未持久化到可查詢欄位。image 兩套維度組合都有"
            "（page 與 query，見 SURFACE_COMBOS），母體結構與 web 相同，沒有額外的降級維度"
            "可查，記為已知缺口，理由與 gsc_daily_metrics 相同。"
        ),
        schedule_note="門檻沿用 gsc_daily_metrics：image 與 web 是同一支腳本、"
                      "同一次探測查詢的不同 search_type 分支，來源延遲特性相同。",
    ),

    PipelineConfig(
        key="gsc_video",
        table="gsc_page_daily",  # 一律查視圖，同 gsc_daily_metrics 的理由
        # property 排在 search_type 前面，理由同 gsc_googlenews；run 33863650667 撞 57014，
        # EXPLAIN 實測不帶 property 時這個查詢形狀（search_type=eq.video&order=date.desc
        # &limit=1）要 26,208ms／33,266ms，帶了只要 4.2ms（見 GSC_PROPERTY 註解）。
        filters=(("property", GSC_PROPERTY), ("search_type", "video")),
        timestamp_column="date",
        max_age_hours=96 + 48,  # 沿用 gsc_daily_metrics：同一支腳本、同一次 run 內完成，來源延遲同構
        cadence_hours=24,
        cadence_label="daily",
        lag_buffer_hours=0.0,  # 見 gsc_image 同欄位註解，gap 檢查整個 SKIP
        gap_window_hours=None,
        gap_skip_reason=(
            "理由結構與 gsc_image 相同（video 也是有排名的 surface，SURFACE_COMBOS 給了"
            "page＋query 兩組，與 web 同構，不放寬排名檢查）：video 在 2026-09-04 之前"
            "warehouse 從未 ingest 過（S3.6 一致性驗證 G39），沒有 live 資料能確認逐日是否"
            "連續有曝光——舊 GSC UI 報告 08-13~08-19 一週總點擊只有 1,280（量級上與 news 的"
            "934 相近，遠低於 image 的 20,767），但同樣只是週彙總，看不出逐日分佈。ingest"
            "端只抓探測到有資料的日期，若某天真的沒有 video 曝光，那天在 gsc_page_daily 合法"
            "地『沒有列』，不是管線故障；gap_window_hours 掃 30 天窗一旦命中就會連紅 30 天，"
            "資料還沒開始累積的頭幾週最容易誤報。在有實測的逐日分佈之前，比照 googleNews／"
            "discover 的保守做法先跳過空段檢查；新鮮度檢查（max_age_hours=144h）已涵蓋"
            "『作業真的停擺』。待累積數週資料後應回頭用實測分佈重新評估，留給下一輪的 follow-up。"
        ),
        ingestion_run_table_name="gsc_daily_metrics",
        degradation=None,
        degradation_skip_reason=(
            "沿用 gsc_daily_metrics 的判定：device 值域在 ingest 端直接 reject 非法值，"
            "不合法列不會落表，reject 數量未持久化到可查詢欄位。video 兩套維度組合都有"
            "（page 與 query，見 SURFACE_COMBOS），母體結構與 web 相同，沒有額外的降級維度"
            "可查，記為已知缺口，理由與 gsc_daily_metrics 相同。"
        ),
        schedule_note="門檻沿用 gsc_daily_metrics：video 與 web 是同一支腳本、"
                      "同一次探測查詢的不同 search_type 分支，來源延遲特性相同。",
    ),

    # ── 4c. GSC Search Analytics — Discover（無排名，page 組）────────
    PipelineConfig(
        key="gsc_discover",
        # 2026-09-03 S2.5：live run 證實 discover 連 page 組（date+page+device）都回 400
        # 「Requests for Discover cannot be grouped by device」——不只 query 維度被擋，
        # device 維度本身就不支援。SURFACE_COMBOS["discover"] 因此改成空 tuple，discover
        # 只收 gsc_daily_totals，不再有 gsc_page_daily 列可查，本管線改指向 totals 表。
        # 2026-09-04 S2.4 補：discover 之後補上不帶 device 的 page_nodevice 組
        # （見 gsc_surfaces.py），page 層有了自己的寫入路徑，新鮮度訊號另立
        # gsc_discover_pages（見下方），本條目維持只管 totals 母體的新鮮度。
        # review NB-3（2026-09-04）：filters 補上 property（排在 search_type 前面）——
        # gsc_daily_totals_uniq(property, search_type, date) 同樣以 property 前導
        # （見 TOTALS_CONFLICT_FIELDS），REQ-3 橫切規則對 totals 表同樣適用。
        table="gsc_daily_totals",
        filters=(("property", GSC_PROPERTY), ("search_type", "discover")),
        timestamp_column="date",
        max_age_hours=96 + 48,  # 沿用 gsc_daily_metrics：totals 與探測查詢同一次 run 內完成
        cadence_hours=24,
        cadence_label="daily",
        # lag_buffer_hours 用不到：gap_window_hours=None 讓整個第二類檢查（空段）SKIP，
        # 這個值只有 check_gaps() 會讀，填 0.0 是滿足型別要求，理由見下方 gap_skip_reason。
        lag_buffer_hours=0.0,
        gap_window_hours=None,
        gap_skip_reason=(
            "review S4.1 SF-2（2026-09-03）＋S2.5 discover-fix 更新：discover 曝光本質斷續——"
            "一篇文章進 Discover 才有曝光，ingest 端只抓探測到有資料的日期，某天沒有 Discover"
            "曝光時那天沒有 totals 列是合法狀態，不是管線故障。gap_window_hours 掃 30 天窗"
            "會把沒曝光的日子當空段、連紅 30 天直到滑出窗外，不是機率事件，是曝光模式的"
            "必然結果，改查 gsc_daily_totals 後這個論證仍然成立（母體換了，斷續的本質沒換）。"
            "新鮮度檢查（max_age_hours=144h）已涵蓋『作業真的停擺』，此處不重複用一個"
            "會誤報的規則去涵蓋同一件事。"
        ),
        # review NB-2（2026-09-04）：此段原文（S2.5 discover-fix 時）寫「discover 只收
        # totals，那張表 discover 現在完全不寫」已過時——S2.4 補上 page_nodevice 組後，
        # discover 現在會把 (date, page) 列寫進 gsc_daily_metrics（見 gsc_surfaces.py
        # SURFACE_COMBOS["discover"]）。本條目仍指向 gsc_daily_totals，是因為 totals 與
        # page 層是兩個母體、兩條寫入路徑：totals 的 ingestion_run 由 write_totals()
        # 另記一列，不與 gsc_daily_metrics 共用分組；page 層的新鮮度訊號另立
        # gsc_discover_pages（見下方），各自獨立追蹤各自的寫入路徑。
        ingestion_run_table_name="gsc_daily_totals",
        degradation=None,
        degradation_skip_reason=(
            "S2.5 discover-fix 後 gsc_discover 指向 gsc_daily_totals：全站彙總沒有"
            "page/query/device 之類的維度可拆，因此沒有『某個子集被靜默丟棄』這種降級可查——"
            "與 gsc_daily_totals 管線本身的判定同理，唯一可能的資料品質問題是整批 0 列，"
            "屬於新鮮度／空段檢查的範圍，不重複用降級規則。"
        ),
        schedule_note="門檻沿用 gsc_daily_metrics：totals 與探測查詢在同一支腳本、"
                      "同一次 run 內完成（見 ingest_gsc_search_analytics.py write_totals()），"
                      "來源延遲特性相同。",
    ),

    # ── 4c-2. GSC Search Analytics — Discover page 層（page_nodevice 組）───
    # 2026-09-04 S2.4：discover 補上不帶 device 的 page_nodevice 組合後，
    # (date, page) 列開始進 gsc_page_daily（見 gsc_surfaces.py SURFACE_COMBOS／
    # 025 device_surface_ck）。totals 與 page 層是兩個母體、兩條寫入路徑，
    # 各自要有自己的新鮮度訊號，因此不改 gsc_discover 的指向，另立本條目。
    PipelineConfig(
        key="gsc_discover_pages",
        table="gsc_page_daily",  # 一律查視圖，同 gsc_daily_metrics 的理由
        # property 必帶：gsc_daily_metrics_dim_uniq(property, search_type, date, ...) 的
        # 前綴要有 property 等值條件 planner 才會選它，不帶會退回 26s 級全表掃描
        # （見 GSC_PROPERTY 欄位註解、2026-09-04 team-lead EXPLAIN ANALYZE 實測）。
        filters=(("property", GSC_PROPERTY), ("search_type", "discover")),
        timestamp_column="date",
        max_age_hours=96 + 48,  # 沿用 gsc_daily_metrics：同一支腳本、同一次 run 內完成，來源延遲同構
        cadence_hours=24,
        cadence_label="daily",
        # lag_buffer_hours 用不到：gap_window_hours=None 讓整個第二類檢查（空段）SKIP，
        # 這個值只有 check_gaps() 會讀，填 0.0 是滿足型別要求，理由見下方 gap_skip_reason。
        lag_buffer_hours=0.0,
        gap_window_hours=None,
        gap_skip_reason=(
            "與 gsc_discover（totals）同一個成因：discover 曝光本質斷續——一篇文章進"
            "Discover 才有曝光，ingest 端只抓探測到有資料的日期，某天沒有 Discover 曝光時"
            "那天在 gsc_page_daily 沒有列是合法狀態，不是管線故障。page 層改走"
            "page_nodevice 組後這個論證不變（母體從 totals 換成 page 明細，斷續的本質"
            "沒換）。gap_window_hours 掃 30 天窗會把沒曝光的日子當空段、連紅 30 天直到"
            "滑出窗外，不是機率事件，是曝光模式的必然結果。新鮮度檢查（max_age_hours=144h）"
            "已涵蓋『作業真的停擺』，此處不重複用一個會誤報的規則去涵蓋同一件事。"
        ),
        ingestion_run_table_name="gsc_daily_metrics",
        degradation=None,
        degradation_skip_reason=(
            "discover 的 page_nodevice 組不請求 device 維度，寫入時 device 恆為 'n/a' 哨兵"
            "（025 device_surface_ck 綁死，見 gsc_surfaces.py is_device_valid()），沒有"
            "可拆的裝置子維度可能被靜默丟棄；page_nodevice 組本身也不含 query 維度"
            "（discover 是無排名 surface，同 gsc_googlenews），因此沒有除 device 以外的"
            "額外維度可查。唯一可能的資料品質問題是整批列數異常，屬於新鮮度／空段檢查的"
            "範圍，不重複用降級規則，理由結構同 gsc_googlenews。"
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
        # lag_buffer_hours 用不到：gap_window_hours=None 讓整個第二類檢查（空段）SKIP，
        # 這個值只有 check_gaps() 會讀，check_gaps 對 gap_window_hours=None 的管線
        # 第一行就直接回傳 SKIP、不會走到用 lag_buffer_hours 的那段邏輯。填 0.0
        # 是滿足型別要求（見上方欄位註解「2026-09-03 改成必填」），不是「這條管線
        # 剛好緩衝需求是 0」——這一行本身就是 team-lead 要求的「明確說明為什麼不需要」。
        lag_buffer_hours=0.0,
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

    # ── 6. AI 答案 share of voice（週跑 LLM 問答，S6.2）──────────────
    PipelineConfig(
        key="ai_sov",
        table="ai_sov_response",
        filters=(),
        # week_start 是**桶標籤**（永遠是 UTC 週一），不是 run_at。
        # 空段檢查用 _floor_to_cadence() 把週頻管線對齊到週一 00:00 做集合比對，
        # 時間戳若取 run_at（週一 06:20 之類）永遠對不上，每一週都會被判成空段——
        # 那不是門檻問題，是對齊方式本身錯了。migration 024 有 CHECK 綁死
        # week_start 必為 ISO 週一，以及 run_at 必須落在它宣稱的那一週內。
        timestamp_column="week_start",
        # ═══ max_age_hours = 192h 的推導 ═══
        #
        # 本管線**沒有來源固有延遲**：資料是作業自己在呼叫 LLM 的當下產生的，
        # 不像 CrUX/GSC 要等對方發布。所以適用「排程週期 × N」這一類公式，
        # 而不是 cwv_hourly_crux 那種「來源延遲上限 + 排程緩衝」。
        #
        # 但**不能取 N=3**（504h ≈ 3 週）：週頻管線的 ×3 意味著漏跑要三週才叫，
        # 而這份資料**無法回填**（沒辦法事後去問「上週的 LLM 會怎麼回答」），
        # 三週的洞就是三週的洞。門檻改成 1 個週期 + 一天的餘裕：
        #
        #   穩態下 week_start 的年齡從 6h（cron 週一 06:00 UTC，桶起點後 6h 才跑）
        #   漲到 174h（= 168 + 6，下一次排程前一刻）。上面再加：
        #     - GitHub Actions schedule trigger 的實測漂移上限 ~1.8h
        #       （本檔 crawl_daily 註解記錄的 104 分鐘最大相鄰間隔，同一個平台行為）
        #     - 一次 run 的執行時長（36 prompt × 3 次，帶 web_search 工具）≈ 1h
        #   → 最壞穩態年齡 ≈ 176.8h，門檻 192h 留約 15h 餘裕。
        #
        # 偵測延遲：整週漏跑後，每日跑的 data-quality-watchdog.yml 會在
        # 漏跑時點後約 28h（隔日 09:30 UTC 那一輪）把它叫出來。
        max_age_hours=168 + 24,
        cadence_hours=24 * 7,
        cadence_label="weekly",
        # ═══ gap_window_hours = 4 週的推導 ═══
        #
        # 不用 cwv_hourly_crux 的 8 週：這份資料無法回填，漏掉的那一週**永遠**
        # 補不回來，掃描窗多長，那個 FAIL 就會紅多久。8 週的窗等於一次漏跑
        # 換來兩個月的常紅告警，而常紅告警就是被忽略的告警。
        # 取 4 週的理由是它剛好等於「這個指標可判讀的最短序列長度」
        # （報告 S6.2 的判讀規則：≥4 週才談趨勢）——可判讀窗內的洞必須看得見，
        # 更舊的洞已經記錄在案且修不掉，繼續紅只有訓練大家忽略的效果。
        gap_window_hours=24 * 28,
        # ═══ lag_buffer_hours = 0.0 的推導（刻意填 0，不是漏填）═══
        #
        # 這個 buffer 的語意是「桶**關閉**後容忍多久沒資料」（見本檔尾端的
        # 長註解）。本管線的資料在桶**起點後約 6h** 就寫好了——cron 排在
        # 週一 06:00 UTC，量的是「當下」而不是「上一週」。等到那一桶關閉
        # （下週一 00:00）時，資料已經就位約 162h。沒有任何來源固有延遲、
        # 也沒有需要被容忍的寫入延遲，0.0 是這個推導的結論而不是預設值。
        #
        # ⚠ 這個 0.0 綁在「cron 排在週初」這個前提上。若之後把排程改到週末
        # （例如週日 23:00 收當週資料），資料就變成貼著桶關閉時間才寫入，
        # 這個值必須跟著改成能覆蓋 GHA 漂移 + run 時長的數字，否則每週
        # 都會在跨週那一刻誤報一次。
        lag_buffer_hours=0.0,
        ingestion_run_table_name="ai_sov_response",
        degradation=DegradationConfig(
            # grounding='ungrounded' = 這次回應**零 citation**，沒有引用任何人。
            # 這是本管線的靜默降級形狀：總列數完全正常、SoV 卻整批下滑，
            # 而真正的原因在 provider 端（模型改版、web_search 工具沒被觸發、
            # prompt 撞到安全政策），不是站方可見度變了。聚合視圖已經把
            # ungrounded 排除在 SoV 分母外，這個檢查是為了讓「排除掉的那一堆
            # 變很大」本身也會叫。
            column="grounding", mode="fallback_value", fallback_value="ungrounded",
            # ⚠ max_ratio=0.5 目前是 **provisional**：本 step 交付時沒有
            # OPENAI_API_KEY，沒有任何一次真實呼叫可以拿來估 ungrounded 的
            # 基線分布（smoke 走 FakeProvider，它的比例是寫死的參數，不是測值）。
            # 取 0.5 的論證而非測值：超過一半的回應零 citation 時，週級 SoV
            # 的分母就落在少數樣本上，那個比例已經不值得讀——這是「指標失效」
            # 的門檻，不是「稍微變差」的門檻。累積 4 週真實資料後應該用實測
            # 分布重新校準，並在報告裡記下改動的週次（同 gsc_url_inspection
            # 的 50% 門檻，那個至少有 20 筆實測墊底，這個沒有）。
            max_ratio=0.5,
            # 一週 36 prompt × 3 次 = 108 列，min_sample=30 在單週資料上就達得到；
            # 低於 30 列代表那一週的 run 根本沒跑完，該由新鮮度/空段檢查處理，
            # 不該由降級檢查對一個殘缺樣本下判斷。
            min_sample=30, sample_limit=500,
        ),
        schedule_note="門檻＝排程週期(168h)+24h 餘裕，不是週期×3——這份資料無法回填，"
                      "漏跑三週才叫等於三週的洞。gap 窗刻意只掃 4 週（可判讀序列的最短長度），"
                      "因為補不回來的洞掃再久也只是常紅。降級檢查看 grounding='ungrounded' 佔比"
                      "（零 citation 的回應），門檻 0.5 目前是 provisional、無實測墊底。",
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
