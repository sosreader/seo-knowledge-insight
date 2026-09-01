r"""
crawl_taxonomy.py — crawler 分群、路徑分桶，以及對應的 LogQL 片段

被 scripts/ingest_crawl_hourly.py 使用。抽出來成獨立模組的理由不只是行數：
**這一層是唯一需要密集單元測試的部分**（分群規則、allowlist、樣式推導），
而 ingest 那一層幾乎全是 HTTP 與時間視窗。分開之後測試也分得乾淨。


═══ 設計決定 ═══

【1. UA 比對一律對 `| json` 之後的 user_agent 欄位做，不可用 line filter】
兩個獨立的理由，都是 2026-09-01 對 prod Loki 實測出來的：

  (a) **正確性**：`|~ "(?i)google"` 掃整行時，命中最多的是 815 次的普通 iPhone Safari——
      那是從 google.com 搜尋點進來的**真人**，`referer` 欄位裡有 "google"。
      用 line filter 分群會把 Google 帶來的自然流量整批誤標成 Googlebot，
      而且數字看起來完全合理，沒有任何錯誤訊號。

  (b) **效能**：line filter 的正規表示式要對每一行原始 log 求值。實測把 41 個
      alternation 的 crawler 樣式當 line filter 前置，反而 30.5s 超時（proxy 上限）；
      改成 `| json | user_agent =~ ...` 的 label filter 只要 12.8s。

【2. 過濾樣式由分群表推導，不手寫第二份】
`build_crawler_ua_pattern()` 從 TOKEN_TO_UA_GROUP 的 key 加上 GENERIC_BOT_MARKERS
程式產生。手寫兩份的失敗模式很具體：facebookexternalhit / Google-AMPHTML /
meta-webindexer / AIWebIndex / Claude-User 的 UA 裡**都沒有 "bot" 這個字**，
一個看起來很合理的 `bot|crawler|spider` 過濾樣式會把它們整批漏掉
（實測合計 1,239 次/小時），而漏掉的部分會靜默併進 human。
由分群表推導就讓「過濾樣式比分群表窄」變成不可能發生的狀態。

【3. path_prefix 的 allowlist 必須寫在 LogQL 裡，不能事後在 Python 收斂】
vocus.cc 的**使用者頁掛在根路徑**（`/<handle>`），所以「第一層路徑段」對全流量是
高基數維度。實測對全流量 `sum by (第一層路徑段)` 直接回 HTTP 400：

    maximum number of series (500) reached for a single query

Loki 的 `max_series` 是 500，而且是**回應層的硬門檻**，不是截斷、不是效能建議。
所以分桶要在 LogQL 求值時就套 allowlist。normalize_path_prefix() 仍會再正規化一次，
那是縱深防禦不是主要防線。

【4. Go template（label_format）的兩個坑】
  - **沒有 `has` / `list`**：回 `function "has" not defined`。allowlist 判斷只能用
    regex alternation，不能用 sprig 的集合函式。
  - **`\.` 會讓整個 template 掛掉**：LogQL 的反引號字串是 raw string，`\.` 原樣送進
    Go template 的雙引號字串字面值，而 `\.` 不是合法的 Go escape，回
    `invalid template ... invalid syntax`。**用 `[.]` 字元類別取代 `\.`** 可完全繞開，
    所以 PATH_SEGMENTS 裡的 `robots[.]txt` 不是筆誤。

  regexReplaceAll 沒有 else 分支，預設值用這個形狀做出來：

      regexReplaceAll "^.*?(TOKEN_A|TOKEN_B).*$|^.*$" .user_agent "${1}"

  第二個 alternative `^.*$` 必定匹配且不含 group 1 ⇒ 沒命中時得到空字串。
  空字串在 Python 端才映射成 other-bot / human——**判別邏輯留在 Python 是刻意的**，
  那是唯一測得到的地方，塞進 Go template 就沒有單元測試可言。

【5. Googlebot desktop / smartphone 要靠第三個 label 才分得開】
兩者的 token 都只是 `Googlebot`，差別在外層有沒有 Android/Mobile：
  desktop    Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)
  smartphone Mozilla/5.0 (Linux; Android 6.0.1; Nexus 5X ...) ... (compatible; Googlebot/2.1; ...)
所以多抽一個 `mob` label。它只在已被 UA filter 篩過的 ~8k 行上求值，成本可忽略。
注意**不能用 "Nexus 5X" 當判別式**：同一個外殼底下還有 AdsBot-Google-Mobile /
Google-AMPHTML / GoogleOther / Google-Safety。
"""
from __future__ import annotations

from typing import Iterable

# ── UA 分群 ─────────────────────────────────────────────────────────────
# 【順序有意義】token 抽取用 regex alternation，同一個起始位置上先列的先贏，
# 所以更長、更具體的必須排在前面：Googlebot-Image 要在 Googlebot 之前，
# 否則 "Googlebot-Image/1.0" 會被抽成 "Googlebot"。
#
# 【值域必須與 supabase/migrations/017 的 crawl_daily_ua_group_ck 一致】
# 這張表是權威對照表，改動要與該 CHECK 同一個 PR。
TOKEN_TO_UA_GROUP: dict[str, str] = {
    # Google —— 具體者在前
    "Googlebot-Image": "googlebot-image",
    "Googlebot-Video": "googlebot-other",
    "Googlebot-News": "googlebot-other",
    "AdsBot-Google-Mobile": "googlebot-other",
    "AdsBot-Google": "googlebot-other",
    "Google-AMPHTML": "googlebot-other",
    "Google-InspectionTool": "googlebot-other",
    "Google-Safety": "googlebot-other",
    "GoogleOther": "googlebot-other",
    # 泛用 Googlebot 要排在所有 Googlebot-* / *-Google-* 之後。
    # desktop/smartphone 再由 MOBILE_MARKERS 細分，見 classify_ua_group()。
    "Googlebot": "googlebot-desktop",
    "bingbot": "bingbot",
    # 會回連、帶 referral 的 AI 搜尋抓取
    "Claude-SearchBot": "ai-search-bot",
    "Claude-User": "ai-search-bot",
    "OAI-SearchBot": "ai-search-bot",
    "ChatGPT-User": "ai-search-bot",
    "PerplexityBot": "ai-search-bot",
    "YouBot": "ai-search-bot",
    "ExaSearchBot": "ai-search-bot",
    # 純語料抓取，不回連
    "ClaudeBot": "ai-training-bot",
    "GPTBot": "ai-training-bot",
    "Bytespider": "ai-training-bot",
    "meta-webindexer": "ai-training-bot",
    "AIWebIndex": "ai-training-bot",
    "Amazonbot": "ai-training-bot",
    "Applebot": "ai-training-bot",
    # 第三方 SEO 稽核爬蟲。算 crawl budget 時要能扣掉——它們不是搜尋引擎。
    "AhrefsSiteAudit": "seo-tool-bot",
    "AhrefsBot": "seo-tool-bot",
    "SemrushBot": "seo-tool-bot",
    "DataForSeoBot": "seo-tool-bot",
    "SERankingBacklinksBot": "seo-tool-bot",
    # 分享預覽。突刺代表被轉發，不是被索引。
    "facebookexternalhit": "social-bot",
    "meta-externalads": "social-bot",
    "Dcard-link-preview-bot": "social-bot",
    # 其他傳統搜尋引擎
    "YandexBot": "other-bot",
    "Baiduspider": "other-bot",
    "DuckDuckBot": "other-bot",
    "PetalBot": "other-bot",
}

# UA 沒命中任何具名 token、但含這些字樣者 → other-bot。
# 用字元類別而非 (?i)：只需涵蓋實際出現過的大小寫，比整段 case-insensitive 便宜。
GENERIC_BOT_MARKERS = ("[Bb]ot", "[Cc]rawler", "[Ss]pider", "[Ss]lurp")

# 只用來細分泛用 Googlebot 的 desktop / smartphone。
MOBILE_MARKERS = ("Android", "iPhone", "iPad", "Mobile")

UA_GROUP_OTHER_BOT = "other-bot"
UA_GROUP_HUMAN = "human"
GOOGLEBOT_TOKEN = "Googlebot"
GOOGLEBOT_SMARTPHONE = "googlebot-smartphone"

# ── path 分桶 ───────────────────────────────────────────────────────────
# 第一層路徑段的 allowlist。不在名單上者一律塌成 PATH_PREFIX_OTHER。
# 【`[.]` 不是筆誤】見設計決定 4：`\.` 會讓 Go template 整個掛掉。
# 名單來自 2026-09-01 的實測分佈，不是猜的；新增路由時要一併更新
# （沒更新的後果是該路由靜默併進 /__other__，不是壞掉）。
PATH_SEGMENTS = (
    "article", "salon", "tags", "user", "post", "search", "api",
    "_next", "static", "not-found", "robots[.]txt", "sitemap[.]xml",
    "feed", "rss", "pay", "become_creator", "[.]well-known", "favicon[.]ico",
)
PATH_PREFIX_ROOT = "/"
PATH_PREFIX_OTHER = "/__other__"
# crawl_daily_path_prefix_ck 的鏡像：單層、字元集受限、octet_length <= 64。
# 這裡先擋一次，讓不合格的桶名在送出前就歸入殘餘桶——015 的註解特別提醒
# 「ingest 端漏做映射時死的是整批，不是那一列」。
PATH_PREFIX_ALLOWED_CHARS = frozenset(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.-"
)
PATH_PREFIX_MAX_BYTES = 64

HTTP_STATUS_MIN = 100
HTTP_STATUS_MAX = 599


# ══════════════════════════════════════════════════════════════════════
# LogQL 片段
# ══════════════════════════════════════════════════════════════════════

def _capture_or_empty(alternatives: Iterable[str], field: str) -> str:
    """產生「命中就回捕捉組、沒命中回空字串」的 label_format template。

    regexReplaceAll 沒有 else 分支，靠第二個 alternative `^.*$` 兜底：
    它必定匹配且不含 group 1，所以 ${1} 展開成空字串。
    """
    pattern = "^.*?(" + "|".join(alternatives) + ").*$|^.*$"
    return '{{ regexReplaceAll "' + pattern + '" ' + field + ' "${1}" }}'


def build_ua_token_expr() -> str:
    return "token=`" + _capture_or_empty(TOKEN_TO_UA_GROUP, ".user_agent") + "`"


def build_mobile_expr() -> str:
    return "mob=`" + _capture_or_empty(MOBILE_MARKERS, ".user_agent") + "`"


def build_path_prefix_expr() -> str:
    """第一層路徑段，且只認 allowlist；其餘塌成空字串（Python 端映射成殘餘桶）。

    形狀：^(/(?:article|tags|...)?)(?:[/?#].*)?$|^.*$
    第一個 alternative 讓 `/article/123?x=1` → `/article`、`/` → `/`；
    不在名單上的路徑（例如根路徑下的使用者 handle）落到 `^.*$` ⇒ 空字串。
    這一步不可省略，見設計決定 3：全流量自由抽取會撞 max_series=500。
    """
    pattern = "^(/(?:" + "|".join(PATH_SEGMENTS) + ")?)(?:[/?#].*)?$|^.*$"
    return "pfx=`" + '{{ regexReplaceAll "' + pattern + '" .path "${1}" }}' + "`"


def build_crawler_ua_pattern() -> str:
    """`user_agent =~` 用的過濾樣式，由分群表 + 泛用標記**推導**而來（見設計決定 2）。"""
    return ".*(" + "|".join((*TOKEN_TO_UA_GROUP, *GENERIC_BOT_MARKERS)) + ").*"


# ══════════════════════════════════════════════════════════════════════
# 分類
# ══════════════════════════════════════════════════════════════════════

def classify_ua_group(token: str, mobile_marker: str) -> str:
    """(token, mobile_marker) → crawl_daily.ua_group。

    token 為空代表 UA 通過了過濾樣式但沒命中任何具名 token ⇒ 它是靠泛用標記
    （bot/crawler/spider/slurp）進來的 ⇒ other-bot。
    因為過濾樣式是由分群表推導的（build_crawler_ua_pattern），
    「通過過濾但 token 為空」與「命中泛用標記」是等價的，不需要再傳旗標進來。
    """
    if not token:
        return UA_GROUP_OTHER_BOT
    group = TOKEN_TO_UA_GROUP.get(token)
    if group is None:
        # 抽到分群表以外的 token：只可能是 label_format 的樣式與這張表分岔了。
        # 不猜、不靜默塞進殘餘桶——那正是 015 的 CHECK 想擋掉的事。
        raise ValueError(
            f"UA token {token!r} 不在 TOKEN_TO_UA_GROUP 裡。"
            f"label_format 的樣式是由這張表產生的，出現這個錯誤代表兩者已經分岔。"
        )
    if token == GOOGLEBOT_TOKEN and mobile_marker:
        return GOOGLEBOT_SMARTPHONE
    return group


def normalize_path_prefix(raw: str) -> str:
    """把 LogQL 抽出的 pfx 正規化成符合 crawl_daily_path_prefix_ck 的桶名。

    LogQL 已經套過 allowlist，這裡是縱深防禦：任何不合格的值塌成殘餘桶，
    而不是一路送到 PostgREST 去撞 CHECK——那會**整批 500 列一起死**，
    不是只死那一列（015 的註解特別提醒過這件事）。
    """
    if not raw or not raw.startswith("/"):
        return PATH_PREFIX_OTHER
    if raw == PATH_PREFIX_ROOT:
        return PATH_PREFIX_ROOT
    if len(raw.encode()) > PATH_PREFIX_MAX_BYTES:
        return PATH_PREFIX_OTHER
    if any(char not in PATH_PREFIX_ALLOWED_CHARS for char in raw[1:]):
        return PATH_PREFIX_OTHER
    return raw


def parse_status_code(raw: str) -> int | None:
    """status label → int，不合法者回 None（呼叫端丟棄）。

    crawl_daily_status_code_ck 只收 100..599。envoy 在連線層失敗時會記 0，
    那不是 HTTP 狀態碼；讓它進 payload 會整批被 CHECK 打回。
    """
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return None
    return value if HTTP_STATUS_MIN <= value <= HTTP_STATUS_MAX else None
