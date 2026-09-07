#!/bin/bash
# launchd 進入點：由 ~/.claude/automation/kb-launcher（已授 Full Disk Access）exec /bin/bash 本檔。
# 直接把 /usr/bin/make 放進 ProgramArguments 會在 launchd 環境被 TCC 擋住 ~/Documents（getcwd: Operation not permitted）。
# 參數可由環境變數覆寫：PROVIDER / REPEATS / CONCURRENCY。
#
# 週一登記多個觸發時段（照 claude-reports 的做法：筆電睡著錯過一個還有下一個）。
# 同一週只跑一次：成功後在 output/ai-sov/ 留 .done-<week_start> 標記，之後的時段看到標記就 SKIP。
#   FORCE=1                  — 忽略標記強制重跑（會 upsert 覆寫本週資料）
#   WEEK_START_OVERRIDE=YYYY-MM-DD — 測試用，指定週標籤
set -euo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:${HOME}/.local/bin"
cd "$(dirname "$0")/.."

# week_start 與 ingest_ai_sov.py 一致：UTC 當週週一
week_start="${WEEK_START_OVERRIDE:-$(python3 -c 'import datetime as d; n=d.datetime.now(d.timezone.utc).date(); print(n - d.timedelta(days=n.weekday()))')}"
marker="output/ai-sov/.done-${week_start}"
mkdir -p output/ai-sov
if [ "${FORCE:-}" != "1" ] && [ -f "$marker" ]; then
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] SKIP week_start=${week_start} 已跑過（$(cat "$marker")）"
  exit 0
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] START week_start=${week_start} provider=${PROVIDER:-claude-code}"
/usr/bin/make ai-sov-local "PROVIDER=${PROVIDER:-claude-code}" "REPEATS=${REPEATS:-3}" "CONCURRENCY=${CONCURRENCY:-2}"
echo "done $(date '+%Y-%m-%dT%H:%M:%S%z') provider=${PROVIDER:-claude-code}" > "$marker"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] DONE week_start=${week_start} marker=${marker}"
