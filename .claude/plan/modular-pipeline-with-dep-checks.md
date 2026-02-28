# 計畫：模組化 Pipeline — 獨立執行 + 依賴檢查

> 日期：2026-02-28
> 狀態：v1 — 初始設計
> 前置計畫：[claude-code-llm-engine.md](./claude-code-llm-engine.md)（Step 0 基礎修正為本計畫前提）
> 研究佐證：[research/06-project-architecture.md](../../research/06-project-architecture.md)

---

## 一、問題描述

### 現況

目前所有 pipeline 分步執行都透過 `run_pipeline.py --step N`：

```bash
python scripts/run_pipeline.py --step 1   # 實際上 subprocess.run → 01_fetch_notion.py
python scripts/run_pipeline.py --step 2   # 實際上 subprocess.run → 02_extract_qa.py
```

**問題：**

| 問題                 | 說明                                                                                                                  |
| -------------------- | --------------------------------------------------------------------------------------------------------------------- |
| **不必要的間接層**   | `run_pipeline.py` 只是一個 subprocess 包裝，轉發 args 給子腳本，增加認知負擔                                          |
| **依賴檢查零散**     | Step 2 自己檢查 `raw_data/markdown/` 非空、Step 3 自己檢查 `qa_all_raw.json` 存在，但缺乏統一且完整的 pre-flight 檢查 |
| **無資料新鮮度檢查** | 沒有機制在 Step 3 執行前警告「`qa_all_raw.json` 已 14 天未更新」                                                      |
| **預設行為混淆**     | `run_pipeline.py --step 0`（=不指定）預設跑 1→2→3，但使用者可能只想檢查一步                                           |
| **config.py 副作用** | `import config` 會立即觸發 `_require_env()`，未設定 `OPENAI_API_KEY` 就連 Step 1（不需要 OpenAI）也無法啟動           |

### 目標設計

```bash
# 直接執行個別模組（不經過 run_pipeline.py）
python scripts/01_fetch_notion.py
python scripts/02_extract_qa.py --limit 3
python scripts/03_dedupe_classify.py
python scripts/04_generate_report.py
python scripts/05_evaluate.py --sample 50

# 每個模組啟動時自動：
#   1. 檢查前置步驟的產出檔案是否存在
#   2. 檢查資料新鮮度（超過閾值 → 警告但不阻斷）
#   3. 只驗證本步驟需要的 env vars（不強制不相關的 key）

# run_pipeline.py 仍然保留（作為 full pipeline 的便捷入口）
python scripts/run_pipeline.py              # 完整流程 1→2→3
python scripts/run_pipeline.py --step 4     # 單步仍可用
```

---

## 二、設計原則

### 2.1 來自 12-Factor App 的啟發

> 研究佐證：[12-Factor App — Dependencies](https://12factor.net/dependencies)

- **顯式宣告依賴**：每個模組在 module level 宣告自己需要的輸入檔案、env vars
- **Dev/prod 一致**：直接執行 Script 和透過 `run_pipeline.py` 行為完全一致
- **Fail-fast, but not fail-early**：缺少必要依賴時 hard exit（fail-fast），但不在 import 時就觸發（不 fail-early）

### 2.2 DAG-aware Task Orchestration

> 研究佐證：[Prefect — Task Dependencies](https://docs.prefect.io/latest/develop/write-tasks/)、
> [Airflow — TaskFlow API](https://airflow.apache.org/docs/apache-airflow/stable/tutorial/taskflow.html)

Pipeline 本質是一個 DAG：

```
Step 1 → Step 2 → Step 3 ─→ Step 4
                         └→ Step 5
```

每個 node（Step）宣告 upstream 依賴（input artifacts），但**不主動觸發** upstream —— 只做 **pre-flight check**。這和 Airflow 的 `ExternalTaskSensor` 或 Prefect 的 `task_input_hash` 理念一致：

- **不自動跑前置步驟**：避免意外的大量 API 呼叫（例如：跑 Step 3 不應自動觸發 Step 2 的 OpenAI 萃取）
- **告知使用者缺少什麼**：明確提示「請先執行 `python scripts/02_extract_qa.py`」
- **新鮮度只警告不阻斷**：使用者可能故意用舊資料做實驗

### 2.3 Lazy Config Loading

> 研究佐證：Django 的 [django.conf.LazySettings](https://docs.djangoproject.com/en/5.1/topics/settings/)

目前 `config.py` 在 import 時就呼叫 `_require_env()`，導致「只跑 Step 1 也要設 `OPENAI_API_KEY`」。改為 lazy pattern：

- **必需但延遲驗證**：env vars 在首次存取時才檢查，而非 module import 時
- **模組級別 env 宣告**：每個 Script 只在 main() 開頭驗證自己需要的 keys

---

## 三、依賴矩陣

### 3.1 檔案依賴（Artifact Dependencies）

| Step       | 輸入依賴                                                                 | 如何檢查       | 阻斷？                            |
| ---------- | ------------------------------------------------------------------------ | -------------- | --------------------------------- |
| **Step 1** | （無，pipeline 起點）                                                    | —              | —                                 |
| **Step 2** | `raw_data/markdown/*.md` ≥ 1 個                                          | glob count > 0 | **Hard exit**                     |
| **Step 3** | `output/qa_all_raw.json` 存在                                            | Path.exists()  | **Hard exit**                     |
| **Step 4** | `output/qa_final.json` + `output/qa_embeddings.npy`                      | Path.exists()  | **Soft**（`--no-qa` 可繞過）      |
| **Step 5** | `output/qa_final.json`（primary）或 `output/qa_all_raw.json`（fallback） | Path.exists()  | **Soft**（fallback 到較粗的資料） |

### 3.2 新鮮度規則（Staleness Rules）

| 依賴檔案                                    | 新鮮度閾值 | 行為                                                        |
| ------------------------------------------- | ---------- | ----------------------------------------------------------- |
| `raw_data/markdown/*.md`（Step 2 讀取）     | 14 天      | 警告：「Step 1 上次執行超過 14 天，可能有新會議紀錄未擷取」 |
| `output/qa_all_raw.json`（Step 3 讀取）     | 7 天       | 警告：「qa_all_raw.json 已 7 天未更新，考慮重跑 Step 2」    |
| `output/qa_final.json`（Step 4/5 讀取）     | 7 天       | 警告：「qa_final.json 已 7 天未更新，考慮重跑 Step 3」      |
| `output/qa_embeddings.npy`（Step 4/5 讀取） | 同上       | 與 `qa_final.json` 同步檢查                                 |

**新鮮度判斷依據：**

```python
# 方案 A：引用 Step 1 的 fetch_log（最精確，但耦合高）
# 方案 B：檔案 mtime（簡單、universal、不受 git 影響 ✅ 推薦）

from pathlib import Path
from datetime import datetime, timedelta

def check_freshness(path: Path, max_age: timedelta) -> tuple[bool, str]:
    """回傳 (is_fresh, message)"""
    mtime = datetime.fromtimestamp(path.stat().st_mtime)
    age = datetime.now() - mtime
    if age > max_age:
        days = age.days
        return False, f"⚠️  {path.name} 已 {days} 天未更新（上次修改：{mtime:%Y-%m-%d}）"
    return True, ""
```

### 3.3 環境變數依賴

| Step       | 必需 env vars    | 可選 env vars                            |
| ---------- | ---------------- | ---------------------------------------- |
| **Step 1** | `NOTION_TOKEN`   | `NOTION_PARENT_PAGE_ID`                  |
| **Step 2** | `OPENAI_API_KEY` | `OPENAI_MODEL`                           |
| **Step 3** | `OPENAI_API_KEY` | `OPENAI_MODEL`, `OPENAI_EMBEDDING_MODEL` |
| **Step 4** | `OPENAI_API_KEY` | `SHEETS_URL`, `OPENAI_MODEL`             |
| **Step 5** | `OPENAI_API_KEY` | `OPENAI_MODEL`, `LMNR_PROJECT_API_KEY`   |

---

## 四、共用依賴檢查模組：`utils/pipeline_deps.py`

### 4.1 核心 API

```python
"""
utils/pipeline_deps.py — 統一的 pipeline 依賴檢查

用法：
    from utils.pipeline_deps import preflight_check, StepDependency

    deps = [
        StepDependency(
            path=Path("output/qa_all_raw.json"),
            required=True,
            max_age_days=7,
            hint="請先執行 python scripts/02_extract_qa.py",
        ),
    ]
    preflight_check(deps, env_keys=["OPENAI_API_KEY"])
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path


@dataclass(frozen=True)
class StepDependency:
    """宣告一個 upstream artifact 依賴"""
    path: Path                          # 檔案或目錄路徑
    required: bool = True               # True=缺失時 hard exit，False=只警告
    max_age_days: int | None = None     # None=不檢查新鮮度
    min_count: int | None = None        # 目錄下最少要有幾個檔案（glob 用）
    glob_pattern: str | None = None     # 搭配 min_count 使用
    hint: str = ""                      # 缺失時顯示的修復提示


def preflight_check(
    deps: list[StepDependency],
    env_keys: list[str] | None = None,
    step_name: str = "",
) -> None:
    """
    執行 pre-flight 依賴檢查。

    - required=True 且缺失 → hard exit (sys.exit(1))
    - required=False 且缺失 → 印警告，繼續
    - max_age_days 超過 → 印警告，繼續（不阻斷）
    - env_keys 缺少 → hard exit
    """
    errors: list[str] = []
    warnings: list[str] = []

    # 1. 環境變數檢查
    for key in (env_keys or []):
        val = os.getenv(key)
        if not val or not val.strip():
            errors.append(f"❌ 環境變數 {key} 未設定")

    # 2. Artifact 檢查
    for dep in deps:
        if dep.glob_pattern and dep.min_count is not None:
            # 目錄 glob 模式
            matches = list(dep.path.glob(dep.glob_pattern))
            if len(matches) < dep.min_count:
                msg = f"{'❌' if dep.required else '⚠️ '} {dep.path}/{dep.glob_pattern} 找到 {len(matches)} 個檔案（需 ≥ {dep.min_count}）"
                if dep.hint:
                    msg += f"\n   💡 {dep.hint}"
                if dep.required:
                    errors.append(msg)
                else:
                    warnings.append(msg)
            # 用最新的 match 檢查新鮮度
            elif dep.max_age_days is not None and matches:
                newest = max(matches, key=lambda p: p.stat().st_mtime)
                _check_freshness(newest, dep.max_age_days, warnings)
        else:
            # 單檔模式
            if not dep.path.exists():
                msg = f"{'❌' if dep.required else '⚠️ '} 找不到 {dep.path}"
                if dep.hint:
                    msg += f"\n   💡 {dep.hint}"
                if dep.required:
                    errors.append(msg)
                else:
                    warnings.append(msg)
            elif dep.max_age_days is not None:
                _check_freshness(dep.path, dep.max_age_days, warnings)

    # 3. 輸出結果
    header = f"[{step_name}] " if step_name else ""
    if warnings:
        for w in warnings:
            print(f"   {w}")
    if errors:
        for e in errors:
            print(f"   {e}")
        print(f"\n{header}依賴檢查失敗，請先處理上述問題")
        sys.exit(1)
    else:
        print(f"   ✅ {header}依賴檢查通過")


def _check_freshness(
    path: Path,
    max_age_days: int,
    warnings: list[str],
) -> None:
    """檢查檔案新鮮度，超過閾值加入 warnings"""
    mtime = datetime.fromtimestamp(path.stat().st_mtime)
    age = datetime.now() - mtime
    if age > timedelta(days=max_age_days):
        warnings.append(
            f"⚠️  {path.name} 已 {age.days} 天未更新"
            f"（上次修改：{mtime:%Y-%m-%d}，建議 ≤ {max_age_days} 天）"
        )
```

### 4.2 各步驟的依賴宣告

```python
# ── scripts/01_fetch_notion.py ──
from utils.pipeline_deps import preflight_check

def main():
    preflight_check(
        deps=[],  # Step 1 無 upstream 依賴
        env_keys=["NOTION_TOKEN"],
        step_name="Step 1: Notion 擷取",
    )
    # ... 現有邏輯

# ── scripts/02_extract_qa.py ──
from utils.pipeline_deps import preflight_check, StepDependency

STEP2_DEPS = [
    StepDependency(
        path=ROOT_DIR / "raw_data" / "markdown",
        required=True,
        min_count=1,
        glob_pattern="*.md",
        max_age_days=14,
        hint="請先執行 python scripts/01_fetch_notion.py",
    ),
]

def main():
    preflight_check(
        deps=STEP2_DEPS,
        env_keys=["OPENAI_API_KEY"],
        step_name="Step 2: Q&A 萃取",
    )
    # ... 現有邏輯

# ── scripts/03_dedupe_classify.py ──
STEP3_DEPS = [
    StepDependency(
        path=OUTPUT_DIR / "qa_all_raw.json",
        required=True,
        max_age_days=7,
        hint="請先執行 python scripts/02_extract_qa.py",
    ),
]

def main():
    preflight_check(
        deps=STEP3_DEPS,
        env_keys=["OPENAI_API_KEY"],
        step_name="Step 3: 去重 + 分類",
    )

# ── scripts/04_generate_report.py ──
STEP4_DEPS = [
    StepDependency(
        path=OUTPUT_DIR / "qa_final.json",
        required=False,       # --no-qa 時可跳過
        max_age_days=7,
        hint="請先執行 python scripts/03_dedupe_classify.py（或用 --no-qa 略過）",
    ),
    StepDependency(
        path=OUTPUT_DIR / "qa_embeddings.npy",
        required=False,       # 同上
        max_age_days=7,
    ),
]

def main():
    preflight_check(
        deps=STEP4_DEPS,
        env_keys=["OPENAI_API_KEY"],
        step_name="Step 4: 週報生成",
    )

# ── scripts/05_evaluate.py ──
STEP5_DEPS = [
    StepDependency(
        path=OUTPUT_DIR / "qa_final.json",
        required=False,       # fallback to qa_all_raw.json
        max_age_days=7,
        hint="建議先執行 Step 3（或用 qa_all_raw.json fallback）",
    ),
]

def main():
    preflight_check(
        deps=STEP5_DEPS,
        env_keys=["OPENAI_API_KEY"],
        step_name="Step 5: 品質評估",
    )
```

---

## 五、config.py 改造：Lazy Env Validation

### 5.1 問題

```python
# 現狀：import config 就會觸發 _require_env()
NOTION_TOKEN = _require_env("NOTION_TOKEN")     # ← 沒設就 crash
OPENAI_API_KEY = _require_env("OPENAI_API_KEY")  # ← Step 1 不需要也 crash
```

### 5.2 解法：LazyEnv descriptor

```python
"""config.py — Lazy env loading"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── 路徑（無副作用，直接定義）─────────────────────
ROOT_DIR = Path(__file__).resolve().parent
RAW_JSON_DIR = ROOT_DIR / "raw_data" / "notion_json"
RAW_MD_DIR = ROOT_DIR / "raw_data" / "markdown"
IMAGES_DIR = ROOT_DIR / "raw_data" / "images"
OUTPUT_DIR = ROOT_DIR / "output"
QA_PER_MEETING_DIR = OUTPUT_DIR / "qa_per_meeting"

# ── Lazy env vars（首次存取時才驗證）────────────────

class _LazyEnv:
    """Descriptor：首次存取 env var 時才做 require 檢查"""

    def __init__(self, key: str, default: str | None = None):
        self._key = key
        self._default = default
        self._value: str | None = None
        self._resolved = False

    def __set_name__(self, owner, name):
        self._attr = name

    def __get__(self, obj, objtype=None):
        if not self._resolved:
            raw = os.getenv(self._key, self._default)
            if self._default is None and (not raw or not raw.strip()):
                raise ValueError(
                    f"必需環境變數 {self._key!r} 未設定。"
                    f"請在 .env 檔案或環境中設定後再執行。"
                )
            self._value = raw.strip() if raw else ""
            self._resolved = True
        return self._value


class _Config:
    NOTION_TOKEN = _LazyEnv("NOTION_TOKEN")
    NOTION_PARENT_PAGE_ID = _LazyEnv("NOTION_PARENT_PAGE_ID", default="")
    OPENAI_API_KEY = _LazyEnv("OPENAI_API_KEY")
    OPENAI_MODEL = _LazyEnv("OPENAI_MODEL", default="gpt-5.2")
    OPENAI_EMBEDDING_MODEL = _LazyEnv("OPENAI_EMBEDDING_MODEL", default="text-embedding-3-small")
    SHEETS_URL = _LazyEnv("SHEETS_URL", default="")


_cfg = _Config()

# 向下相容：保留 module-level 名稱
# 但存取時才觸發驗證（不在 import 時）
def __getattr__(name: str):
    """Module-level __getattr__ for lazy access"""
    if hasattr(_cfg, name):
        return getattr(_cfg, name)
    raise AttributeError(f"module 'config' has no attribute {name!r}")
```

> **研究佐證**：Python 3.7+ 支援 module-level `__getattr__`（[PEP 562](https://peps.python.org/pep-0562/)），正是為了 lazy attribute access 設計。Django、attrs、pydantic 都用類似 pattern。

### 5.3 向下相容性

| 現有用法                               | 改後行為                            |
| -------------------------------------- | ----------------------------------- |
| `import config; config.OPENAI_API_KEY` | 首次存取時驗證（不在 import 時） ✅ |
| `config.ROOT_DIR`                      | 路徑直接定義，無延遲 ✅             |
| `config.SIMILARITY_THRESHOLD`          | 非 env var，直接定義 ✅             |
| `check_config()` in run_pipeline.py    | 需改用 `os.getenv()` 直接檢查       |

---

## 六、run_pipeline.py 精簡

### 現有角色

1. CLI arg parser（轉發到子腳本）
2. `check_config()` 粗略驗證
3. 迴圈呼叫 subprocess
4. 計時與輸出

### 改後角色

- **保留為「全流程便捷入口」**，不刪除
- 移除 `check_config()`（各 Script 自帶 `preflight_check`）
- 簡化 arg 轉發（不再重複定義所有子腳本的 args）
- 加入一個 `--check` flag：只做 pre-flight 檢查，不執行

```python
def main():
    parser = argparse.ArgumentParser(description="SEO Q&A Pipeline 主控")
    parser.add_argument("--step", type=int, choices=[1, 2, 3, 4, 5], default=0)
    parser.add_argument("--check", action="store_true", help="只執行依賴檢查，不實際跑")
    # 僅保留少量 top-level flags，其餘透過 -- 轉發
    args, remaining = parser.parse_known_args()

    steps = [args.step] if args.step else [1, 2, 3]
    scripts = {1: "01_fetch_notion.py", 2: "02_extract_qa.py", ...}

    for step in steps:
        cmd = [sys.executable, scripts[step]] + remaining
        if args.check:
            cmd.append("--check")   # 子腳本也需支援 --check
        result = subprocess.run(cmd, cwd=ROOT_DIR)
        if result.returncode != 0:
            sys.exit(1)
```

---

## 七、README.md 更新

### 分步執行區段改寫

````markdown
### 分步執行

每個步驟都可以直接執行，啟動時自動檢查前置步驟的資料是否就緒：

\```bash

# 步驟 1：從 Notion 擷取

python scripts/01_fetch_notion.py
python scripts/01_fetch_notion.py --force # 全量重抓
python scripts/01_fetch_notion.py --since 7d # 只抓 7 天內更新的

# 步驟 2：OpenAI 萃取 Q&A

python scripts/02_extract_qa.py # 增量模式
python scripts/02_extract_qa.py --limit 3 # 先試 3 份
python scripts/02_extract_qa.py --force # 全部重新處理

# → 自動檢查：raw_data/markdown/ 是否有 .md 檔案

# 步驟 3：去重 + 分類

python scripts/03_dedupe_classify.py
python scripts/03_dedupe_classify.py --skip-dedup # 只分類
python scripts/03_dedupe_classify.py --limit 30 # 測試模式

# → 自動檢查：output/qa_all_raw.json 是否存在

# 步驟 4：產生每週 SEO 週報

python scripts/04_generate_report.py
python scripts/04_generate_report.py --no-qa # 不使用知識庫

# → 自動檢查：output/qa_final.json 是否存在（--no-qa 可跳過）

# 步驟 5：品質評估

python scripts/05_evaluate.py
python scripts/05_evaluate.py --sample 50 --with-source

# → 自動檢查：output/qa_final.json（fallback: qa_all_raw.json）

\```

#### 只檢查依賴（不執行）

\```bash
python scripts/02_extract_qa.py --check

# 輸出：✅ Step 2: Q&A 萃取 依賴檢查通過

# 或： ❌ raw_data/markdown/\*.md 找到 0 個檔案（需 ≥ 1）

# 💡 請先執行 python scripts/01_fetch_notion.py

\```

#### 全流程（保留向下相容）

\```bash
python scripts/run_pipeline.py # 完整 1→2→3
python scripts/run_pipeline.py --step 4 # 單步也行
python scripts/run_pipeline.py --check # 只檢查所有步驟的依賴
\```
````

---

## 八、與 claude-code-llm-engine.md 的關係

本計畫是 **claude-code-llm-engine.md 的前置作業**，兩者的先後順序：

```
本計畫（模組化 + 依賴檢查）
  └─ config.py lazy loading       ← 解除 import config 的 env 副作用
  └─ utils/pipeline_deps.py      ← 統一依賴檢查 API
  └─ 各 Script 加入 preflight    ← 直接執行能力
  └─ README.md 更新              ← 文件同步

claude-code-llm-engine.md Step 0（基礎修正）
  └─ stable_id                   ← 需要先有模組化，因為 qa_tools.py 也要用 preflight
  └─ merged_from.source_file     ← 同上
  └─ qa_embeddings_index.json    ← 同上

claude-code-llm-engine.md Step 2+（qa_tools.py 等）
  └─ 建立在 preflight + lazy config 之上
```

**特別注意**：`qa_tools.py`（claude-code-llm-engine.md 設計的工具）禁止 `import config`（避免觸發 `OPENAI_API_KEY` 檢查）。Lazy config 做完後，這個限制可以放寬，但仍建議 `qa_tools.py` 使用 `pipeline_deps.py` 做自己的 env 檢查，保持模組獨立性。

---

## 九、實作步驟（依序）

### Phase 1：基礎設施（± 4 小時）

| #   | 任務                                 | 影響檔案                      | 風險               |
| --- | ------------------------------------ | ----------------------------- | ------------------ |
| 1.1 | 新建 `utils/pipeline_deps.py`        | 新檔案                        | 無                 |
| 1.2 | 為 `pipeline_deps.py` 寫 unit tests  | `tests/test_pipeline_deps.py` | 無                 |
| 1.3 | config.py 改 lazy loading（PEP 562） | `config.py`                   | **中**（全域影響） |
| 1.4 | config.py 改後執行全量測試           | —                             | —                  |

### Phase 2：各模組加入 preflight（± 3 小時）

| #   | 任務                                                           | 影響檔案                        |
| --- | -------------------------------------------------------------- | ------------------------------- |
| 2.1 | `01_fetch_notion.py` 加入 preflight（env only）                | `scripts/01_fetch_notion.py`    |
| 2.2 | `02_extract_qa.py` 加入 preflight（替換現有的 hard exit）      | `scripts/02_extract_qa.py`      |
| 2.3 | `03_dedupe_classify.py` 加入 preflight（替換現有的 hard exit） | `scripts/03_dedupe_classify.py` |
| 2.4 | `04_generate_report.py` 加入 preflight（soft dep）             | `scripts/04_generate_report.py` |
| 2.5 | `05_evaluate.py` 加入 preflight（soft dep）                    | `scripts/05_evaluate.py`        |
| 2.6 | 所有腳本加入 `--check` flag（只做 preflight，不執行）          | 以上所有                        |

### Phase 3：run_pipeline.py 精簡 + README 更新（± 2 小時）

| #   | 任務                                                        | 影響檔案                  |
| --- | ----------------------------------------------------------- | ------------------------- |
| 3.1 | `run_pipeline.py` 移除 `check_config()`，改用子腳本自帶檢查 | `scripts/run_pipeline.py` |
| 3.2 | `run_pipeline.py` 加入 `--check` flag                       | 同上                      |
| 3.3 | README.md 「分步執行」區段改寫                              | `README.md`               |
| 3.4 | README.md 「建議的工作流程」加入依賴檢查說明                | `README.md`               |
| 3.5 | Makefile 加入 `make check`（= `run_pipeline.py --check`）   | `Makefile`                |

### Phase 4：整合測試（± 1 小時）

| #   | 任務                                                                                       |
| --- | ------------------------------------------------------------------------------------------ |
| 4.1 | 測試：未設 `OPENAI_API_KEY`，`python scripts/01_fetch_notion.py` 應能正常執行              |
| 4.2 | 測試：未設 `NOTION_TOKEN`，`python scripts/02_extract_qa.py` 不應在 import 階段 crash      |
| 4.3 | 測試：`output/qa_all_raw.json` 不存在時，`python scripts/03_dedupe_classify.py` 給明確提示 |
| 4.4 | 測試：`python scripts/run_pipeline.py --check` 列出所有步驟的依賴狀態                      |
| 4.5 | 全量 `pytest tests/ -v` 通過                                                               |

---

## 十、成功標準

### 功能面

- [ ] 每個 Script（01-05）可直接 `python scripts/0N_xxx.py` 執行，無需 `run_pipeline.py`
- [ ] 缺少前置步驟產出時，給出明確提示（檔案名 + 修復指令）
- [ ] 資料超過閾值天數時，給出新鮮度警告（不阻斷）
- [ ] `--check` flag 只做依賴檢查，不執行任何 API 呼叫
- [ ] 未設 `OPENAI_API_KEY` 時，Step 1 可正常執行
- [ ] `run_pipeline.py` 一鍵流程行為不變（向下相容）

### 品質面

- [ ] `utils/pipeline_deps.py` 有 ≥ 80% 測試覆蓋率
- [ ] config.py lazy loading 不破壞現有 23 個 tests
- [ ] 零 hardcoded paths（全部來自 config.py 或相對路徑）

### 文件面

- [ ] README.md 「分步執行」區段反映新的直接執行方式
- [ ] research/06-project-architecture.md 更新 Changelog
- [ ] Makefile 新增 `make check` target

---

## 十一、風險與緩解

| 風險                                   | 影響       | 機率 | 緩解                                                           |
| -------------------------------------- | ---------- | ---- | -------------------------------------------------------------- |
| config.py lazy loading 破壞現有 import | 全域       | 中   | Phase 1.4 全量測試；PEP 562 是官方機制                         |
| 多處 `import config` 的使用方式不統一  | 可能漏改   | 低   | grep 所有 `config.NOTION_TOKEN` / `config.OPENAI_API_KEY` 用例 |
| `--check` flag 與現有 args 衝突        | CLI        | 低   | 先做 `parse_known_args()` 確認無衝突                           |
| mtime 被 git checkout 重置             | 新鮮度誤報 | 低   | git 預設保留 mtime；若需要可改用 fetch_log 時間戳              |

---

## 附錄：研究佐證彙整

| 主題                    | 來源                                                                                                                                                                                                                | 應用                                                  |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------- |
| DAG task orchestration  | [Prefect Task Dependencies](https://docs.prefect.io/latest/develop/write-tasks/)、[Airflow TaskFlow](https://airflow.apache.org/docs/apache-airflow/stable/tutorial/taskflow.html)                                  | pre-flight check 不自動觸發 upstream，只檢查 artifact |
| Lazy config loading     | [PEP 562 — Module **getattr**](https://peps.python.org/pep-0562/)、[Django LazySettings](https://docs.djangoproject.com/en/5.1/topics/settings/)                                                                    | config.py 延遲驗證 env vars                           |
| 12-Factor Dependencies  | [12factor.net/dependencies](https://12factor.net/dependencies)                                                                                                                                                      | 顯式宣告依賴，取代隱式側效應                          |
| Fail-fast principle     | [Martin Fowler — Fail Fast](https://www.martinfowler.com/ieeeSoftware/failFast.pdf)                                                                                                                                 | 缺依賴時立即 exit，不讓錯誤傳播                       |
| Data pipeline freshness | [Great Expectations — Data Freshness](https://docs.greatexpectations.io/docs/reference/expectations/data_quality_use_cases/freshness)、[dbt source freshness](https://docs.getdbt.com/docs/deploy/source-freshness) | max_age_days 閾值設計                                 |
