#!/bin/bash
# launchd 進入點：由 ~/.claude/automation/kb-launcher（已授 Full Disk Access）exec /bin/bash 本檔。
# 直接把 /usr/bin/make 放進 ProgramArguments 會在 launchd 環境被 TCC 擋住 ~/Documents（getcwd: Operation not permitted）。
# 參數可由環境變數覆寫：PROVIDER / REPEATS / CONCURRENCY。
set -euo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:${HOME}/.local/bin"
cd "$(dirname "$0")/.."
exec /usr/bin/make ai-sov-local "PROVIDER=${PROVIDER:-claude-code}" "REPEATS=${REPEATS:-3}" "CONCURRENCY=${CONCURRENCY:-2}"
