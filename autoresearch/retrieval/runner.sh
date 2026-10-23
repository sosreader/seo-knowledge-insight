#!/usr/bin/env bash
# autoresearch/runner.sh — Single experiment runner for retrieval optimization.
#
# Checks server health, runs eval_local.py, parses composite score,
# compares with previous best, and appends to results.tsv.
#
# Usage:
#   bash autoresearch/runner.sh
#   bash autoresearch/runner.sh "description of this experiment"
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
RESULTS_TSV="$SCRIPT_DIR/results.tsv"
BASELINE_JSON="$SCRIPT_DIR/baseline.json"
EVAL_SCRIPT="$SCRIPT_DIR/eval_local.py"
PYTHON="${PROJECT_ROOT}/.venv/bin/python"

# Target: online rag-api by default; local rag-api: RAG_API_BASE=http://localhost:8080
API_BASE="${RAG_API_BASE:-https://warehouse-api.vocus.cc/internal/rag}"
API_BASE="${API_BASE%/}"
DESCRIPTION="${1:-no description}"

# Load API key from .env if not already set
if [ -z "${SEO_API_KEY:-}" ] && [ -f "$PROJECT_ROOT/.env" ]; then
    SEO_API_KEY=$(grep '^SEO_API_KEY=' "$PROJECT_ROOT/.env" | cut -d= -f2)
fi
API_KEY="${SEO_API_KEY:-}"

# ── 1. Check server reachability (+ auth) ────────────────────────────────────
# Auth headers come from env (CF Access pair preferred, else SEO_API_KEY); never echoed.

AUTH_ARGS=()
if [ -n "${CF_ACCESS_CLIENT_ID:-}" ] && [ -n "${CF_ACCESS_CLIENT_SECRET:-}" ]; then
    AUTH_ARGS=(-H "CF-Access-Client-Id: ${CF_ACCESS_CLIENT_ID}" -H "CF-Access-Client-Secret: ${CF_ACCESS_CLIENT_SECRET}")
elif [ -n "$API_KEY" ]; then
    AUTH_ARGS=(-H "X-API-Key: ${API_KEY}")
fi

if ! curl -sf ${AUTH_ARGS[@]+"${AUTH_ARGS[@]}"} "${API_BASE}/qa?limit=1" > /dev/null 2>&1; then
    echo "ERROR: rag-api not reachable or unauthorized at ${API_BASE}" >&2
    echo "Online: set CF_ACCESS_CLIENT_ID / CF_ACCESS_CLIENT_SECRET. Local: RAG_API_BASE=http://localhost:8080" >&2
    exit 2
fi

# ── 2. Run eval ──────────────────────────────────────────────────────────────

EVAL_OUTPUT=$("$PYTHON" "$EVAL_SCRIPT" --api-base "$API_BASE" ${API_KEY:+--api-key "$API_KEY"})
EVAL_EXIT=$?

if [ $EVAL_EXIT -ne 0 ]; then
    echo "ERROR: eval_local.py failed with exit code $EVAL_EXIT" >&2
    exit 1
fi

# ── 3. Parse results ─────────────────────────────────────────────────────────

COMPOSITE=$(echo "$EVAL_OUTPUT" | grep '^COMPOSITE_SCORE=' | tail -1 | cut -d= -f2)
METRICS=$(echo "$EVAL_OUTPUT" | grep '^METRICS=' | tail -1 | cut -d= -f2-)

if [ -z "$COMPOSITE" ]; then
    echo "ERROR: Could not parse COMPOSITE_SCORE from eval output" >&2
    exit 1
fi

# ── 4. Get previous best ────────────────────────────────────────────────────

# Read previous best from results.tsv (last non-header line with status=keep)
PREV_BEST=""
if [ -f "$RESULTS_TSV" ] && [ "$(wc -l < "$RESULTS_TSV")" -gt 1 ]; then
    # Get the best composite from all 'keep' entries, or latest if none
    KEEP_SCORES=$(awk -F'\t' 'NR>1 && $12=="keep" {print $2}' "$RESULTS_TSV")
    if [ -n "$KEEP_SCORES" ]; then
        PREV_BEST=$(echo "$KEEP_SCORES" | sort -rn | head -1)
    else
        # No keeps yet, use latest entry
        PREV_BEST=$(awk -F'\t' 'NR>1 {score=$2} END {print score}' "$RESULTS_TSV")
    fi
fi

# Fallback to baseline.json
if [ -z "$PREV_BEST" ] && [ -f "$BASELINE_JSON" ]; then
    PREV_BEST=$("$PYTHON" -c "import json; print(json.load(open('$BASELINE_JSON'))['composite_score'])")
fi

PREV_BEST="${PREV_BEST:-0.000000}"

# ── 5. Compute delta ─────────────────────────────────────────────────────────

DELTA=$("$PYTHON" -c "print(f'{${COMPOSITE} - ${PREV_BEST}:+.6f}')")

# ── 6. Git hash ──────────────────────────────────────────────────────────────

GIT_HASH=$(git -C "$PROJECT_ROOT" rev-parse --short=7 HEAD 2>/dev/null || echo "unknown")

# ── 7. Append to results.tsv ────────────────────────────────────────────────

TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
# status is empty — agent decides keep/discard after reading this output
printf '%s\t%s\t%s\t%s\t\t%s\n' \
    "$TIMESTAMP" "$COMPOSITE" "$METRICS" "$GIT_HASH" "$DESCRIPTION" \
    >> "$RESULTS_TSV"

# ── 8. Output for agent ─────────────────────────────────────────────────────

echo "---"
echo "COMPOSITE_SCORE=${COMPOSITE}"
echo "PREV_BEST=${PREV_BEST}"
echo "DELTA=${DELTA}"
echo "GIT_HASH=${GIT_HASH}"
echo "---"
