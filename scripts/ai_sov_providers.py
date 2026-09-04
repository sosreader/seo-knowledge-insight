"""
ai_sov_providers.py — AI SoV 的 provider 抽象與 citation 解析（S6.2）

被 scripts/ingest_ai_sov.py 使用。本檔負責「問一次 LLM、拿回一組 citation」，
不碰 Supabase、不決定要問哪些 prompt——存取層在 ai_sov_warehouse.py，
panel 在 ai_sov_panel.py（同一種「共用存取/設定層獨立成檔」的拆法，
沿用 crawl_warehouse.py 之於 ingest_crawl_hourly.py 的前例）。


═══ 設計決定 ═══

【1. 為什麼是 protocol 而不是 if provider == "openai"】
S6.2 的待裁決項之一是要不要加 Perplexity / Gemini。那個決定會改變的只有
「怎麼發請求、怎麼從回應裡挖出 citation」，不該連帶改動聚合邏輯與寫入路徑。
Provider protocol 把邊界劃在 ProviderAnswer 這個資料結構上：新增一家
provider = 新增一個類別 + 一組解析測試，ingest 腳本一個字不用改。

【2. 為什麼用 stdlib urllib 而不是 openai SDK】
本 repo 的 ingest_*.py 一律走 stdlib urllib（crawl / cwv / gsc 三支都是），
GitHub Actions 上只 `pip install python-dotenv`。openai SDK 在 utils/ 那邊
是給 QA pipeline 用的，那條路徑有完整的 requirements.txt。這支週跑作業
多裝一個 SDK 只為了發一個 POST，代價是每週的 workflow 都多一次相依安裝
與一個版本漂移面。Responses API 的請求體與回應結構都很小，直接組。

【3. 為什麼「零 citation」要當成一個獨立狀態，而不是「沒引用 vocus」】
一次回應零 citation 代表 provider 這次**沒有引用任何人**——通常是沒觸發
檢索（模型改版、工具被停、prompt 撞到安全政策）。把它記成「沒引用 vocus」
會讓 provider 端的行為變動偽裝成站方可見度下降，而且是無聲的：總量正常、
比例下滑，看不出原因。ProviderAnswer 因此把 citations 為空這件事原樣帶出去，
由上層標成 grounding='ungrounded'、從 SoV 分母排除、另外當降級指標監測。

【4. 為什麼 rank 以「URL 去重後的出現順序」定義】
Responses API 的 annotation 帶 start_index（citation 在回應文字裡的位置），
同一個 URL 可能在一段回應裡被標註多次。用出現順序排序後以 URL 去重，
得到的才是「這個回應實際引了哪幾個來源、依序是誰」。
⚠ 這個序不是 SERP 排名，跨 provider 比較沒有意義（見 migration 024 的欄位註解）。

【5. 為什麼 429 要拆成兩種、而不是一律重試】
OpenAI 用同一個 HTTP 狀態碼（429）表達兩件完全不同的事：暫時性的速率限制
（`error.type=rate_limit_error`，重試通常會成功），與帳號額度耗盡
（`error.type=insufficient_quota`／`error.code=credit_balance_exhausted`，
不管重試幾次都是同一個結果，因為問題不在請求頻率、在帳戶餘額）。
把兩者都當成 RETRYABLE_STATUS 處理，會讓後者對 108 次呼叫各重試到底
（實測 21 分鐘、0 列產出）——那不是保守，是在已知徒勞的情況下繼續徒勞。
401/403（金鑰失效／權限不足）同理：換一次請求不會讓金鑰重新生效。
這三種歸為 fatal：不重試、拋 ProviderFatalError，讓上層（run_panel）
立即中止整條 run，而不是耗盡 MAX_ATTEMPTS 才對外表現出「失敗」。
"""
from __future__ import annotations

import hashlib
import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Iterable, Mapping, Protocol, Sequence

logger = logging.getLogger(__name__)

OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"
HTTP_TIMEOUT_SECONDS = 120  # web_search 工具會實際去抓網頁，比純生成慢得多
MAX_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = (2.0, 8.0)  # 第 1、2 次重試前的等待；長度必須 = MAX_ATTEMPTS - 1
RETRYABLE_STATUS = (408, 429, 500, 502, 503, 504)
# 429 本身可重試（速率限制），但下列狀態碼一律 fatal：401/403 是金鑰失效或
# 權限不足，重試不會讓金鑰重新生效。429 是否 fatal 要再看 error body（見
# _is_fatal_openai_error），因為它同時承載速率限制（可重試）與額度耗盡
# （不可重試）兩種語意（設計決定 5）。
FATAL_HTTP_STATUS = (401, 403)
# OpenAI 額度/帳務類錯誤的 error.type／error.code——只有這些值視為 fatal，
# 其他 429（例如 rate_limit_error / rate_limit_exceeded）仍走一般重試。
FATAL_OPENAI_ERROR_TYPES = frozenset({"insufficient_quota"})
FATAL_OPENAI_ERROR_CODES = frozenset({"insufficient_quota", "credit_balance_exhausted"})
USER_AGENT = "seo-knowledge-insight-ai-sov/1.0"


class ProviderError(RuntimeError):
    """呼叫 provider 失敗。呼叫端必須當成失敗處理，不得靜默記成『沒引用』。"""


class ProviderFatalError(ProviderError):
    """呼叫 provider 失敗，且重試對這個錯誤沒有意義（額度耗盡／認證失效）。

    這類錯誤不是暫時性的：對同一個 (prompt, repeat) 重試 3 次、或對 108 次
    呼叫各重試 3 次，得到的都是同一個結果，只是白白多耗時間（實例：
    2026-09-04 run 33862967625，OpenAI 回 insufficient_quota，108 次呼叫
    各重試 2 次，整條 run 白耗 21 分鐘才以 0 列結束）。呼叫端（ingest_ai_sov
    的 run_panel）收到這個例外必須立即中止整條 run，不得繼續問下一個
    prompt——見 ai_sov_providers 設計決定 5。"""


@dataclass(frozen=True)
class Citation:
    url: str
    domain: str


@dataclass(frozen=True)
class ProviderAnswer:
    text: str
    citations: tuple[Citation, ...] = field(default_factory=tuple)
    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def is_grounded(self) -> bool:
        return bool(self.citations)


class Provider(Protocol):
    """一次問答的最小介面。新增 provider 只需實作這三樣。"""

    name: str
    model: str

    def answer(self, prompt: str) -> ProviderAnswer: ...


# ══════════════════════════════════════════════════════════════════════
# 網域正規化與目標判定
# ══════════════════════════════════════════════════════════════════════

def normalize_domain(url: str) -> str | None:
    """從 URL 取出正規化網域：小寫、去 port、去開頭的 www.。

    無法解析（沒有 scheme/host、或不是 http(s)）時回 None——呼叫端會把它
    整個丟掉而不是塞一個空字串進 cited_domains，那會在 domain 佔比視圖裡
    變成一個叫做「」的競品。
    """
    try:
        parsed = urllib.parse.urlsplit(url)
    except ValueError:
        return None
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        return None
    host = parsed.hostname.lower().rstrip(".")
    return host[4:] if host.startswith("www.") else host


def is_target_domain(domain: str, target: str) -> bool:
    """domain 是否為 target 本身或其子網域。

    ⚠ 【已知缺口】vocus.cc 的創作者可以綁自訂網域，那些頁面的內容屬於本站、
    網域卻不是 vocus.cc，本函式判定為「不是我們」。因此本指標量到的是
    **vocus.cc 網域下**的 share of voice，會系統性低估。要修需要一份
    自訂網域清單（平台側資料，不在本 repo），列為待裁決項而非靜默忽略。
    """
    target = target.lower()
    return domain == target or domain.endswith("." + target)


def dedupe_citations(urls: Iterable[str]) -> tuple[Citation, ...]:
    """依出現順序去重（以 URL 為鍵），並丟掉無法解析網域的項目。"""
    seen: set[str] = set()
    result: list[Citation] = []
    for url in urls:
        if not isinstance(url, str) or url in seen:
            continue
        domain = normalize_domain(url)
        if domain is None:
            logger.warning("略過無法解析網域的 citation：%.120s", url)
            continue
        seen.add(url)
        result.append(Citation(url=url, domain=domain))
    return tuple(result)


def first_target_rank(citations: Sequence[Citation], target: str) -> int | None:
    """target 第一次出現的位置（1-based）；沒出現回 None。"""
    for index, citation in enumerate(citations, start=1):
        if is_target_domain(citation.domain, target):
            return index
    return None


def response_digest(text: str) -> str:
    """回應全文的 sha256 hex。全文不入庫，只留摘要（見 migration 024 欄位註解）。"""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ══════════════════════════════════════════════════════════════════════
# OpenAI Responses API
# ══════════════════════════════════════════════════════════════════════

def _iter_text_blocks(payload: Mapping) -> Iterable[Mapping]:
    """走訪 Responses API 回應裡所有 output_text 區塊。

    刻意不假設 output[0] 就是訊息：帶工具的回應會先出現 web_search_call
    之類的項目，硬取索引在工具被跳過時會拿到錯的東西（而且不報錯）。
    """
    for item in payload.get("output") or []:
        if not isinstance(item, Mapping) or item.get("type") != "message":
            continue
        for block in item.get("content") or []:
            if isinstance(block, Mapping) and block.get("type") == "output_text":
                yield block


def _annotation_urls(block: Mapping) -> list[tuple[int, str]]:
    """從一個 output_text 區塊取出 (start_index, url)。"""
    pairs: list[tuple[int, str]] = []
    for annotation in block.get("annotations") or []:
        if not isinstance(annotation, Mapping) or annotation.get("type") != "url_citation":
            continue
        url = annotation.get("url")
        if isinstance(url, str) and url:
            pairs.append((int(annotation.get("start_index") or 0), url))
    return pairs


def parse_openai_response(payload: Mapping) -> ProviderAnswer:
    """把 Responses API 的 JSON 轉成 ProviderAnswer。

    零 citation 是合法結果（見設計決定 3），不拋例外；但回應裡完全沒有
    output_text 區塊代表這次呼叫的形狀不是我們預期的，那要拋——那是
    「API 換了、解析器沒跟上」的形狀，靜默回空會讓整批資料變成 ungrounded
    而看起來像 provider 行為變動。
    """
    blocks = list(_iter_text_blocks(payload))
    if not blocks:
        raise ProviderError(f"回應裡沒有 output_text 區塊，解析器可能已與 API 脫節：{str(payload)[:300]}")

    text = "".join(str(block.get("text") or "") for block in blocks)
    pairs = [pair for block in blocks for pair in _annotation_urls(block)]
    ordered = [url for _, url in sorted(pairs, key=lambda p: p[0])]
    usage = payload.get("usage") if isinstance(payload.get("usage"), Mapping) else {}
    return ProviderAnswer(
        text=text,
        citations=dedupe_citations(ordered),
        input_tokens=int(usage.get("input_tokens") or 0),
        output_tokens=int(usage.get("output_tokens") or 0),
    )


def _is_fatal_openai_error(status: int, raw_body: str) -> bool:
    """判斷一次失敗回應是不是『重試沒有意義』（見設計決定 5）。

    401/403 一律 fatal。429 要拆開看 error body：`error.type` 或 `error.code`
    命中額度/帳務類清單才算 fatal，其餘 429（含 body 解析不出來、或明確是
    rate_limit_error 的情形）一律視為可重試——寧可對真正的速率限制多重試
    幾次，也不要把解析不出來的錯誤誤判成 fatal 而漏掉可能自癒的失敗。
    """
    if status in FATAL_HTTP_STATUS:
        return True
    if status != 429:
        return False
    try:
        payload = json.loads(raw_body)
    except (json.JSONDecodeError, TypeError):
        return False
    error = payload.get("error") if isinstance(payload, Mapping) else None
    if not isinstance(error, Mapping):
        return False
    error_type = str(error.get("type") or "")
    error_code = str(error.get("code") or "")
    return error_type in FATAL_OPENAI_ERROR_TYPES or error_code in FATAL_OPENAI_ERROR_CODES


def _post_json(url: str, body: Mapping, headers: Mapping[str, str], timeout: int) -> tuple[int, str]:
    request = urllib.request.Request(
        url, data=json.dumps(body).encode(), headers=dict(headers), method="POST"
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read().decode()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode(errors="replace")
    except urllib.error.URLError as exc:
        raise ProviderError(f"連線失敗：{exc.reason}") from exc


class OpenAIProvider:
    """OpenAI Responses API + web_search 工具。

    ⚠ api_key 只在建構時讀進記憶體、只放進 Authorization header，
    不寫進任何 log、不進 ProviderAnswer、不落磁碟。錯誤訊息一律只帶
    HTTP 狀態碼與回應片段（OpenAI 的錯誤回應不含 key）。
    """

    def __init__(self, api_key: str, model: str, *, timeout: int = HTTP_TIMEOUT_SECONDS) -> None:
        if not api_key:
            raise ProviderError("缺少 OPENAI_API_KEY")
        self.name = "openai"
        self.model = model
        self._api_key = api_key
        self._timeout = timeout

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
        }

    def _body(self, prompt: str) -> dict:
        # tool_choice 不強制：強制呼叫工具會讓「這個問題模型認為不需要檢索」
        # 這個真實訊號消失，而那正是 ungrounded 想量到的東西。
        return {
            "model": self.model,
            "input": prompt,
            "tools": [{"type": "web_search"}],
        }

    def answer(self, prompt: str) -> ProviderAnswer:
        last_error = ""
        for attempt in range(MAX_ATTEMPTS):
            status, raw = _post_json(OPENAI_RESPONSES_URL, self._body(prompt), self._headers(), self._timeout)
            if status == 200:
                return parse_openai_response(json.loads(raw))
            last_error = f"HTTP {status}：{raw[:300]}"
            if _is_fatal_openai_error(status, raw):
                # 額度耗盡／認證失效：重試得到的一定是同一個結果，不進
                # RETRYABLE_STATUS 的重試迴圈，直接讓上層立即中止整條 run
                # （見設計決定 5）。
                raise ProviderFatalError(f"OpenAI 呼叫失敗（不可重試）：{last_error}")
            if status not in RETRYABLE_STATUS or attempt == MAX_ATTEMPTS - 1:
                break
            wait = RETRY_BACKOFF_SECONDS[attempt]
            logger.warning("provider 回 %s，%.0fs 後重試（第 %d/%d 次）", status, wait, attempt + 2, MAX_ATTEMPTS)
            time.sleep(wait)
        raise ProviderError(f"OpenAI 呼叫失敗：{last_error}")


# ══════════════════════════════════════════════════════════════════════
# FakeProvider —— 測試與無金鑰環境下跑通整條鏈
# ══════════════════════════════════════════════════════════════════════

FAKE_PEER_DOMAINS = ("medium.com", "pixnet.net", "dcard.tw", "matters.town")


class FakeProvider:
    """不發任何網路請求的 provider。

    兩種用法：
      - scripted：測試給定一串 ProviderAnswer，依呼叫順序回傳（超出則循環）。
        用來精確驅動「引用/未引用/零引用」三種分支。
      - 預設（scripted=None）：由 (seed, prompt, 第幾次呼叫) 的 sha256 決定
        這次是 ungrounded、grounded 未引用、還是 grounded 且引用，比例由
        建構參數控制。**確定性**：同樣的 seed 與呼叫順序永遠得到同樣結果，
        所以無金鑰環境下的 smoke test 是可重現的，不是隨機亂數。

    ⚠ 產出的數字沒有任何現實意義，只用來證明「整條鏈接得起來」。
    """

    def __init__(self, *, model: str = "fake-1", target_domain: str = "vocus.cc",
                 scripted: Sequence[ProviderAnswer] | None = None,
                 ungrounded_rate: float = 0.2, cited_rate: float = 0.35, seed: str = "s6.2") -> None:
        self.name = "fake"
        self.model = model
        self._target = target_domain
        self._scripted = tuple(scripted) if scripted else ()
        self._ungrounded_rate = ungrounded_rate
        self._cited_rate = cited_rate
        self._seed = seed
        self.calls = 0

    def _roll(self, prompt: str, salt: str) -> float:
        raw = f"{self._seed}|{prompt}|{self.calls}|{salt}".encode()
        return int(hashlib.sha256(raw).hexdigest()[:8], 16) / 0xFFFFFFFF

    def _synthesize(self, prompt: str) -> ProviderAnswer:
        if self._roll(prompt, "grounding") < self._ungrounded_rate:
            return ProviderAnswer(text=f"[fake ungrounded] {prompt}", citations=())
        peer = FAKE_PEER_DOMAINS[self.calls % len(FAKE_PEER_DOMAINS)]
        urls = [f"https://{peer}/article/{self.calls}"]
        if self._roll(prompt, "cited") < self._cited_rate:
            urls.insert(self.calls % 2, f"https://{self._target}/article/{self.calls}")
        return ProviderAnswer(
            text=f"[fake grounded] {prompt}",
            citations=dedupe_citations(urls),
            input_tokens=len(prompt),
            output_tokens=len(prompt) * 2,
        )

    def answer(self, prompt: str) -> ProviderAnswer:
        result = (self._scripted[self.calls % len(self._scripted)]
                  if self._scripted else self._synthesize(prompt))
        self.calls += 1
        return result
