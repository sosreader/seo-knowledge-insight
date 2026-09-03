"""回歸測試：五條管線 workflow 的 `freshness` job 必須 needs: ingest + if: always()。

背景（2026-09-03）：`freshness` job 原本刻意不設 `needs:`，讓它跟 `ingest` job
平行起跑——理由是涵蓋「ingest 掛掉時 freshness 仍要跑」。但平行起跑同時製造了
一個競態：`freshness` 可能讀到 `ingest` 這次執行**還沒寫完**的資料庫。CrUX
（週頻、ingest 要跑 15~20s）實測撞到：run 33710475866 的 freshness 在 ingest
把 2026-08-24 那週寫完之前就讀了資料庫，把這次 run 自己正在寫的那一週誤判成
gap FAIL——CrUX 幾乎每次成功執行都會中，等於一個永遠在叫的告警。

修法是 `needs: ingest` **搭配** `if: always()`：needs 保證 freshness 一定在
ingest 這次執行有結果之後才跑（不管結果是成功還是失敗），消掉競態；
if: always() 保證 ingest 失敗時 freshness 依然會跑，不會複製
「新鮮度告警住在它要監控的作業裡，看不到自己缺席」的病灶（S2.2 事故，
gsc-url-inspection.yml 的既有註解也提過同一個教訓）。「workflow 整個沒被
觸發」的涵蓋範圍現在由獨立排程的 data-quality-watchdog.yml 負責，
不依賴 needs。

本檔用純文字解析（不引入 pyyaml 依賴——這幾支 workflow 目前不在任何 CI 的
pytest 執行路徑上，requirements.txt 也沒有 pyyaml，不必為一支 meta 測試
新增依賴），只驗證 `freshness:` job 區塊內同時出現 `needs: ingest` 與
`always()`——這是這次修法唯一在意的兩個 token，不需要完整解析 YAML 結構。
"""
from __future__ import annotations

from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parent.parent
WORKFLOWS_DIR = ROOT_DIR / ".github" / "workflows"

# 五條有 ingest + freshness 兩個 job 的管線 workflow。
# etl-and-deploy.yml / deploy-ts-api.yml / deploy-docs.yml 不在此列——
# 那些是別的形狀（單一管線內部 needs 串接一整條 pipeline），不适用本測試。
PIPELINE_WORKFLOWS = [
    "cwv-crux-history.yml",
    "cwv-hourly.yml",
    "crawl-hourly.yml",
    "gsc-search-analytics.yml",
    "gsc-url-inspection.yml",
]


def _freshness_job_header(workflow_text: str) -> dict[str, str]:
    """抓出 `  freshness:` job 自己的 `needs:` / `if:`（4 空白縮排，job-level key）。

    刻意不抓整個 job 區塊：freshness job 裡另外還有一個 step 級的
    `if: always()`（「Check for stale running ingestion_run rows (global)」，
    8 空白縮排，跟本次修法無關、修法之前就存在），區塊級的字串搜尋會被它
    混淆而誤判「本來就有 always()」。只認 job 自己那一層（4 空白）的
    `needs:`／`if:` 才不會誤判。
    """
    lines = workflow_text.splitlines()
    start = None
    for i, line in enumerate(lines):
        if line == "  freshness:":
            start = i
            break
    assert start is not None, "找不到 `  freshness:` job（縮排必須是兩個空白）"

    result: dict[str, str] = {}
    for line in lines[start + 1:]:
        if line.startswith("    ") and not line.startswith("     "):
            # job-level key（4 空白，第 5 個字元不是空白）
            key, _, value = line.strip().partition(":")
            if key in ("needs", "if"):
                result[key] = value.strip()
        elif line == "    steps:" or (line and not line.startswith(" ")):
            break  # 進入 steps: 區塊或碰到下一個 top-level key，job-level 欄位列完了
    return result


@pytest.mark.parametrize("workflow_name", PIPELINE_WORKFLOWS)
def test_freshness_job_needs_ingest(workflow_name: str) -> None:
    header = _freshness_job_header((WORKFLOWS_DIR / workflow_name).read_text())
    assert header.get("needs") == "ingest", (
        f"{workflow_name} 的 freshness job 缺少 `needs: ingest`（實際："
        f"{header.get('needs')!r}）——沒有它，freshness 可能在 ingest 這次"
        "執行寫完之前就讀資料庫，把正在寫入的資料誤判成 gap FAIL"
        "（見本檔頂端 CrUX 實例）。"
    )


@pytest.mark.parametrize("workflow_name", PIPELINE_WORKFLOWS)
def test_freshness_job_runs_even_if_ingest_fails(workflow_name: str) -> None:
    header = _freshness_job_header((WORKFLOWS_DIR / workflow_name).read_text())
    assert "always()" in header.get("if", ""), (
        f"{workflow_name} 的 freshness job 加了 needs 卻沒有 job 級的 "
        f"`if: always()`（實際：{header.get('if')!r}）——ingest 失敗時這個 "
        "job 會被 GitHub Actions 預設跳過，複製『新鮮度告警住在它要監控的"
        "作業裡，看不到自己缺席』的病灶（S2.2）。"
    )


@pytest.mark.parametrize("workflow_name", PIPELINE_WORKFLOWS)
def test_freshness_job_still_gated_to_schedule_or_dispatch(workflow_name: str) -> None:
    """加 always() 不能連原本的事件類型篩選都繞過去。"""
    header = _freshness_job_header((WORKFLOWS_DIR / workflow_name).read_text())
    condition = header.get("if", "")
    assert "github.event_name == 'schedule'" in condition
    assert "github.event_name == 'workflow_dispatch'" in condition
