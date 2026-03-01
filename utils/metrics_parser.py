"""
metrics_parser — Google Sheets 指標擷取與解析（無 OpenAI 依賴）

提供：
- fetch_from_sheets()：從 Google Sheets 下載指定分頁 CSV
- parse_metrics_tsv()：解析 TSV 格式的 SEO 指標
- detect_anomalies()：標記核心指標與趨勢異常
- METRIC_QUERY_MAP：指標對應語意查詢的對照表
- CORE_METRICS / ALERT_THRESHOLD_* / SKIP_METRICS：閾值常數

此模組不依賴 config.py（不會觸發 OPENAI_API_KEY 驗證），
可在 qa_tools.py 和 scripts/ 中安全 import。
"""
from __future__ import annotations

import csv
import io
import logging
import re
import urllib.error
import urllib.request
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


# ── 指標閾值 ──────────────────────────────────────────
ALERT_THRESHOLD_MONTHLY = 0.15   # 月趨勢超過此閾值（絕對值）視為需要關注
ALERT_THRESHOLD_WEEKLY = 0.20    # 上週趨勢超過此閾值（絕對值）視為需要關注

# 核心指標（一定納入報告，不管趨勢如何）
CORE_METRICS = {
    "曝光", "點擊", "CTR", "有效 (Coverage)", "檢索未索引",
    "工作階段總數（七天）", "Organic Search (工作階段)",
    "Discover", "AMP (non-Rich)", "AMP Article",
    "Google News", "News(new)", "Image",
}

# 從報告中略過（系統性缺失或無意義）
SKIP_METRICS = {"Sparklines", "#N/A", ""}

# 預設 Google Sheets URL
DEFAULT_SHEETS_URL = (
    "https://docs.google.com/spreadsheets/d/1i3unCxF-rx_DF5BcunC9rYTFj6BnfTUeyuHe7_AcFlM/edit?gid=0#gid=0"
)

# ── 指標語意查詢對照表 ──────────────────────────────────
# 當指標觸發異常時，用這裡的查詢（而非泛用模板）搜尋知識庫。
# 每個指標可對應一到多條查詢字串，彼此互補，覆蓋不同知識切角。
# 未列在此表的指標會退回通用模板："{指標} 大幅{方向} 原因 怎麼處理"
METRIC_QUERY_MAP: dict[str, list[str]] = {
    # ── 核心流量 ──
    "曝光":               ["整體曝光下降代表什麼 SEO 含義", "曝光上升但點擊未同步 SERP 版位"],
    "點擊":               ["點擊率下降原因 CTR 如何改善", "點擊與曝光趨勢背離"],
    "CTR":                ["CTR 持續下降原因解讀", "如何提升 CTR 搜尋結果外觀"],
    "行動裝置點擊":        ["行動裝置流量下降 手機 SEO 問題"],
    "行動裝置曝光":        ["行動裝置曝光下降 手機可用性"],

    # ── 搜尋外觀（Rich Results）──
    "AMP (non-Rich)":    ["AMP 頁面流量下降 非焦點新聞 原因", "AMP 非 Rich 外觀變動"],
    "AMP Article":       ["AMP Article 焦點新聞流量下降 原因", "AMP 文章索引問題 SERP 展示",
                          "AMP 與 Google News 導頁關係"],
    "Video Appearance":  ["影片外觀 Video Appearance 消失 原因", "VideoObject 結構化資料 影片展示"],
    "Video":             ["Video SERP 流量下降 影片 SEO", "影片搜尋流量分析"],
    "Image":             ["圖片搜尋流量下降 Image SEO", "圖片 alt 結構化資料 圖片搜尋"],
    "FAQ":               ["FAQ rich result 消失 常見問題標記", "FAQ 流量下降 結構化資料"],
    "評論摘錄":           ["評論摘錄 Review Snippet 消失 原因", "AggregateRating 結構化資料"],
    "產品摘要":           ["產品摘要 Product 結構化資料 消失", "電商 SEO Rich result"],
    "論壇":               ["論壇 Discussions and forums 排名", "討論區 SERP 外觀"],
    "Rich":              ["Rich Result 外觀消失 結構化資料問題", "rich snippet 流量影響"],
    "Rich Ratio":        ["Rich Result 比例下降 結構化資料覆蓋率"],
    "結構化 Ratio":       ["結構化資料覆蓋率下降 哪些頁面需要補強"],
    "GPE Click (手機)":  ["Google Perspectives 手機點擊 觀點面板"],
    "GPE Imp (手機)":    ["Google Perspectives 曝光 觀點搜尋功能"],
    "GPE Click (桌機)":  ["Google Perspectives 桌機流量 觀點面板"],
    "GPE Imp  (桌機)":   ["Google Perspectives 桌機曝光"],

    # ── Discover / News ──
    "Discover":          ["Google Discover 流量下降 探索 原因", "Discover 演算法 內容策略",
                          "如何點燃 Discover 推薦文章"],
    "Google News":       ["Google News 流量下降 原因", "Google News App 導頁 AMP 關係",
                          "News 流量與 AMP Article 連動"],
    "News(new)":         ["Google News 新增流量下降", "焦點新聞 Top Stories 排名掉出"],
    "探索比例":           ["Discover 流量佔比下降 探索成長策略"],
    "新聞比例":           ["Google News 流量佔比分析", "新聞類文章比例 時事 SEO"],

    # ── 索引狀態 ──
    "有效 (Coverage)":   ["有效頁面數下降 索引減少 原因", "Coverage 有效頁下滑 如何處理"],
    "檢索未索引":         ["檢索未索引增加 原因 如何修復", "未索引頁面增加 Googlebot 封鎖",
                          "伺服器錯誤影響索引 WAF CDN 問題"],
    "已找到未索引":       ["已發現未索引頁面增加 Google 找到但不收錄 原因"],
    "重覆頁面;Google選擇": ["重複頁面 canonical 設定問題", "Google 選擇不同 canonical 原因"],
    "錯誤（伺服器錯誤）": ["伺服器錯誤 50x 影響 SEO 索引", "WAF 誤殺 Googlebot 問題"],
    "Sitemap提交並索引": ["Sitemap 索引率下降 提交問題", "Sitemap 有效頁比例"],
    "排除":              ["Search Console 排除頁面增加 noindex robots"],
    "有效/所有":         ["有效頁面佔比下降 索引效率"],
    "未索引/有效":        ["未索引與有效頁比值 索引品質"],
    "Sitemap/有效":      ["Sitemap 覆蓋率 有效頁面"],
    "GI Ratio":          ["Good Impression 良好曝光比例 Core Web Vitals 影響"],
    "Good Impresstion":  ["良好曝光體驗佔比 CWV 與 SEO 關係"],
    "GE Ratio 桌機":     ["桌機良好體驗比例 Core Web Vitals 桌機"],
    "GE Imp 桌機":       ["桌機良好曝光數 CWV 體驗指標"],

    # ── Core Web Vitals ──
    "手機 好":           ["手機 Core Web Vitals 良好比例 如何提升", "行動裝置體驗 CWV"],
    "手機 中":           ["手機 CWV 待改善 如何優先處理"],
    "手機 差":           ["手機 Core Web Vitals 差的頁面 如何修復"],
    "桌機 好":           ["桌機 Core Web Vitals 良好比例"],
    "桌機 中":           ["桌機 CWV 待改善頁面"],
    "桌機 差":           ["桌機 Core Web Vitals 差 LCP FID CLS"],
    "Mobile 索引 (內部KPI)": ["手機優先索引 Mobile-first indexing 問題"],
    "手機/有效":          ["手機版頁面佔有效頁比例 行動版索引"],
    "手機占比":           ["手機流量占比變化 行動裝置趨勢"],
    "手機良好":           ["手機 CWV 良好頁面數 體驗優化"],
    "桌機良好":           ["桌機 CWV 良好頁面數"],

    # ── 影片索引 ──
    "影片網頁數-已編入索引": ["影片頁面索引數下降 VideoObject 結構化資料問題"],
    "影片網頁數-未編入索引": ["影片頁面未索引增加 影片 SEO 索引問題"],
    "多媒體比例":          ["多媒體內容 SEO 圖片影片比例"],

    # ── 結構化資料 ──
    "AMP 索引(有效）":    ["AMP 有效索引數下降 AMP 技術問題"],
    "AMP 索引(警告）":    ["AMP 警告增加 AMP Error 修復方式"],
    "AMP Ratio":          ["AMP 頁面比例 AMP 策略"],
    "AMP Article Ratio":  ["AMP Article 比例 焦點新聞覆蓋率"],
    "標誌 (Logo)":        ["Logo 結構化資料 品牌外觀"],
    "導航標記":            ["Breadcrumb 導航標記結構化資料 麵包屑"],
    "影片":               ["影片結構化資料 VideoObject 覆蓋率"],
    "討論區":              ["討論區 結構化資料 DiscussionForums"],
    "圖片中繼資料":        ["圖片 metadata alt EXIF SEO"],
    "資料頁面":            ["資料類型頁面結構化資料"],
    "查看摘要（review）":  ["Review Snippet 評論摘要結構化資料"],

    # ── 連結 ──
    "外部連結":            ["外部連結分佈 backlink 質量分析"],
    "100 (連結)":          ["100 個連結的頁面 重要頁面連結數"],
    "200 (連結)":          ["200 個連結的頁面"],
    "100 (網域)":          ["100 個連結的網域 referring domain"],
    "200 (網域)":          ["200 個 referring domain 外部連結增加"],
    "100 (目標網頁)":      ["100 個目標網頁被連結 重要落地頁"],
    "200 (目標網頁)":      ["200 個目標網頁 連結架構優化"],
    "內部連結":            ["內部連結架構優化 如何提升頁面權重", "每頁內部連結數量標準"],
    "每頁內部連結":         ["每頁內部連結數量 內部連結密度"],
    "內部連結分布":         ["內部連結分佈不均 重要頁面連結不足"],
    "每頁外部連結":         ["每頁外部連結數量"],
    "外部連結分布":         ["外部連結分佈分析 連結策略"],

    # ── 爬蟲 ──
    "最近一天的檢索數":    ["Google 爬蟲抓取頻率 Crawl Budget", "每日檢索數下降原因"],
    "檢索數 (90 days)":   ["90 天檢索趨勢 Crawl Budget 管理"],
    "回應時間 (最近一天)": ["伺服器回應時間 TTFB 影響 SEO 索引"],
    "回應時間 (90天平均)": ["伺服器平均回應時間 速度優化"],
    "週平均檢索數":        ["每週平均爬取量 Crawl Budget 趨勢"],
    "週平均回應時間":      ["每週平均回應時間 速度問題"],
    "HTML 檢索比例":       ["HTML 頁面爬取比例 爬蟲效率"],
    "HTML 檢索/有效":      ["HTML 爬取與有效索引比 爬取效率"],
    "新網頁":              ["新頁面被 Google 發現索引速度 新內容 SEO"],
    "流量頁面/有效":        ["流量頁面佔有效頁比例 哪些頁面帶流量"],
    "流量頁面 (新內部KPI)": ["有流量的頁面數 內容健康度 KPI"],
    "檢索數/有效":          ["爬取與索引比 Crawl Budget 效率"],
    "/api/rss/news":       ["RSS Feed 被爬取 結構性流量"],
    "/rss/new-articles":   ["RSS 新文章 Feed 爬取狀況"],
    "/rss/news":           ["RSS News Feed 索引"],

    # ── URL 路徑 ──
    "/":                   ["首頁 SEO 排名 品牌搜尋 首頁流量下降"],
    "/article/":           ["文章頁面流量下降 內容頁 SEO", "/article 路徑索引異常"],
    "/post":               ["Post 頁面 SEO 流量變化"],
    "/user":               ["用戶頁面 /user 流量下降 索引策略 noindex"],
    "/salon/":             ["Salon 沙龍頁面 SEO 流量", "社群頁面 SEO"],
    "/tags/":              ["標籤頁 tags 流量 SEO 標籤頁索引策略"],
    "/search":             ["站內搜尋頁 /search 應否索引 noindex"],
    "/event/":             ["活動頁面 event SEO"],
    "/home":               ["首頁變體 /home 路徑"],
    "/introduce":          ["介紹頁 introduce 索引"],

    # ── 全網域分析 ──
    "全網域":              ["全網域 URL 總數 網站規模"],
    "檢索未索引 (全部)":   ["全網域未索引頁面分析"],
    "/en/":                ["英文頁面 /en/ SEO 多語系 hreflang", "英文頁面 core update 影響"],
    "/tag/":               ["標籤頁 tag 流量 索引策略"],
    "/user/":              ["用戶頁 user SEO 是否應 noindex"],
    "總合":                ["關鍵指標總合分析"],
    "差距":                ["指標差距分析 目標 vs 實際"],

    # ── KW 追蹤 ──
    "KW: 影評":            ["影評關鍵字 SEO 排名 電影評論"],
    "KW: 電影":            ["電影關鍵字 SEO 流量趨勢"],
    "KW: 評價":            ["評價關鍵字 SEO 用戶意圖"],
    "KW: 攻略":            ["攻略關鍵字 SEO 遊戲攻略流量"],
    "KW: 股":              ["股票關鍵字 財經 SEO"],
    "KW: 劇":              ["韓劇台劇關鍵字 SEO 追劇流量"],
    "營運 KW：保養":        ["保養關鍵字 美妝 SEO"],
    "營運 KW：必買":        ["必買關鍵字 購物 SEO"],

    # ── GA / 流量來源 ──
    "工作階段總數（七天）": ["工作階段總數下降 整體流量分析", "流量來源結構分析"],
    "Organic Search (工作階段)": ["Organic Search 工作階段下降 自然搜尋流量",
                                  "GSC 點擊 vs GA 工作階段落差"],
    "Direct  (工作階段)":  ["Direct 流量與 Discover 計算關係", "GSC Discover vs GA Direct"],
    "Organic Social  (工作階段)": ["社群流量 Organic Social 趨勢"],
    "Referral (工作階段)": ["Referral 流量來源分析"],
    "GPT (工作階段)":      ["AI 引流 ChatGPT 流量來源 AI SEO"],
    "Gemini":              ["Gemini AI 搜尋引流 AI overview SEO"],
    "Perplexity":          ["Perplexity AI 搜尋流量"],
    "AI 占比":             ["AI 來源流量佔比 AI SEO 趨勢 即時新聞"],
    "Google 導流":         ["Google 導流量 搜尋導流比例"],
    "Google 導流占比":     ["Google 導流佔比下降 搜尋依賴度"],
    "GSC 搜尋/GA 搜尋":    ["GSC 點擊與 GA Organic 落差原因 AMP 流量歸因"],
    "GSC 探索/GA Direct":  ["Discover 流量被歸到 GA Direct 流量歸因問題"],
    "搜尋流量占比 (工作階段)": ["搜尋流量比例 SEO 依賴度分析", "搜尋流量比例趨勢"],
    "全部流量":            ["全站流量趨勢分析"],
    "其他流量":            ["非 Google 流量來源"],
    "其他流量（新使用者）": ["新用戶流量來源 SEO 成長指標"],
    "Google Analytics":    ["GA4 資料設定問題 追蹤問題"],
    "GSC 最後日":          ["GSC 資料延遲 最後資料日"],

    # ── 內容指標 ──
    "總文章數":            ["文章總量與 SEO 表現關係 內容規模"],
    "當週文章數":          ["本週新文章數量 內容供給 SEO 影響"],
    "文章 vs 流量":        ["文章數量與流量成長相關性分析"],
    "首頁占比":            ["首頁流量佔比 品牌搜尋"],
    "文章占比":            ["文章頁面流量佔比 內容頁貢獻"],
    "專題佔比":            ["專題頁面流量佔比 主題集合 SEO"],
    "沙龍佔比":            ["沙龍頁面流量佔比"],
    "搜尋標籤占比":        ["搜尋標籤頁流量佔比 標籤 SEO"],
    "一般點擊":            ["一般藍色連結點擊 非外觀型流量"],
    "一般點擊佔比":        ["一般點擊佔比 外觀紅利依賴度"],
    "搜尋點擊流量圖 (E3)": ["E3 區塊搜尋點擊流量 GSC"],
    "網頁條件/總流量比":   ["有流量頁面佔比 長尾流量分佈"],

    # ── 體驗 / CWV 比率 ──
    "良好/有效":           ["良好 CWV 頁面佔有效頁比 體驗 KPI"],
    "強化/有效":           ["結構化資料強化頁面佔比"],
    "良好/流量":           ["有流量且 CWV 良好的頁面比例 重點優化"],
    "良好 (100%)":         ["CWV 100% 良好頁面數"],
    "強化/有流量":         ["有流量且有結構化資料頁面"],
    "強化(All)/有流量":    ["所有結構化強化頁面與流量頁面比"],
    "點擊流量/流量頁面":   ["每個流量頁面的平均點擊 SEO 效率"],

    # ── 爬取驗證 ──
    "檢索未索引驗證時間":  ["Search Console 未索引驗證時間 手動驗證"],
    "檢索未索引失敗時間":  ["未索引修復失敗 驗證不通過原因"],
    "檢索未索引失敗數目":  ["未索引失敗數量上升 索引問題規模"],

    # ── Google News 訂閱 ──
    "Google News 訂閱":    ["Google News Publisher Center 訂閱數 新聞 SEO"],
}


# ──────────────────────────────────────────────────────
# Google Sheets 自動擷取
# ──────────────────────────────────────────────────────

_SHEET_ID_RE = re.compile(r"^[a-zA-Z0-9_-]{10,60}$")
_GID_RE = re.compile(r"^\d{1,10}$")
_MAX_RESPONSE_BYTES = 10 * 1024 * 1024  # 10 MB 上限
_ALLOWED_HOST = "docs.google.com"


def _validate_sheet_id(sheet_id: str) -> None:
    if not _SHEET_ID_RE.match(sheet_id):
        raise ValueError(f"sheet_id 格式不合法：{sheet_id!r}")


def _validate_gid(gid: str) -> None:
    if not _GID_RE.match(gid):
        raise ValueError(f"gid 格式不合法：{gid!r}")


def _parse_sheets_url(url: str) -> tuple[str, str]:
    """從 Google Sheets URL 解析 sheet_id 與 gid"""
    parsed = urlparse(url)
    if parsed.netloc != _ALLOWED_HOST:
        raise ValueError(
            f"不允許的 Sheets 主機：{parsed.netloc!r}，僅允許 {_ALLOWED_HOST!r}"
        )
    m = re.search(r"/spreadsheets/d/([a-zA-Z0-9_-]+)", url)
    if not m:
        raise ValueError(f"無法從 URL 解析 sheet ID：{url}")
    sheet_id = m.group(1)
    _validate_sheet_id(sheet_id)
    gid_match = re.search(r"[?&#]gid=([0-9]+)", url)
    gid = gid_match.group(1) if gid_match else "0"
    _validate_gid(gid)
    return sheet_id, gid


def _find_gid_by_tab_name(sheet_id: str, tab: str) -> str | None:
    """在 Sheets HTML 裡找 tab 名稱對應的 gid（不需 OAuth）"""
    _validate_sheet_id(sheet_id)
    try:
        url = f"https://{_ALLOWED_HOST}/spreadsheets/d/{sheet_id}/edit"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status != 200:
                return None
            html = resp.read(_MAX_RESPONSE_BYTES).decode("utf-8", errors="ignore")
        m = re.search(
            r'"sheetId":(\d+)[^}]*"title":"' + re.escape(tab) + r'"',
            html,
        )
        if m:
            gid = m.group(1)
            _validate_gid(gid)
            return gid
        m2 = re.search(
            r'"title":"' + re.escape(tab) + r'"[^}]*"sheetId":(\d+)',
            html,
        )
        if m2:
            gid = m2.group(1)
            _validate_gid(gid)
            return gid
    except (urllib.error.URLError, urllib.error.HTTPError, OSError, TimeoutError) as e:
        logger.warning("_find_gid_by_tab_name 失敗，tab=%r，err=%s", tab, e)
    return None


def fetch_from_sheets(url_or_id: str, tab: str = "vocus") -> str:
    """
    從 Google Sheets 下載指定分頁的 CSV 並轉為 TSV 字串。
    試算表須設為「任何知道連結者可檢視」。
    """
    if url_or_id.startswith("http"):
        sheet_id, url_gid = _parse_sheets_url(url_or_id)
        if url_gid != "0":
            gid = url_gid
        else:
            gid = _find_gid_by_tab_name(sheet_id, tab) or "0"
    else:
        _validate_sheet_id(url_or_id)
        sheet_id = url_or_id
        gid = _find_gid_by_tab_name(sheet_id, tab) or "0"

    _validate_gid(gid)
    csv_url = (
        f"https://{_ALLOWED_HOST}/spreadsheets/d/{sheet_id}"
        f"/export?format=csv&id={sheet_id}&gid={gid}"
    )
    logger.info("下載: %s", csv_url)
    req = urllib.request.Request(csv_url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        if resp.status != 200:
            raise ValueError(f"Google Sheets 回應異常，HTTP 狀態碼：{resp.status}")
        raw = resp.read(_MAX_RESPONSE_BYTES)
    text = raw.decode("utf-8-sig")

    reader = csv.reader(io.StringIO(text))
    lines = ["\t".join(row) for row in reader]
    return "\n".join(lines)


# ──────────────────────────────────────────────────────
# TSV 解析
# ──────────────────────────────────────────────────────

def _parse_value(raw: str) -> float | str | None:
    """把試算表格子的原始字串轉成數值 / None"""
    v = raw.strip()
    if v in ("#N/A", "#DIV/0!", "#REF!", "#VALUE!", ""):
        return None
    if v.endswith("%"):
        try:
            return float(v.rstrip("%")) / 100
        except ValueError:
            return None
    try:
        return float(v.replace(",", ""))
    except ValueError:
        return v


def parse_metrics_tsv(text: str) -> dict[str, dict]:
    """
    解析從 Google 試算表複製的 TSV。

    期望格式（第一行為 header，之後每行 metric_name + 數值）：
        （空）\t月趨勢\t上週\tMax\tMin\tSparklines\t日期1\t日期2
        曝光\t-3.61%\t-26.09%\t65,358,724\t48,305,965\t\t48,305,965\t65,358,724

    回傳 dict：metric_name → {monthly, weekly, max, min, latest, previous, latest_date, previous_date}
    """
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        return {}

    header_idx = 0
    for i, line in enumerate(lines):
        if "月趨勢" in line or "上週" in line:
            header_idx = i
            break

    header_cols = lines[header_idx].split("\t")
    date_cols = [c.strip() for c in header_cols if re.match(r"\d+/\d+/\d+", c.strip())]
    latest_date = date_cols[0] if date_cols else ""
    previous_date = date_cols[1] if len(date_cols) > 1 else ""

    def _safe_col(cols: list[str], idx: int):
        return _parse_value(cols[idx]) if idx < len(cols) else None

    metrics: dict[str, dict] = {}
    for line in lines[header_idx + 1:]:
        cols = line.split("\t")
        if not cols or not cols[0].strip():
            continue
        name = cols[0].strip()
        if name in SKIP_METRICS:
            continue

        metrics[name] = {
            "monthly":       _safe_col(cols, 1),
            "weekly":        _safe_col(cols, 2),
            "max":           _safe_col(cols, 3),
            "min":           _safe_col(cols, 4),
            "latest":        _safe_col(cols, 6) if len(cols) > 6 else None,
            "previous":      _safe_col(cols, 7) if len(cols) > 7 else None,
            "latest_date":   latest_date,
            "previous_date": previous_date,
        }

    return metrics


# ──────────────────────────────────────────────────────
# 異常偵測
# ──────────────────────────────────────────────────────

def detect_anomalies(metrics: dict[str, dict]) -> list[dict]:
    """
    找出需要關注的指標，分為：
    - CORE：核心指標（不管趨勢都納入）
    - ALERT_UP / ALERT_DOWN：月趨勢或週趨勢超過閾值
    """
    alerts = []

    for name, m in metrics.items():
        monthly = m.get("monthly")
        weekly = m.get("weekly")

        if name in CORE_METRICS:
            alerts.append({**m, "name": name, "flag": "CORE"})
            continue

        monthly_abs = abs(monthly) if isinstance(monthly, float) else 0
        weekly_abs = abs(weekly) if isinstance(weekly, float) else 0

        if monthly_abs >= ALERT_THRESHOLD_MONTHLY or weekly_abs >= ALERT_THRESHOLD_WEEKLY:
            flag = "ALERT_UP" if (monthly or 0) > 0 else "ALERT_DOWN"
            alerts.append({**m, "name": name, "flag": flag})

    return alerts
