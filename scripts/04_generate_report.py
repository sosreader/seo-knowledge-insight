"""
步驟 4：依據每週 SEO 指標 + Q&A 知識庫，產生分析報告

使用方式：
    # 直接串 Google Sheets URL（最簡）：
    python scripts/04_generate_report.py --input "https://docs.google.com/spreadsheets/d/..."

    # 指定分頁（預設取 vocus）：
    python scripts/04_generate_report.py --input "https://..." --tab vocus

    # 從本機檔案讀（手動從試算表複製存檔用）：
    python scripts/04_generate_report.py --input metrics.tsv

    # 輸出到指定路徑：
    python scripts/04_generate_report.py --input "https://..." --output report.md
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import logging
import re
import sys
import urllib.request
from datetime import datetime
from urllib.parse import urlparse
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)

# ── 路徑修正 ─────────────────────────────────────────
try:
    import config
    from utils.openai_helper import get_embeddings
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    import config
    from utils.openai_helper import get_embeddings

from openai import OpenAI


# 預設 Google Sheets URL（可在 .env 設定 SHEETS_URL 覆蓋）
DEFAULT_SHEETS_URL = "https://docs.google.com/spreadsheets/d/1fzttLHJfl2Tnecxg0PDKsTmj0-PT5eSsYOivTI6wRdo"

# ── 指標閾值 ──────────────────────────────────────────
# 月趨勢超過此閾值（絕對值）視為需要關注
ALERT_THRESHOLD_MONTHLY = 0.15   # 15%
# 上週趨勢超過此閾值（絕對值）視為需要關注
ALERT_THRESHOLD_WEEKLY = 0.20    # 20%

# 核心指標（一定納入報告，不管趨勢如何）
CORE_METRICS = {
    "曝光", "點擊", "CTR", "有效 (Coverage)", "檢索未索引",
    "工作階段總數（七天）", "Organic Search (工作階段)",
    "Discover", "AMP (non-Rich)", "AMP Article",
    "Google News", "News(new)", "Image",
}

# 從報告中略過（系統性缺失或無意義）
SKIP_METRICS = {"Sparklines", "#N/A", ""}

# ── 指標語意查詢對照表 ──────────────────────────────────
# 當指標觸發異常時，用這裡的查詢（而非泛用模板）來搜尋知識庫。
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

    # 全網域分析
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
    """驗證 sheet_id 格式，防止注入攻擊。"""
    if not _SHEET_ID_RE.match(sheet_id):
        raise ValueError(f"sheet_id 格式不合法：{sheet_id!r}")


def _validate_gid(gid: str) -> None:
    """驗證 gid 為純數字，防止注入攻擊。"""
    if not _GID_RE.match(gid):
        raise ValueError(f"gid 格式不合法：{gid!r}")


def _parse_sheets_url(url: str) -> tuple[str, str]:
    """從 Google Sheets URL 解析 sheet_id 與 gid"""
    parsed = urlparse(url)
    if parsed.netloc != _ALLOWED_HOST:
        raise ValueError(f"不允許的 Sheets 主機：{parsed.netloc!r}，僅允許 {_ALLOWED_HOST!r}")
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
        # 格式："sheetId":123456,"title":"vocus"
        m = re.search(
            r'"sheetId":(\d+)[^}]*"title":"' + re.escape(tab) + r'"',
            html,
        )
        if m:
            gid = m.group(1)
            _validate_gid(gid)
            return gid
        # 備案：title 在前
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
        # URL 已含非預設 gid → 直接用；否則依 tab 名稱查
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
    print(f"   下載: {csv_url}")
    req = urllib.request.Request(csv_url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        if resp.status != 200:
            raise ValueError(f"Google Sheets 回應異常，HTTP 狀態碼：{resp.status}")
        raw = resp.read(_MAX_RESPONSE_BYTES)
    # Sheets CSV 為 UTF-8-BOM
    text = raw.decode("utf-8-sig")

    # CSV → TSV：使用 csv 模組正確處理含逗號的數值（如 "1,234,567"）
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
    # 百分比
    if v.endswith("%"):
        try:
            return float(v.rstrip("%")) / 100
        except ValueError:
            return None
    # 數字（可能含逗號）
    try:
        return float(v.replace(",", ""))
    except ValueError:
        return v  # 保留原始字串（如日期）


def parse_metrics_tsv(text: str) -> dict[str, dict]:
    """
    解析從 Google 試算表複製的 TSV。

    期望格式（第一行為 header，之後每行 metric_name + 數值）：
        （空）\t月趨勢\t上週\tMax\tMin\tSparklines\t日期1\t日期2
        曝光\t-3.61%\t-26.09%\t65,358,724\t48,305,965\t\t48,305,965\t65,358,724

    回傳 dict： metric_name → {monthly, weekly, max, min, latest, previous, latest_date, previous_date}
    """
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        return {}

    # 找 header 行（包含「月趨勢」或「上週」）
    header_idx = 0
    for i, line in enumerate(lines):
        if "月趨勢" in line or "上週" in line:
            header_idx = i
            break

    header_cols = lines[header_idx].split("\t")
    # 找日期欄（通常是 col 5, 6，即 header_cols[5], header_cols[6]）
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
            "monthly":      _safe_col(cols, 1),
            "weekly":       _safe_col(cols, 2),
            "max":          _safe_col(cols, 3),
            "min":          _safe_col(cols, 4),
            "latest":       _safe_col(cols, 6) if len(cols) > 6 else None,
            "previous":     _safe_col(cols, 7) if len(cols) > 7 else None,
            "latest_date":  latest_date,
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

        # 核心指標：一定加入
        if name in CORE_METRICS:
            alerts.append({**m, "name": name, "flag": "CORE"})
            continue

        # 趨勢異常
        monthly_abs = abs(monthly) if isinstance(monthly, float) else 0
        weekly_abs = abs(weekly) if isinstance(weekly, float) else 0

        if monthly_abs >= ALERT_THRESHOLD_MONTHLY or weekly_abs >= ALERT_THRESHOLD_WEEKLY:
            flag = "ALERT_UP" if (monthly or 0) > 0 else "ALERT_DOWN"
            alerts.append({**m, "name": name, "flag": flag})

    return alerts


# ──────────────────────────────────────────────────────
# Q&A 語意搜尋
# ──────────────────────────────────────────────────────

def _load_qa_database() -> list[dict]:
    """優先讀最終版，否則用原始版"""
    final = config.OUTPUT_DIR / "qa_final.json"
    raw = config.OUTPUT_DIR / "qa_all_raw.json"

    if final.exists():
        data = json.loads(final.read_text(encoding="utf-8"))
        qas = data.get("qa_database", [])
        # 若只跑了測試批次（<50），改用原始版
        if len(qas) >= 50:
            return qas

    if raw.exists():
        data = json.loads(raw.read_text(encoding="utf-8"))
        return data.get("qa_pairs", [])

    return []


def _load_persisted_embeddings(qa_count: int) -> np.ndarray | None:
    """載入 Step 3 持久化的 embedding，若不存在或數量不匹配則回傳 None。"""
    emb_path = config.OUTPUT_DIR / "qa_embeddings.npy"
    if not emb_path.exists():
        return None
    emb = np.load(emb_path)
    if emb.shape[0] != qa_count:
        print(f"   ⚠️  Embedding 數量 ({emb.shape[0]}) 與 Q&A 數量 ({qa_count}) 不匹配，重新計算")
        return None
    return emb


def _compute_keyword_boost(
    queries: list[str],
    qa_pairs: list[dict],
    boost: float | None = None,
    max_hits: int | None = None,
) -> np.ndarray:
    """
    Hybrid Search 關鍵字雙向匹配 boost。
    匹配方式（優先序）：
      1. kw 完整出現在 query 中（正向）
      2. query 的 token 出現在 kw 中（反向）
      3. kw 的 token 出現在 query 中
      4. 中文 bigram（前 2 字）弱命中（給 partial 分）
    回傳 shape = (n_queries, n_qa) 的 boost 矩陣。
    """
    boost = boost if boost is not None else config.KW_BOOST
    max_hits = max_hits if max_hits is not None else config.KW_BOOST_MAX_HITS
    partial = config.KW_BOOST_PARTIAL

    boost_matrix = np.zeros((len(queries), len(qa_pairs)), dtype=np.float32)

    for qi, query in enumerate(queries):
        query_lower = query.lower()
        query_tokens = {t for t in query_lower.split() if len(t) >= 2}
        for ji, qa in enumerate(qa_pairs):
            total_hits = 0.0
            for kw in qa.get("keywords", []):
                kw_lower = kw.lower()
                kw_tokens = {t for t in kw_lower.split() if len(t) >= 2}
                if kw_lower in query_lower:
                    total_hits += 1
                elif any(t in kw_lower for t in query_tokens):
                    total_hits += 1
                elif any(t in query_lower for t in kw_tokens):
                    total_hits += 1
                elif len(kw_lower) >= 2 and kw_lower[:2] in query_lower:
                    total_hits += (partial / boost) if boost else 0
            if total_hits > 0:
                boost_matrix[qi, ji] = boost * min(total_hits, max_hits)

    return boost_matrix


def find_relevant_qas_multi(
    queries: list[str],
    qa_pairs: list[dict],
    top_k_per_query: int = 3,
    total_max: int = 15,
    min_score: float = 0.28,
) -> list[dict]:
    """
    多查詢版（Hybrid Search）：針對每個異常指標分別做 embedding 搜尋，
    並結合關鍵字精確匹配 boost，取各查詢 top_k 結果後合併去重。
    回傳的每筆 Q&A 帶有 `_queries` 欄位，記錄哪些查詢命中了它。
    """
    if not qa_pairs or not queries:
        return []

    # 嘗試載入持久化 embedding（避免重算）
    persisted_embs = _load_persisted_embeddings(len(qa_pairs))
    if persisted_embs is not None:
        print("   ✨ 使用持久化 embedding（免重算）")
        # 只需 embed queries
        query_embeddings = get_embeddings(queries)
        query_embs = np.array(query_embeddings)
        qa_embs = persisted_embs
    else:
        # Fallback: 一次批次 embed 所有 queries + 所有 QA 問題
        questions = [qa.get("question", "") for qa in qa_pairs]
        all_texts = queries + questions
        all_embeddings = get_embeddings(all_texts)
        query_embs = np.array(all_embeddings[: len(queries)])
        qa_embs = np.array(all_embeddings[len(queries) :])

    qa_norm = qa_embs / (np.linalg.norm(qa_embs, axis=1, keepdims=True) + 1e-8)
    q_norm = query_embs / (np.linalg.norm(query_embs, axis=1, keepdims=True) + 1e-8)
    # 語意相似度矩陣
    score_matrix = q_norm @ qa_norm.T  # (n_queries, n_qa)

    # Hybrid: 加上關鍵字 boost
    keyword_boost = _compute_keyword_boost(queries, qa_pairs)
    score_matrix = score_matrix + keyword_boost

    # 收集每個 query 的 top-k
    collected: dict[int, dict] = {}  # qa_index -> 結果 dict
    for qi, query in enumerate(queries):
        scores = score_matrix[qi]
        top_indices = np.argsort(scores)[::-1][:top_k_per_query]
        for idx in top_indices:
            if scores[idx] < min_score:
                continue
            if idx not in collected:
                collected[idx] = {
                    **qa_pairs[idx],
                    "_score": float(scores[idx]),
                    "_queries": [query],
                }
            else:
                # 同一 Q&A 被多個 query 命中 → 更新最高分 + 累積 queries
                if scores[idx] > collected[idx]["_score"]:
                    collected[idx]["_score"] = float(scores[idx])
                collected[idx]["_queries"].append(query)

    # 依最高分排序，取前 total_max
    results = sorted(collected.values(), key=lambda x: -x["_score"])
    return results[:total_max]


def _rerank_qas(
    candidates: list[dict],
    context_summary: str,
    top_k: int,
) -> list[dict]:
    """
    LLM Reranker：用 gpt-5-mini 從候選 Q&A 中選出對當週指標摘要最有幫助的 top_k 筆。
    以結構化輸出回傳排序後的 index 陣列，失敗時 fallback 回原有排序。
    """
    if len(candidates) <= top_k:
        return candidates  # 候選數量不足，不須 rerank

    client = OpenAI(api_key=config.OPENAI_API_KEY)

    # 建立候選清單（截短 answer 節省 token）
    numbered = []
    for i, qa in enumerate(candidates):
        ans_snippet = (qa.get("answer") or "")[:200].replace("\n", " ")
        numbered.append(f"[{i}] Q: {qa['question']}\n    A（節錄）: {ans_snippet}")
    candidates_text = "\n\n".join(numbered)

    # 截短 context 避免 token 過多
    ctx = context_summary[:600] if len(context_summary) > 600 else context_summary

    prompt = (
        f"本週 SEO 指標摘要：\n{ctx}\n\n"
        f"以下是 {len(candidates)} 筆候選 Q&A（編號 0–{len(candidates)-1}）：\n\n"
        f"{candidates_text}\n\n"
        f"請從中選出對解讀本週指標最有直接幫助的 {top_k} 筆，"
        f"以重要性遞減順序回傳 index 陣列（JSON），例如 {{\"ranked\": [3, 0, 5, ...]}}。"
        f"只回傳 JSON，不要說明。"
    )

    try:
        resp = client.chat.completions.create(
            model="gpt-5-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            max_completion_tokens=256,
        )
        raw = resp.choices[0].message.content or "{}"
        ranked_indices: list[int] = json.loads(raw).get("ranked", [])
        # 過濾合法 index，補足 top_k
        valid = [i for i in ranked_indices if isinstance(i, int) and 0 <= i < len(candidates)]
        # 補入未被選中的（按原分數順序），確保回傳剛好 top_k 筆
        seen = set(valid)
        for i in range(len(candidates)):
            if i not in seen:
                valid.append(i)
        reranked = [candidates[i] for i in valid[:top_k]]
        print(f"   🎯 Reranker 完成：{len(candidates)} → {len(reranked)} 筆")
        return reranked
    except Exception as e:
        print(f"   ⚠️  Reranker 失敗（{e}），使用原始排序")
        return candidates[:top_k]


# ──────────────────────────────────────────────────────
# 格式化輔助
# ──────────────────────────────────────────────────────

def _fmt_pct(v) -> str:
    if v is None:
        return "N/A"
    if isinstance(v, float):
        sign = "+" if v > 0 else ""
        return f"{sign}{v*100:.1f}%"
    return str(v)


def _fmt_num(v) -> str:
    if v is None:
        return "N/A"
    if isinstance(v, float):
        if v >= 1_000_000:
            return f"{v/1_000_000:.2f}M"
        if v >= 1_000:
            return f"{v:,.0f}"
        # 判斷是比例還是數值
        if abs(v) <= 5:
            return f"{v:.4f}"
        return f"{v:.1f}"
    return str(v)


def _build_metrics_summary(alerts: list[dict]) -> str:
    """把關注指標整理成文字摘要，供 LLM 閱讀"""
    lines = []

    core = [a for a in alerts if a["flag"] == "CORE"]
    alert_down = [a for a in alerts if a["flag"] == "ALERT_DOWN"]
    alert_up = [a for a in alerts if a["flag"] == "ALERT_UP"]

    if core:
        lines.append("【核心指標】")
        for m in core:
            lines.append(
                f"  {m['name']}: 最新 {_fmt_num(m['latest'])} | "
                f"月趨勢 {_fmt_pct(m['monthly'])} | 週趨勢 {_fmt_pct(m['weekly'])}"
            )

    if alert_down:
        lines.append("\n【顯著下滑（月趨勢）】")
        for m in sorted(alert_down, key=lambda x: (x.get("monthly") or 0)):
            lines.append(
                f"  {m['name']}: {_fmt_pct(m['monthly'])} (月) / {_fmt_pct(m['weekly'])} (週)"
            )

    if alert_up:
        lines.append("\n【顯著上升（月趨勢）】")
        for m in sorted(alert_up, key=lambda x: -(x.get("monthly") or 0)):
            lines.append(
                f"  {m['name']}: {_fmt_pct(m['monthly'])} (月) / {_fmt_pct(m['weekly'])} (週)"
            )

    return "\n".join(lines)


# ──────────────────────────────────────────────────────
# LLM 報告產生
# ──────────────────────────────────────────────────────

REPORT_SYSTEM_PROMPT = """\
你是資深 SEO 分析師，任務是把本週的指標變化「翻譯成意義」，並用過去顧問會議累積的 Q&A 知識庫作為佐證。

重要原則：
- 用戶可以直接看 Google Sheets，**不需要你重複數字**。
- 每一個觀察必須說明「這代表什麼」「為什麼發生」「應該怎麼做」。
- 每個 insight 都應盡量引用【Q&A 知識庫】的具體內容作為依據，格式：（參考：「{Q&A 的關鍵句}」）
- 如果知識庫沒有直接對應，請根據 SEO 原理推論，並標明「（推論）」。
- 避免泛泛的 SEO 建議；結合本週資料的具體變化給出針對性意見。
- 引用知識庫時，請同時標註原始會議來源（標題+日期），方便讀者追溯驗證。

報告格式（Markdown，用繁體中文，技術術語保留英文）：

## 本週核心訊號
（3-4 點，每點說明一個重要的「現象 → 意義 → 知識庫怎麼說」，不提數字）

## 異常指標解讀
（針對顯著上升 / 下滑的指標，逐一解釋可能的因果機制，重點引用知識庫）

## 本週行動清單
（3 條具體 Todo，每條注明依據是哪個 Q&A 的建議或觀察）

## 直接引用知識庫
（原文引用 1-2 個本週最相關的 Q&A 問答，格式：**Q**：… / **A（節錄）**：… / **來源**：…）
"""


def generate_report(metrics_summary: str, relevant_qas: list[dict], metrics_date: str) -> str:
    client = OpenAI(api_key=config.OPENAI_API_KEY)

    # 知識庫：讓每條 Q&A 盡量完整，並標示被哪些指標查詢命中（幫助 LLM 知道關聯性）
    qa_context = ""
    if relevant_qas:
        qa_context = "\n\n【Q&A 知識庫（來自歷次 SEO 顧問會議記錄）】\n"
        qa_context += "（以下知識由指標異常查詢匹配，括號內是觸發此 Q&A 的指標信號）\n"
        for i, qa in enumerate(relevant_qas[:12], 1):
            triggered = "、".join(qa.get("_queries", [])[:3])
            snippet = qa["answer"][:600] + ("..." if len(qa["answer"]) > 600 else "")
            # 溯源資訊：讓報告讀者可以追溯到原始會議
            source_title = qa.get("source_title", "")
            source_date = qa.get("source_date", "")
            source_info = ""
            if source_title or source_date:
                parts = [p for p in [source_title, source_date] if p]
                source_info = f"來源：{'、'.join(parts)}\n"
            qa_context += (
                f"\n[{i}] 觸發信號：{triggered}\n"
                f"{source_info}"
                f"Q: {qa['question']}\n"
                f"A: {snippet}\n"
            )

    user_msg = (
        f"報告日期：{metrics_date}\n\n"
        f"【本週指標摘要】（數字僅供 LLM 判斷方向，報告中請勿重複羅列）\n"
        f"{metrics_summary}"
        f"{qa_context}"
    )

    response = client.chat.completions.create(
        model=config.OPENAI_MODEL,
        messages=[
            {"role": "system", "content": REPORT_SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        max_completion_tokens=16384,  # gpt-5 推理模型：reasoning + output 共享，需預留足夠空間
    )

    msg = response.choices[0].message
    content = msg.content

    # gpt-5 系列可能將內容放在 reasoning_content（thinking output）
    if not content:
        reasoning = getattr(msg, "reasoning_content", None)
        if reasoning:
            print(f"   ⚠️  content 為空，嘗試使用 reasoning_content（{len(reasoning)} chars）")
            content = reasoning
        else:
            print(f"   ❌ finish_reason={response.choices[0].finish_reason}")
            print(f"   ❌ refusal={getattr(msg, 'refusal', None)}")
            print(f"   ❌ msg fields: {getattr(msg, 'model_fields_set', None)}")

    return content or "（報告產生失敗）"


# ──────────────────────────────────────────────────────
# 主程式
# ──────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="產生每週 SEO 分析報告")
    parser.add_argument(
        "--input", "-i",
        type=str,
        default=None,
        help="Google Sheets URL 或本機 TSV 路徑。不指定則用 config.SHEETS_URL 或預設 URL。",
    )
    parser.add_argument(
        "--tab",
        type=str,
        default="vocus",
        help="Google Sheets 分頁名稱（預設: vocus）",
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=None,
        help="輸出 Markdown 報告路徑。預設：output/report_YYYYMMDD.md",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=15,
        help="從知識庫最多取幾個相關 Q&A（預設 15）",
    )
    parser.add_argument(
        "--no-qa",
        action="store_true",
        help="不使用 Q&A 知識庫（單純分析指標）",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("📊 SEO 週報產生器")
    print("=" * 60)

    # 決定資料來源（優先順序：--input > .env SHEETS_URL > 預設 URL）
    source = args.input or getattr(config, "SHEETS_URL", "") or DEFAULT_SHEETS_URL

    if source.startswith("http"):
        print(f"\n📥 從 Google Sheets 擷取（tab: {args.tab}）...")
        try:
            tsv_text = fetch_from_sheets(source, tab=args.tab)
        except Exception as e:
            print(f"❌ 下載失敗：{e}")
            print("💡 請確認該試算表權限為「任何知道連結者可檢視」")
            sys.exit(1)
    elif source:
        tsv_text = Path(source).read_text(encoding="utf-8")
    else:
        print("📋 請貼上試算表資料（完成後按 Ctrl+D）：")
        tsv_text = sys.stdin.read()

    if not tsv_text.strip():
        print("❌ 沒有收到資料")
        sys.exit(1)

    # 解析
    print("\n🔍 解析指標資料 ...")
    metrics = parse_metrics_tsv(tsv_text)
    if not metrics:
        print("❌ 無法解析指標，請確認格式是從 Google 試算表直接複製的 TSV")
        sys.exit(1)
    print(f"   解析到 {len(metrics)} 個指標")

    # 異常偵測
    alerts = detect_anomalies(metrics)
    alert_down = [a for a in alerts if a["flag"] == "ALERT_DOWN"]
    alert_up = [a for a in alerts if a["flag"] == "ALERT_UP"]
    print(f"   核心指標: {len([a for a in alerts if a['flag']=='CORE'])} 個")
    print(f"   顯著下滑: {len(alert_down)} 個 | 顯著上升: {len(alert_up)} 個")

    metrics_summary = _build_metrics_summary(alerts)

    # 語意搜尋相關 Q&A（多查詢策略：每個異常指標獨立查詢）
    relevant_qas = []
    if not args.no_qa:
        print("\n🔎 搜尋相關 Q&A 知識庫 ...")
        qa_pairs = _load_qa_database()
        if qa_pairs:
            print(f"   知識庫共 {len(qa_pairs)} 個 Q&A")
            # 為每個需要解釋的指標建立語意查詢
            queries: list[str] = []
            seen: set[str] = set()

            def _add_query(q: str) -> None:
                if q not in seen:
                    seen.add(q)
                    queries.append(q)

            for a in alerts:
                name = a["name"]
                monthly = a.get("monthly") or 0
                weekly = a.get("weekly") or 0
                direction = "下降" if (monthly < 0 or weekly < 0) else "上升"

                # 優先使用 METRIC_QUERY_MAP 的精確查詢
                if name in METRIC_QUERY_MAP:
                    for q in METRIC_QUERY_MAP[name]:
                        _add_query(q)
                else:
                    # 通用退回模板
                    if a["flag"] == "CORE":
                        _add_query(f"{name} {direction} 代表什麼 SEO 含義")
                    elif a["flag"] == "ALERT_DOWN":
                        _add_query(f"{name} 大幅下降 原因 怎麼處理")
                    elif a["flag"] == "ALERT_UP":
                        _add_query(f"{name} 大幅上升 代表什麼 注意事項")

            # 固定補充：確保核心知識庫場景必然覆蓋
            for q in [
                "CTR 持續下降 搜尋結果外觀 如何改善",
                "檢索未索引增加 WAF 封鎖 Googlebot",
                "Discover 流量波動 探索演算法",
                "AMP Article 流量下降 焦點新聞",
                "伺服器回應時間 爬蟲抓取 索引影響",
            ]:
                _add_query(q)

            # 先取較大的候選池（top_k 的 2 倍，最多 30），再用 LLM Reranker 精選
            candidate_pool = max(args.top_k * 2, 20)
            candidates = find_relevant_qas_multi(
                queries, qa_pairs,
                top_k_per_query=3,
                total_max=candidate_pool,
            )
            print(f"   使用 {len(queries)} 個查詢，候選 {len(candidates)} 個 Q&A")
            relevant_qas = _rerank_qas(candidates, metrics_summary, args.top_k)
            print(f"   使用 {len(queries)} 個查詢，找到 {len(relevant_qas)} 個相關 Q&A（已 Rerank）")
        else:
            print("   ⚠️  找不到 Q&A 知識庫，跳過（先執行步驟 2-3 建立知識庫）")

    # 取得日期，標準化為 YYYYMMDD
    sample_metric = next((m for m in metrics.values() if m.get("latest_date")), {})
    raw_date = sample_metric.get("latest_date", "")
    try:
        # 解析 M/D/YYYY → YYYYMMDD
        dt = datetime.strptime(raw_date, "%m/%d/%Y")
        date_str = dt.strftime("%Y%m%d")
        report_date = dt.strftime("%Y/%m/%d")
    except ValueError:
        date_str = datetime.today().strftime("%Y%m%d")
        report_date = raw_date or datetime.today().strftime("%Y/%m/%d")

    # 產生報告
    print(f"\n✍️  產生報告（日期：{report_date}）...")
    report_md = generate_report(metrics_summary, relevant_qas, report_date)

    # 輸出
    if args.output:
        out_path = Path(args.output)
    else:
        out_path = config.OUTPUT_DIR / f"report_{date_str}.md"

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report_md, encoding="utf-8")

    print("\n" + "=" * 60)
    print(f"✅ 報告完成！")
    print(f"   📄 {out_path}")
    print("=" * 60)

    # 直接印到 console
    print("\n" + "─" * 60)
    print(report_md)


if __name__ == "__main__":
    main()
