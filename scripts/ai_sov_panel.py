"""
ai_sov_panel.py — AI SoV prompt panel 的載入與驗證（S6.2）

被 scripts/ingest_ai_sov.py 使用。本檔只做「讀檔 + 驗證結構」，不發任何
HTTP 請求——單元測試可以直接 import 驗 panel 本身，不需要 mock 網路
（與 quality_gate_config.py 之於 data_quality_gate.py 是同一種拆法）。


═══ 為什麼 panel 是 repo 內的靜態檔案 ═══

任務書 Security 段對 S6.2 的要求：「prompt panel 為 repo 內靜態清單、不接受
外部輸入，避免 prompt injection 面」。

具體是這樣運作的：ingest 腳本把 panel 裡的字串直接當成送給 LLM 的 input。
如果這份清單可以被外部來源（GSC API 回應、使用者輸入、資料庫某張表）動態
填充，那條路徑上的任何一方就能決定我們對 LLM 說什麼——而我們又拿 LLM 的
回應去寫資料庫。本檔的驗證因此不是「防呆」，是**信任邊界的實作點**：

  1. 只從 repo 內的固定路徑讀（load_panel 的 path 參數只給測試用）。
  2. 每個欄位的型別與值域都驗，控制字元一律拒絕——LLM 的 input 裡混進
     換行以外的控制字元沒有任何正當用途，卻是最常見的越界注入手法。
  3. 驗證失敗一律拋例外，不做「跳過這一條繼續跑」的降級——panel 少一條
     prompt 會讓週級比例的分母悄悄改變，那是任務書禁止的靜默降級。

═══ 為什麼 20–50 這個範圍是硬限制 ═══

下界：樣本太少時週級比例的解析度不夠（20 prompt × 3 次 = 60 個樣本，
一個 prompt 全滅就讓整體掉 5 個百分點）。
上界：每週的 API 呼叫數 = prompt 數 × 重複次數，50 × 3 = 150 次已經是
這個低成熟度指標值得花的成本上限（費用估算見 S6.2 報告）。
兩個界都寫成 assert 而不是註解，因為改 panel 的人不會回來讀這段。
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
PANEL_PATH = ROOT_DIR / "data" / "ai_sov_prompts.json"

MIN_PROMPTS = 20
MAX_PROMPTS = 50
ID_RE = re.compile(r"^[a-z0-9][a-z0-9\-]{1,63}$")
THEME_RE = re.compile(r"^[a-z0-9][a-z0-9\-]{1,63}$")
# 允許一般可見字元與空白；拒絕 C0/C1 控制字元（含換行——panel 的 prompt 是單句問題，
# 不需要換行，而換行是把額外指令夾帶進 LLM input 最常見的形狀）。
CONTROL_CHAR_RE = re.compile(r"[\x00-\x1f\x7f-\x9f]")
MAX_PROMPT_CHARS = 300


class PanelError(ValueError):
    """panel 結構不合法。呼叫端不得吞掉——少一條 prompt 就是分母悄悄變了。"""


@dataclass(frozen=True)
class PanelPrompt:
    id: str
    theme: str
    prompt: str
    source_query: str


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise PanelError(message)


def _validate_text(value: object, field: str, where: str, *, max_chars: int) -> str:
    _require(isinstance(value, str), f"{where}: {field} 必須是字串，實得 {type(value).__name__}")
    text = str(value)
    _require(not CONTROL_CHAR_RE.search(text), f"{where}: {field} 含控制字元（含換行），一律拒絕")
    _require(len(text) <= max_chars, f"{where}: {field} 超過 {max_chars} 字元（實得 {len(text)}）")
    return text


def _parse_prompt(raw: object, index: int) -> PanelPrompt:
    where = f"prompts[{index}]"
    _require(isinstance(raw, dict), f"{where}: 必須是物件")
    entry = dict(raw)  # type: ignore[arg-type]

    prompt_id = _validate_text(entry.get("id"), "id", where, max_chars=64)
    _require(bool(ID_RE.match(prompt_id)), f"{where}: id={prompt_id!r} 不符 {ID_RE.pattern}")

    theme = _validate_text(entry.get("theme"), "theme", where, max_chars=64)
    _require(bool(THEME_RE.match(theme)), f"{where}: theme={theme!r} 不符 {THEME_RE.pattern}")

    prompt = _validate_text(entry.get("prompt"), "prompt", where, max_chars=MAX_PROMPT_CHARS)
    _require(len(prompt.strip()) >= 8, f"{where}: prompt 過短，不像一個問題句")

    source_query = _validate_text(entry.get("source_query", ""), "source_query", where, max_chars=200)
    return PanelPrompt(id=prompt_id, theme=theme, prompt=prompt, source_query=source_query)


def _validate_panel_shape(payload: object) -> dict:
    _require(isinstance(payload, dict), "panel 根節點必須是物件")
    doc = dict(payload)  # type: ignore[arg-type]
    _require(doc.get("version") == 1, f"panel version 必須是 1，實得 {doc.get('version')!r}")
    target = doc.get("target_domain")
    _require(isinstance(target, str) and bool(target), "panel 缺少 target_domain")
    _require(isinstance(doc.get("prompts"), list), "panel 缺少 prompts 陣列")
    return doc


def load_panel(path: Path | None = None) -> tuple[PanelPrompt, ...]:
    """讀取並驗證 prompt panel。任何結構問題一律拋 PanelError，不做部分載入。"""
    panel_path = path or PANEL_PATH
    doc = _validate_panel_shape(json.loads(panel_path.read_text(encoding="utf-8")))

    prompts = tuple(_parse_prompt(raw, i) for i, raw in enumerate(doc["prompts"]))
    _require(
        MIN_PROMPTS <= len(prompts) <= MAX_PROMPTS,
        f"panel 需 {MIN_PROMPTS}–{MAX_PROMPTS} 條 prompt，實得 {len(prompts)}",
    )
    ids = [p.id for p in prompts]
    _require(len(ids) == len(set(ids)), f"panel 有重複的 id：{sorted({i for i in ids if ids.count(i) > 1})}")
    texts = [p.prompt for p in prompts]
    _require(len(texts) == len(set(texts)), "panel 有重複的 prompt 文字（重複問句等於偷偷加權那個主題）")
    return prompts


def panel_target_domain(path: Path | None = None) -> str:
    """panel 宣告的目標網域。與 provider 端的判定分開，避免兩處各寫一個常數。"""
    doc = _validate_panel_shape(json.loads((path or PANEL_PATH).read_text(encoding="utf-8")))
    return str(doc["target_domain"])
