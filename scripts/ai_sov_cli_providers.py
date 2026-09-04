"""
ai_sov_cli_providers.py — 本機 CLI provider（codex／claude-code）給 AI SoV 用（S6.2）

被 scripts/ingest_ai_sov.py 使用，實作 ai_sov_providers.Provider protocol。
OpenAI provider 走付費 API；本檔的兩個 provider 改走使用者機器上已登入的
CLI（`codex` / `claude`），耗訂閱額度、不計 API 費用，代價是週跑必須在
使用者的機器上執行、機器沒開該週就沒有資料且不可回填（見
docs/ai-sov-local-runner.md）。


═══ 探測基礎 ═══

兩支 CLI 的行為都先用真實呼叫探測過，證據存在
knowledge-base `.verification/2026-09-04-ai-sov-golive/local-provider-probe/`
（codex.jsonl／codex.err／claude2.jsonl／claude2.err／claude.json／schema.json）。
本檔的解析邏輯直接對應探測到的事件形狀，不是猜測。


═══ 設計決定 ═══

【1. 為什麼共用一個 _run_cli 而不是各自 subprocess.run】
兩支 CLI 的呼叫失敗模式一致：找不到執行檔（沒裝／沒在 PATH）、逾時
（探測證實兩者都會在 stdin 可讀時卡住等『額外輸入』直到逾時）、非零 exit。
把這三種對應到 ProviderFatalError／ProviderError 的規則只寫一次，兩個
provider 共用，新增第三支本機 CLI 只需要接上這個函式加一個輸出解析器。

【2. 為什麼 stdin 一律 DEVNULL】
探測到的第一個真實故障：codex 沒有明確關閉 stdin 時，會印出
「Reading additional input from stdin...」然後停住，直到逾時才结束
（codex.err：`exit=0 secs=70`，但那 70 秒幾乎全部耗在等 stdin，不是在思考）。
批次呼叫的行程沒有互動終端可以餵它，必須從一開始就把 stdin 接掉。

【3. 為什麼 cwd 是每次呼叫獨立的臨時目錄】
codex 的 -C／claude 的 cwd 都會被 CLI 讀來判斷「這個目錄可不可信」、
要不要載入該目錄的 AGENTS.md／CLAUDE.md。用 repo 目錄本身會讓 CLI
讀到本 repo 的專案設定與 skills，混進與這次呼叫無關的上下文；用共用的
單一臨時目錄則在 --concurrency > 1 時會有多個呼叫互踩（codex 的
--output-schema 檔案路徑、claude 的 session 檔）。每次呼叫各開各的臨時目錄，
呼叫結束即刪除，兩個問題一次解決。

【4. codex／claude-code 的 grounded 判定不是同一套，而且刻意不同】
claude-code：模型在沒有明講『必須搜尋』時會直接憑內部知識列網址、
完全不觸發 WebSearch（探測 web_search_requests=0 的那次）。因此
ClaudeCodeProvider 要求回答附「來源：」段，並把段落裡的每個 URL
與同一次呼叫裡所有 WebSearch tool_result 實際回傳過的 URL 做交集——
不在搜尋結果裡的網址即使模型寫出來也不算 citation（會被濾除並記
warning log，不進 ProviderAnswer.citations，因為這個資料結構沒有
『未驗證』欄位，見 ai_sov_providers.ProviderAnswer 的既有形狀）。

codex：--output-schema 已經強制模型的最終輸出必須符合
{answer: string, sources: string[]} 這個 JSON schema，是 API 層級的
結構化輸出保證，不是靠模型自律的文字慣例。但探測也發現一個不對稱之處：
codex 的 hosted web_search 工具在 JSONL 事件裡只留下查詢字串
（item.type=="web_search" 的 query/queries），**不會**把搜尋引擎實際
回傳的 URL 清單一起吐出來——不像 Claude Code 的 tool_result 帶完整的
title/url 陣列。CodexProvider 因此無法比照 ClaudeCodeProvider 做『來源
是否真的出現在搜尋結果裡』的交叉驗證，只能信任 schema 強制的結構化輸出
本身。這是比 ClaudeCodeProvider 弱一階的保證，記在這裡供之後查核——
如果未來想補強，需要 codex CLI 在事件裡曝露 web_search 的實際結果列表，
目前版本（0.149.0）沒有。

【5. codex 為什麼探測時會亂讀檔案、以及 --ignore-user-config 為什麼修得掉這個】
第一次探測（見 knowledge-base probe 證據 codex.jsonl）顯示：即使沒有要求，
codex 也會執行 command_execution，甚至讀了 sandbox 目錄以外的檔案（使用者
home 目錄下其他 repo 的 AGENTS.md／CLAUDE.md）。根因找到了：使用者本機
`~/.codex/config.toml` 有一行 `persistent_instructions = "Follow project
AGENTS.md guidelines. ..."`，這行對「每一次」codex 呼叫都生效，等於系統
提示明講「去找並遵守 AGENTS.md」——這才是它主動搜尋、讀取專案文件的直接
原因，不是模型自發的越界行為。config.toml 裡的 `[projects."..."]` trust
清單（含好幾個真實 repo 的絕對路徑）很可能也在同一份被載入的設定裡，
讓模型「知道」有哪些路徑可查。

修法用 CLI 既有的 `--ignore-user-config`（不載入 $CODEX_HOME/config.toml，
但 CODEX_HOME 下的登入憑證不受影響）驗證過：同一個 prompt、同樣的 --sandbox
read-only，加上這個旗標後**完全沒有任何 command_execution 事件**，
直接進 web_search → agent_message，input_tokens 從實測 ~15.7 萬降到
~11.7 萬（少了被讀進 context 的那些專案文件）。這比原本設想的『無法
關掉、只能緩解』更進一步：--ignore-user-config 不是『關掉 shell 工具』
本身（模型理論上仍可能因為其他理由呼叫 shell），但它移除了會主動誘發
shell 探索的那個持久化系統提示，觀察到的探索行為因此消失。仍保留兩層
既有緩解作為防禦深度：
  1. prompt 前綴明講『禁止執行任何指令、禁止讀取本機檔案』；
  2. 顯式帶 --sandbox read-only（保底不會有任何寫入）。
claude-code 的保證仍然更強：--allowedTools WebSearch 是 CLI 層級白名單，
沒被列入的工具（含任何 shell/Bash 工具）連呼叫的機會都沒有，是結構性
保證，不依賴『系統提示裡有沒有教它別亂搜』這種可能因設定檔內容而變動的
前提。選 provider 時仍應把這個差異納入考量。
"""
from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Iterable, Sequence

from ai_sov_providers import (
    ProviderAnswer,
    ProviderError,
    ProviderFatalError,
    dedupe_citations,
)

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_SECONDS = 240  # 每題實測 56～70 秒，含重試緩衝抓 3～4 倍
DEFAULT_CODEX_MODEL = "gpt-5.4"
DEFAULT_CLAUDE_CODE_MODEL = "claude-sonnet-5"
DEFAULT_CLAUDE_CODE_MAX_TURNS = 8

# codex --output-schema 檔案內容：強制最終回覆是這個形狀的 JSON。
CODEX_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "answer": {"type": "string"},
        "sources": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["answer", "sources"],
    "additionalProperties": False,
}

# 沒有這句，探測到的 claude-code 會直接憑內部知識列網址、完全不觸發搜尋
# （見設計決定 4）。「來源：」這個中文標頭要求跟 _SOURCES_HEADING_RE 綁定，
# 兩邊改動要一起改。
CLAUDE_CODE_SEARCH_DIRECTIVE = (
    "在回答之前，你「必須」先呼叫 WebSearch 工具搜尋這個問題的最新資訊，"
    "禁止只憑內部知識直接作答。搜尋完成後再回答問題本身，並在回答最後另起一段，"
    "以「來源：」開頭，逐行列出你在回答內容中實際引用的完整網址（每行一個）。"
)

_SOURCES_HEADING_RE = re.compile(r"來源[：:]\s*")
_URL_RE = re.compile(r"https?://[^\s)\]>」』，,]+")


def _strip_trailing_punctuation(url: str) -> str:
    """去掉 URL 尾端誤黏的標點（句尾句號、中文引號等），不動 query string 本身。"""
    return url.rstrip(".,;:!?)\"'』」")


def _run_cli(args: Sequence[str], *, timeout: int, cwd: Path,
             unset_env: Sequence[str] = ()) -> str:
    """執行本機 CLI，回傳 stdout。

    找不到執行檔（沒裝／沒在 PATH）視為系統性問題，跟 OpenAI 的
    401/403（金鑰失效）同一類：換一次呼叫不會讓執行檔突然出現，因此拋
    ProviderFatalError 讓上層立即中止整條 run（見 ai_sov_providers 設計
    決定 5）。逾時與非零 exit 是單次呼叫層級的失敗，拋 ProviderError，
    上層會記一筆失敗、繼續跑下一次呼叫（設計決定 4）。
    """
    env = os.environ.copy()
    for key in unset_env:
        env.pop(key, None)
    try:
        result = subprocess.run(
            list(args), stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, timeout=timeout, cwd=str(cwd), env=env, text=True,
        )
    except FileNotFoundError as exc:
        raise ProviderFatalError(f"找不到本機 CLI 執行檔 {args[0]}：{exc}") from exc
    except subprocess.TimeoutExpired as exc:
        raise ProviderError(f"CLI 逾時（{timeout}s，未在時限內結束）") from exc
    if result.returncode != 0:
        raise ProviderError(
            f"CLI 以非零碼結束（exit={result.returncode}）：{(result.stderr or '')[:500]}"
        )
    return result.stdout


def _iter_jsonl_events(stdout: str) -> Iterable[dict]:
    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(event, dict):
            yield event


# ══════════════════════════════════════════════════════════════════════
# Codex CLI
# ══════════════════════════════════════════════════════════════════════

def _last_codex_agent_message(events: list[dict]) -> str:
    """取最後一個 item.type=="agent_message" 的 text（符合 --output-schema 的 JSON 字串）。

    取『最後一個』而不是第一個：探測顯示 codex 在給出最終答案前，可能先
    跑幾輪 command_execution／web_search（見設計決定 5），中間不會有
    agent_message；只有收斂到最終答案時才會產生它，理論上整條 thread
    只有一個，但取最後一個對『萬一有多個』的情形更保守正確。
    """
    text = None
    for event in events:
        if event.get("type") != "item.completed":
            continue
        item = event.get("item") or {}
        if item.get("type") == "agent_message" and isinstance(item.get("text"), str):
            text = item["text"]
    if text is None:
        raise ProviderError("codex 輸出裡沒有 agent_message，解析器可能已與 CLI 脫節")
    return text


def _codex_usage(events: list[dict]) -> tuple[int, int]:
    """從（最後一個）turn.completed 事件取 token 使用量。

    output_tokens 把 output_tokens 與 reasoning_output_tokens 相加：
    這兩者在 codex 的 usage 裡是分開的欄位，但都是這次呼叫實際產生的
    輸出（推理過程的 token 一樣計費／計額度），跟 OpenAI Responses API
    的 usage.output_tokens 本身已內含推理 token 的核算方式對齊。
    """
    usage: dict = {}
    for event in events:
        if event.get("type") == "turn.completed":
            usage = event.get("usage") or {}
    if not usage:
        logger.warning("codex 輸出裡沒有 turn.completed／usage，token 計數以 0 記")
    input_tokens = int(usage.get("input_tokens") or 0)
    output_tokens = int(usage.get("output_tokens") or 0) + int(usage.get("reasoning_output_tokens") or 0)
    return input_tokens, output_tokens


def parse_codex_output(stdout: str) -> ProviderAnswer:
    """把 codex --json 的 JSONL stdout 轉成 ProviderAnswer。

    最終答案不符 schema（缺 answer/sources、或 agent_message 的 text
    根本不是合法 JSON）一律拋 ProviderError，不做『能救多少救多少』的
    寬鬆解析——那會讓『schema 被繞過』與『schema 生效但答案真的沒有來源』
    混在一起，前者是解析器該擋下的異常，後者才是合法的 ungrounded。
    """
    events = list(_iter_jsonl_events(stdout))
    raw_text = _last_codex_agent_message(events)
    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ProviderError(f"codex 最終回覆不是合法 JSON：{raw_text[:300]}") from exc
    if not isinstance(payload, dict) or "answer" not in payload or "sources" not in payload:
        raise ProviderError(f"codex 最終回覆不符 schema（缺 answer/sources）：{str(payload)[:300]}")
    answer_text = str(payload.get("answer") or "")
    sources = payload.get("sources")
    urls = [s for s in sources if isinstance(s, str)] if isinstance(sources, list) else []
    input_tokens, output_tokens = _codex_usage(events)
    return ProviderAnswer(
        text=answer_text,
        citations=dedupe_citations(urls),
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )


class CodexProvider:
    """本機 codex CLI（訂閱額度）。已知限制見模組設計決定 4／5。"""

    def __init__(self, *, model: str = DEFAULT_CODEX_MODEL, timeout: int = DEFAULT_TIMEOUT_SECONDS,
                 executable: str = "codex") -> None:
        self.name = "codex"
        self.model = model
        self._timeout = timeout
        self._executable = executable

    def _build_prompt(self, prompt: str) -> str:
        return (
            "（執行限制：只能使用 web_search 工具搜尋網路作答；禁止執行任何 shell 指令、"
            "禁止讀取或列出本機檔案系統，也不要嘗試存取工作目錄以外的任何路徑。此限制"
            "為 prompt 層級提醒，非強制沙箱保證，回答本身無需複述這段限制。）\n\n"
            + prompt
        )

    def answer(self, prompt: str) -> ProviderAnswer:
        with tempfile.TemporaryDirectory(prefix="ai-sov-codex-") as tmp:
            tmp_path = Path(tmp)
            schema_path = tmp_path / "schema.json"
            schema_path.write_text(json.dumps(CODEX_OUTPUT_SCHEMA), encoding="utf-8")
            args = [
                self._executable, "--search", "exec",
                "--skip-git-repo-check", "--ephemeral", "--json",
                "--ignore-user-config",
                "-m", self.model,
                "--sandbox", "read-only",
                "--output-schema", str(schema_path),
                "-C", tmp,
                self._build_prompt(prompt),
            ]
            stdout = _run_cli(args, timeout=self._timeout, cwd=tmp_path)
        return parse_codex_output(stdout)


# ══════════════════════════════════════════════════════════════════════
# Claude Code CLI
# ══════════════════════════════════════════════════════════════════════

def _websearch_call_count(events: list[dict]) -> int:
    """assistant 事件裡 tool_use(name=WebSearch) 的次數。

    不用 usage.server_tool_use.web_search_requests 判斷——探測證實這個
    欄位對 Claude Code 的 WebSearch 工具恆為 0（是這支 CLI 的統計缺口，
    不是『沒搜尋』的訊號），見設計決定 4。
    """
    count = 0
    for event in events:
        if event.get("type") != "assistant":
            continue
        for block in (event.get("message") or {}).get("content") or []:
            if isinstance(block, dict) and block.get("type") == "tool_use" and block.get("name") == "WebSearch":
                count += 1
    return count


def _websearch_result_urls(events: list[dict]) -> set[str]:
    """蒐集所有 WebSearch tool_result 裡『搜尋引擎實際回傳過』的 URL。

    優先讀結構化的 tool_use_result.results[].content[].url——這是 Claude
    Code 自己整理過的結果清單，比對 tool_result 的文字內容做 regex 抽取
    可靠。沒有這個欄位時才退回文字抽取，當作向後相容的備援路徑。

    ⚠ 實測（非探測樣本，真實重跑一次）發現 results 是**混型陣列**：同一次
    WebSearch 呼叫的 results 裡，除了帶 content 陣列的結構化搜尋結果 dict，
    還會混一個純字串（CLI 自己生成的搜尋摘要文字，不是搜尋結果）。逐項先
    判斷型別再處理，不假設整個陣列同型——這正是探測樣本沒有覆蓋到、只靠
    真實重跑才抓到的落差，因此修 fixture 之外也在這裡留一條註解說明原因。
    """
    urls: set[str] = set()
    for event in events:
        if event.get("type") != "user":
            continue
        tool_use_result = event.get("tool_use_result")
        if isinstance(tool_use_result, dict) and tool_use_result.get("results"):
            for result in tool_use_result.get("results") or []:
                if not isinstance(result, dict):
                    continue
                for item in result.get("content") or []:
                    url = item.get("url") if isinstance(item, dict) else None
                    if isinstance(url, str) and url:
                        urls.add(_strip_trailing_punctuation(url))
            continue
        for block in (event.get("message") or {}).get("content") or []:
            if not (isinstance(block, dict) and block.get("type") == "tool_result"):
                continue
            content = block.get("content")
            text = content if isinstance(content, str) else json.dumps(content, ensure_ascii=False)
            for match in _URL_RE.findall(text or ""):
                urls.add(_strip_trailing_punctuation(match))
    return urls


def _sources_section_urls(text: str) -> list[str]:
    """取回答文字裡『來源：』段落之後列出的 URL，依出現順序、不去重（去重交給 dedupe_citations）。"""
    match = _SOURCES_HEADING_RE.search(text)
    if not match:
        return []
    tail = text[match.end():]
    return [_strip_trailing_punctuation(u) for u in _URL_RE.findall(tail)]


def _result_event(events: list[dict]) -> dict:
    for event in reversed(events):
        if event.get("type") == "result":
            return event
    raise ProviderError("claude code 輸出裡沒有 result 事件，解析器可能已與 CLI 脫節")


def parse_claude_code_output(stdout: str) -> ProviderAnswer:
    """把 claude -p --output-format stream-json 的 stdout 轉成 ProviderAnswer。

    grounded 判定＝『來源：』段列出的 URL 與 WebSearch tool_result 實際
    回傳過的 URL 的交集（設計決定 4）。沒觸發過 WebSearch 時，即使回答
    文字裡剛好有「來源：」段也一律視為 ungrounded——那些網址從未被驗證，
    是模型自己編的，不是這次呼叫真的查到的。
    """
    events = list(_iter_jsonl_events(stdout))
    result = _result_event(events)
    if result.get("is_error"):
        raise ProviderError(f"claude code 回報錯誤：{str(result.get('result'))[:300]}")
    text = str(result.get("result") or "")

    searched = _websearch_call_count(events) > 0
    claimed_urls = _sources_section_urls(text) if searched else []
    grounded_urls: list[str] = []
    if claimed_urls:
        verified = _websearch_result_urls(events)
        grounded_urls = [u for u in claimed_urls if u in verified]
        unverified = [u for u in claimed_urls if u not in verified]
        if unverified:
            logger.warning(
                "claude-code 回答列出 %d 個未出現在 WebSearch 結果裡的網址，已濾除、不計入 citation：%s",
                len(unverified), unverified[:5],
            )

    usage = result.get("usage") or {}
    return ProviderAnswer(
        text=text,
        citations=dedupe_citations(grounded_urls),
        input_tokens=int(usage.get("input_tokens") or 0) + int(usage.get("cache_read_input_tokens") or 0),
        output_tokens=int(usage.get("output_tokens") or 0),
    )


class ClaudeCodeProvider:
    """本機 claude CLI（訂閱額度）。--allowedTools 白名單只留 WebSearch，
    是 CLI 層級的強制限制（不像 codex 只能靠 prompt 提醒），見模組設計決定 5。
    """

    def __init__(self, *, model: str = DEFAULT_CLAUDE_CODE_MODEL, timeout: int = DEFAULT_TIMEOUT_SECONDS,
                 executable: str = "claude", max_turns: int = DEFAULT_CLAUDE_CODE_MAX_TURNS) -> None:
        self.name = "claude-code"
        self.model = model
        self._timeout = timeout
        self._executable = executable
        self._max_turns = max_turns

    def answer(self, prompt: str) -> ProviderAnswer:
        full_prompt = f"{CLAUDE_CODE_SEARCH_DIRECTIVE}\n\n{prompt}"
        args = [
            self._executable, "-p", full_prompt,
            "--allowedTools", "WebSearch",
            "--output-format", "stream-json", "--verbose",
            "--max-turns", str(self._max_turns),
        ]
        if self.model:
            args += ["--model", self.model]
        with tempfile.TemporaryDirectory(prefix="ai-sov-claude-code-") as tmp:
            stdout = _run_cli(
                args, timeout=self._timeout, cwd=Path(tmp),
                # CLAUDECODE／CLAUDE_CODE_ENTRYPOINT 若殘留（例如本 provider
                # 本身被 Claude Code 呼叫時繼承的環境變數），子行程的 claude
                # CLI 會偵測到自己身處巢狀 session 而改變行為；顯式清掉這兩個
                # 變數才能保證它以獨立的非互動 session 執行（見探測命令）。
                unset_env=("CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT"),
            )
        return parse_claude_code_output(stdout)
