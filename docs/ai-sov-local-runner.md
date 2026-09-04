# AI SoV 本機 CLI Provider 跑法

> 適用於 `scripts/ingest_ai_sov.py --provider codex` 與 `--provider claude-code`——
> 用使用者機器上已登入的 `codex` / `claude` CLI 訂閱額度跑週級 AI SoV 量測，
> 不走 OpenAI API 計費。與 `.github/workflows/ai-sov-weekly.yml`（走 `openai` provider、
> 在 GitHub Actions runner 上跑）是**兩條互不相依的路徑**：workflow 不變、繼續用
> API key；本機路徑是額外選項，不是取代。

---

## 為什麼需要這條路徑

`openai` provider 每次呼叫都是計費的 API 請求；`codex` / `claude-code` 這兩個
provider 改叫本機已登入的 CLI，problem 從「多花 API 費用」變成「多花訂閱裡的
用量額度」。細節與已知限制見 `scripts/ai_sov_cli_providers.py` 模組 docstring
（探測證據、grounded 判定、codex 無法完全關掉 shell 工具等）。

---

## 前置條件

```bash
# 1. 確認 CLI 已安裝且已登入（各自檢查一次即可，之後長期有效）
codex --version
claude --version

# 2. 確認 .env 有 Supabase 寫入憑證（本機路徑一樣寫同一張表，走同一個 warehouse 層）
grep SUPABASE_URL .env
grep SUPABASE_SERVICE_KEY .env

# 3. Python 虛擬環境（跑 ingest 腳本本身，不需要另裝 SDK——CLI 呼叫走 subprocess）
source .venv/bin/activate
```

---

## 執行

```bash
# 預設 codex、repeats=3、concurrency=2
make ai-sov-local

# 換 provider / 調參數
make ai-sov-local PROVIDER=claude-code REPEATS=3 CONCURRENCY=1

# 直接呼叫腳本（等效，Makefile target 只是包了 log 導出與預設值）
.venv/bin/python scripts/ingest_ai_sov.py --execute \
  --provider codex --repeats 3 --concurrency 2
```

log 會同時印到終端機、附加寫入 `output/ai-sov/<今天日期>.log`（`make` target
自動 `mkdir -p output/ai-sov` 並用 `tee -a`）。

### Smoke（不寫入 Supabase）

```bash
# --max-prompts 只跑前 N 條、強制 dry-run（腳本層驗證，不能與 --execute 併用）
.venv/bin/python scripts/ingest_ai_sov.py --provider codex --repeats 1 --max-prompts 2
.venv/bin/python scripts/ingest_ai_sov.py --provider claude-code --repeats 1 --max-prompts 1
```

### 驗證上一次寫入

```bash
.venv/bin/python scripts/ingest_ai_sov.py --verify
```

---

## `--concurrency` 怎麼選

每題實測 56～70 秒。36 prompt × 3 repeats = 108 次呼叫，序跑（concurrency=1）
約需 2 小時；concurrency=2～4 大致把牆鐘時間除以並行度，但不是線性——codex／
claude CLI 各自對它們的後端有自己的並行請求限制，開太多只會把部分呼叫擠成
逾時或 429，不是更快。上限在 `ingest_ai_sov.py` 的 `MAX_CONCURRENCY = 4` 硬擋。

建議：先用 concurrency=2 跑一次觀察有沒有大量逾時／失敗，穩定的話再往上調。

---

## 訂閱額度考量

- **Codex**：`--search` 模式每題的 `input_tokens` 實測約 15 萬，其中大部分
  （實測約 6 成）是 `cached_input_tokens`——命中快取的部分通常不計入額度或
  計費倍率遠低於未命中部分，但仍計入單次呼叫的 context 消耗。108 次呼叫的
  累積 token 量不小，若訂閱方案有週期性用量上限，先用 `--max-prompts` 小量
  跑過一次確認單題耗用量，再排進正式週跑。
- **Claude Code**：token 消耗主要看 WebSearch 觸發次數與回應長度；
  `--max-turns 8` 已經限制每次呼叫最多回合數，避免單一 prompt 因為模型
  反覆搜尋而暴衝。

兩者都沒有像 OpenAI Responses API 那樣「按 token 計費、金額透明」的即時反饋，
訂閱額度的實際耗用速度需要靠跑過幾次之後回頭看 CLI 自己的用量面板估算。

---

## 已知限制（跑之前要知道的事）

- **資料無法回填。** 機器沒開的那一週就是缺，沒有人能事後問「上週的 LLM
  會怎麼回答」。與 `ai-sov-weekly.yml` 的 workflow docstring 描述的限制
  完全一樣，本機路徑額外多一層：workflow 在 CI runner 上跑，機器一定在；
  本機路徑要求「使用者的機器那天有開機、CLI 額度沒被別的任務用掉」。
- **codex 的 shell 工具沒有結構性關掉的選項，但根因已找到並修掉。**
  第一次探測發現 codex 會主動搜尋、讀取 sandbox 目錄以外的檔案（含使用者
  home 目錄下其他 repo 的 AGENTS.md／CLAUDE.md）。根因是使用者本機
  `~/.codex/config.toml` 的 `persistent_instructions` 明講「Follow project
  AGENTS.md guidelines」，等於系統提示教它去找專案文件。CodexProvider 已
  帶 `--ignore-user-config`（不載入該設定檔，登入憑證不受影響）——實測
  同一個 prompt 加上這個旗標後完全沒有 command_execution 事件，
  input_tokens 也從 ~15.7 萬降到 ~11.7 萬。但這**不是**『CLI 層級白名單』
  那種結構性保證：--ignore-user-config 移除的是誘發探索的那個持久化提示，
  不是拿掉 shell 這個工具本身，模型理論上仍可能因為別的理由呼叫它。仍保留
  `--sandbox read-only` + prompt 提醒兩層防禦深度。介意這個差異的話選
  `claude-code`——`--allowedTools WebSearch` 是 CLI 層級白名單，沒被列入的
  工具連呼叫機會都沒有，不依賴系統提示內容，是真正的結構性保證。
- **grounded 判定的可信度不對稱。** claude-code 有『來源 URL ∩ 搜尋結果 URL』
  的交叉驗證；codex 因為 CLI 沒有把搜尋結果 URL 曝露在事件流裡，只能信任
  `--output-schema` 強制的結構化輸出本身，是弱一階的保證。兩個 provider 的
  週級數字因此不完全等質，跨 provider 比較 SoV 數字時要記得這點。

---

## launchd 排程範本（僅供參考，未安裝）

以下 plist 示範「每週一本地時間 07:00 自動跑一次」。**這是範本，本次交付
沒有安裝它**——是否要排程、排到哪台機器，由使用者自行決定並手動安裝。

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>cc.vocus.ai-sov-local</string>

  <key>ProgramArguments</key>
  <array>
    <string>/usr/bin/make</string>
    <string>-C</string>
    <string>/absolute/path/to/seo-knowledge-insight</string>
    <string>ai-sov-local</string>
    <string>PROVIDER=codex</string>
    <string>REPEATS=3</string>
    <string>CONCURRENCY=2</string>
  </array>

  <key>StartCalendarInterval</key>
  <dict>
    <key>Weekday</key>
    <integer>1</integer>  <!-- 1 = 週一 -->
    <key>Hour</key>
    <integer>7</integer>
    <key>Minute</key>
    <integer>0</integer>
  </dict>

  <key>StandardOutPath</key>
  <string>/absolute/path/to/seo-knowledge-insight/output/ai-sov/launchd.out.log</string>
  <key>StandardErrorPath</key>
  <string>/absolute/path/to/seo-knowledge-insight/output/ai-sov/launchd.err.log</string>

  <!-- codex/claude CLI 的登入憑證通常存在使用者 keychain／設定檔裡，
       launchd 以背景 daemon 身分執行時不一定能存取到與互動終端機相同的
       環境（PATH、keychain unlock 狀態）。裝之前先用同一組
       ProgramArguments 手動跑一次確認能通，不要假設裝上去就會動。 -->
</dict>
</plist>
```

安裝方式（**未執行，供之後手動操作時參考**）：

```bash
cp this.plist ~/Library/LaunchAgents/cc.vocus.ai-sov-local.plist
launchctl load ~/Library/LaunchAgents/cc.vocus.ai-sov-local.plist
```

機器睡眠/關機時 launchd 排程不會補跑錯過的那次——這正是上面「資料無法
回填」那條限制在排程層面的體現，不是 launchd 設定的問題。
