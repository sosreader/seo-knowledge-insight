"""回歸測試：六條管線 workflow 的資料品質 gate 必須「在 ingest 之後、且 ingest
失敗時照樣跑」。

背景（2026-09-03）：`freshness` job 原本刻意不設 `needs:`，讓它跟 `ingest` job
平行起跑——理由是涵蓋「ingest 掛掉時 freshness 仍要跑」。但平行起跑同時製造了
一個競態：`freshness` 可能讀到 `ingest` 這次執行**還沒寫完**的資料庫。CrUX
（週頻、ingest 要跑 15~20s）實測撞到：run 33710475866 的 freshness 在 ingest
把 2026-08-24 那週寫完之前就讀了資料庫，把這次 run 自己正在寫的那一週誤判成
gap FAIL——CrUX 幾乎每次成功執行都會中，等於一個永遠在叫的告警。
當時的修法是 `needs: ingest` **搭配** `if: always()`。

2026-09-10：GitHub Actions 逐 job 計費、每個 job 各自無條件進位到整分鐘，
而這條 gate 的 job 中位數只有 8~22 秒（實測 2026-09-02..09-08）。四條非 matrix
管線把 gate 併成 `ingest` job 尾端的 step，兩個不變量改由「step 順序」與
「step 級 if: always()」承擔，語意等價：
  needs: ingest       → 同 job 的後續 step（順序天然保證，競態一樣被消掉）
  job 級 if: always() → step 級 if: always()（ingest 步驟失敗時照樣跑）

本檔因此分成兩組：
  MERGED_WORKFLOWS   —— gate 已併成 ingest job 的 step，驗 step 級不變量
  SPLIT_WORKFLOWS    —— gate 仍是獨立 job，驗原本的 job 級不變量

兩組加起來仍是原本那六支，沒有任何一支從測試涵蓋範圍裡消失。

本檔用純文字解析（不引入 pyyaml 依賴——requirements.txt 沒有 pyyaml，不必為
一支 meta 測試新增依賴）。
"""
from __future__ import annotations

from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parent.parent
WORKFLOWS_DIR = ROOT_DIR / ".github" / "workflows"

# 資料品質 gate 已併入 ingest job 的管線（2026-09-10）。
MERGED_WORKFLOWS = [
    "cwv-crux-history.yml",
    "cwv-hourly.yml",
    "crawl-hourly.yml",
    "gsc-url-inspection.yml",
]

# 仍保留獨立 freshness job 的管線，各有不可併的理由：
#
#   gsc-search-analytics.yml —— ingest 是 matrix（六個 surface，max-parallel: 1），
#     freshness 是跨六條腿的 fan-in。併進 ingest 會變成每個 surface 各跑一次
#     gate，而且失去「等六個都寫完再檢查」的語意。
#
#   ai-sov-weekly.yml —— ingest 有 `timeout-minutes: 60`（36 prompt x 3 次帶
#     web_search，刻意壓上限），job 級 timeout 觸發時 job 被取消，併進去的 step
#     不保證會跑；而且這支自 2026-09-05 起 schedule 已註解掉、只剩
#     workflow_dispatch，併了也省不到任何排程計費分鐘。
SPLIT_WORKFLOWS = [
    "gsc-search-analytics.yml",
    "ai-sov-weekly.yml",
]

EVENT_GATE_TOKENS = (
    "github.event_name == 'schedule'",
    "github.event_name == 'workflow_dispatch'",
)


def _job_names(workflow_text: str) -> list[str]:
    """所有 job 名稱（2 空白縮排、位於 `jobs:` 之後的 key）。"""
    lines = workflow_text.splitlines()
    start = lines.index("jobs:")
    names = []
    for line in lines[start + 1:]:
        if line and not line.startswith(" "):
            break
        if line.startswith("  ") and not line.startswith("   ") and line.rstrip().endswith(":"):
            names.append(line.strip().rstrip(":"))
    return names


def _ingest_steps(workflow_text: str) -> list[dict[str, str]]:
    """抓 `  ingest:` job 的 steps，每個 step 回 {name, if, run}。

    只認 6 空白的 `- name:`／8 空白的 `if:`／8 空白的 `run:`——不進 steps 內層
    的 `env:` 或 run 區塊，避免把 run script 裡的字串誤當成 job 結構。
    """
    lines = workflow_text.splitlines()
    start = lines.index("  ingest:")
    steps: list[dict[str, str]] = []
    in_steps = False
    for line in lines[start + 1:]:
        if line.startswith("  ") and not line.startswith("   ") and line.rstrip().endswith(":"):
            break  # 下一個 job
        if line == "    steps:":
            in_steps = True
            continue
        if not in_steps:
            continue
        if line.startswith("      - name:"):
            steps.append({"name": line.split(":", 1)[1].strip(), "if": "", "run": ""})
        elif steps and line.startswith("        ") and not line.startswith("         "):
            key, _, value = line.strip().partition(":")
            if key in ("if", "run"):
                steps[-1][key] = value.strip()
        elif steps and line.startswith("          ") and steps[-1]["run"] in ("", "|"):
            steps[-1]["run"] += " " + line.strip()
    return steps


def _freshness_job_header(workflow_text: str) -> dict[str, str]:
    """抓出 `  freshness:` job 自己的 `needs:` / `if:`（4 空白縮排，job-level key）。

    刻意不抓整個 job 區塊：freshness job 裡另外還有一個 step 級的
    `if: always()`（「Check for stale running ingestion_run rows (global)」，
    8 空白縮排），區塊級的字串搜尋會被它混淆而誤判「本來就有 always()」。
    """
    lines = workflow_text.splitlines()
    start = lines.index("  freshness:")
    result: dict[str, str] = {}
    for line in lines[start + 1:]:
        if line.startswith("    ") and not line.startswith("     "):
            key, _, value = line.strip().partition(":")
            if key in ("needs", "if"):
                result[key] = value.strip()
        elif line == "    steps:" or (line and not line.startswith(" ")):
            break
    return result


def _gate_steps(workflow_text: str) -> list[dict[str, str]]:
    return [s for s in _ingest_steps(workflow_text) if "data_quality_gate.py" in s["run"]]


# ── 併入型：gate 是 ingest job 的 step ────────────────────────────────────────


@pytest.mark.parametrize("workflow_name", MERGED_WORKFLOWS)
def test_merged_workflow_has_no_separate_freshness_job(workflow_name: str) -> None:
    names = _job_names((WORKFLOWS_DIR / workflow_name).read_text())
    assert "freshness" not in names, (
        f"{workflow_name} 同時留著獨立的 freshness job 與併入的 step——"
        "gate 會跑兩次，而且逐 job 計費的整分鐘又被收回去了。"
    )
    assert names == ["ingest"], f"{workflow_name} 預期只剩 ingest 一個 job，實際 {names}"


@pytest.mark.parametrize("workflow_name", MERGED_WORKFLOWS)
def test_merged_gate_steps_run_after_the_write(workflow_name: str) -> None:
    """gate 必須排在寫入 step 之後——這是 needs: ingest 原本買到的東西。"""
    steps = _ingest_steps((WORKFLOWS_DIR / workflow_name).read_text())
    gate_indexes = [i for i, s in enumerate(steps) if "data_quality_gate.py" in s["run"]]
    write_indexes = [
        i for i, s in enumerate(steps)
        if "--execute" in s["run"] or "--verify" in s["run"]
    ]
    assert gate_indexes, f"{workflow_name} 的 ingest job 裡找不到 data_quality_gate.py step"
    assert write_indexes, f"{workflow_name} 的 ingest job 裡找不到寫入／驗證 step"
    assert min(gate_indexes) > max(write_indexes), (
        f"{workflow_name} 的資料品質 gate 排在寫入之前——會讀到 ingest 這次執行"
        "還沒寫完的資料庫，把自己正在寫的那一段誤判成 gap FAIL（見本檔頂端 CrUX 實例）。"
    )


@pytest.mark.parametrize("workflow_name", MERGED_WORKFLOWS)
def test_merged_gate_steps_run_even_if_ingest_fails(workflow_name: str) -> None:
    for step in _gate_steps((WORKFLOWS_DIR / workflow_name).read_text()):
        assert "always()" in step["if"], (
            f"{workflow_name} 的 gate step {step['name']!r} 沒有 `if: always()`"
            f"（實際：{step['if']!r}）——前面的 ingest step 失敗時它會被跳過，"
            "複製『新鮮度告警住在它要監控的作業裡，看不到自己缺席』的病灶（S2.2）。"
        )


@pytest.mark.parametrize("workflow_name", MERGED_WORKFLOWS)
def test_merged_gate_steps_still_gated_to_schedule_or_dispatch(workflow_name: str) -> None:
    """加 always() 不能連原本的事件類型篩選都繞過去。"""
    for step in _gate_steps((WORKFLOWS_DIR / workflow_name).read_text()):
        for token in EVENT_GATE_TOKENS:
            assert token in step["if"], (
                f"{workflow_name} 的 gate step {step['name']!r} 掉了事件篩選 {token}"
                f"（實際：{step['if']!r}）"
            )


# ── 拆分型：gate 仍是獨立 job ─────────────────────────────────────────────────


@pytest.mark.parametrize("workflow_name", SPLIT_WORKFLOWS)
def test_freshness_job_needs_ingest(workflow_name: str) -> None:
    header = _freshness_job_header((WORKFLOWS_DIR / workflow_name).read_text())
    assert header.get("needs") == "ingest", (
        f"{workflow_name} 的 freshness job 缺少 `needs: ingest`（實際："
        f"{header.get('needs')!r}）——沒有它，freshness 可能在 ingest 這次"
        "執行寫完之前就讀資料庫，把正在寫入的資料誤判成 gap FAIL"
        "（見本檔頂端 CrUX 實例）。"
    )


@pytest.mark.parametrize("workflow_name", SPLIT_WORKFLOWS)
def test_freshness_job_runs_even_if_ingest_fails(workflow_name: str) -> None:
    header = _freshness_job_header((WORKFLOWS_DIR / workflow_name).read_text())
    assert "always()" in header.get("if", ""), (
        f"{workflow_name} 的 freshness job 加了 needs 卻沒有 job 級的 "
        f"`if: always()`（實際：{header.get('if')!r}）——ingest 失敗時這個 "
        "job 會被 GitHub Actions 預設跳過，複製『新鮮度告警住在它要監控的"
        "作業裡，看不到自己缺席』的病灶（S2.2 事故）。"
    )


@pytest.mark.parametrize("workflow_name", SPLIT_WORKFLOWS)
def test_freshness_job_still_gated_to_schedule_or_dispatch(workflow_name: str) -> None:
    header = _freshness_job_header((WORKFLOWS_DIR / workflow_name).read_text())
    condition = header.get("if", "")
    for token in EVENT_GATE_TOKENS:
        assert token in condition


def test_split_workflows_have_a_documented_reason_not_to_merge() -> None:
    """兩支例外各自的理由必須是結構性的、可從 workflow 本身驗證的。

    不是靠註解自述——matrix 與 job 級 timeout 都直接讀得出來。
    """
    gsc = (WORKFLOWS_DIR / "gsc-search-analytics.yml").read_text()
    assert "    strategy:" in gsc and "      matrix:" in gsc, (
        "gsc-search-analytics 的 ingest 不再是 matrix 了——不可併的理由消失，"
        "應該重新評估是否搬進 MERGED_WORKFLOWS。"
    )
    sov = (WORKFLOWS_DIR / "ai-sov-weekly.yml").read_text()
    assert "    timeout-minutes:" in sov, (
        "ai-sov-weekly 的 ingest 不再有 job 級 timeout——不可併的理由之一消失，"
        "應該重新評估。"
    )
