"""產生 freshness 公式的 parity golden（api/tests/jobs/update-freshness.test.ts 讀取 golden.json）。

用 SKI 的 Python 實作（scripts/update_freshness.py）的 compute_freshness_score 與 _compute_updates
在固定參考時間算出預期值，TS 版（src/jobs/freshness.ts）必須逐筆一致。

執行（不需要 requests／python-dotenv：本腳本只取純函式，網路與 dotenv 以 stub 取代）：

    python3 api/tests/fixtures/freshness-parity/generate_golden.py

Python 版刪除（E 階段）之前才能重新產生；之後 golden.json 就是凍結的真源，不要手改。
"""
from __future__ import annotations

import json
import sys
import types
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT))
sys.modules.setdefault("requests", types.ModuleType("requests"))
dotenv_stub = types.ModuleType("dotenv")
dotenv_stub.load_dotenv = lambda *a, **k: False  # type: ignore[attr-defined]
sys.modules.setdefault("dotenv", dotenv_stub)

from scripts.update_freshness import (  # noqa: E402
    HALF_LIFE_DAYS,
    MIN_DIFF,
    _compute_updates,
    compute_freshness_score,
)

REF = datetime(2026, 10, 26, 2, 0, 0, tzinfo=timezone.utc)  # 週一 02:00 UTC，與排程一致


def date_before(days: int) -> str:
    return (REF - timedelta(days=days)).strftime("%Y-%m-%d")


def build_grid() -> list[dict]:
    ages = sorted(
        set(range(-5, 120)) | set(range(120, 4200, 11)) | {539, 540, 541, 1080, 3587, 3588, 3589}
    )
    return [
        {"source_date": date_before(a), "evergreen": False, "score": compute_freshness_score(date_before(a), False, REF)}
        for a in ages
    ]


# (source_date, evergreen, freshness_score)：涵蓋公式分支與「差異 < 0.001 跳過」邊界
CASES: list[tuple[str | None, bool | None, float | None]] = [
    (date_before(0), False, 1.0),            # 今天 → 1.0，跳過
    (date_before(-3), False, 1.0),           # 未來日期 → 1.0
    (date_before(1), False, 1.0),
    (date_before(30), False, 1.0),
    (date_before(100), False, 0.9),
    (date_before(539), False, 1.0),
    (date_before(540), False, 1.0),          # 半衰期 → 約 0.5
    (date_before(541), False, 0.5),
    (date_before(1000), False, 1.0),
    (date_before(3587), False, 1.0),
    (date_before(3588), False, 1.0),         # 接近 0.01 下限
    (date_before(3600), False, 1.0),         # 下限 0.01
    (date_before(9000), False, 0.01),        # 已在下限，跳過
    ("2000-01-01", False, 1.0),
    ("2024-02-29", False, 1.0),              # 閏日
    ("2023-02-29", False, 1.0),              # 不存在的日期 → 1.0
    ("2024-13-45", False, 0.4),              # 無效日期 → 1.0，與舊值差 0.6 要更新
    ("2024-5-1 ab", False, 0.7),             # 前 10 碼非 YYYY-MM-DD → 1.0
    ("abcdefghij", False, 1.0),
    ("2024-05-01T12:00:00Z", False, 1.0),    # 只取前 10 碼
    ("2024-05-01", False, None),             # freshness_score NULL → 視為 1.0
    ("2024-05-01", False, 0.0),              # 舊值 0 被 `or 1.0` 當 1.0（Python 行為）
    ("", False, 0.8),                        # 空日期 → 1.0
    (None, False, 0.8),                      # NULL 日期 → 1.0
    ("2024", False, 0.8),                    # 長度不足 → 1.0
    (None, None, None),                      # 全 NULL
    ("2020-01-01", True, 0.5),               # evergreen 舊值偏離 → 回 1.0
    ("2020-01-01", True, 1.0),               # evergreen 已是 1.0 → 跳過
    ("2020-01-01", True, 0.9995),            # evergreen 差 0.0005 → 跳過
    ("2020-01-01", True, None),              # evergreen 舊值 NULL → 視為 1.0，跳過
    ("2020-01-01", None, 1.0),               # evergreen NULL 視為 false
]


def build_items() -> list[dict]:
    items = []
    for i, (source_date, evergreen, score) in enumerate(CASES, start=1):
        items.append(
            {
                "id": f"{i:016x}",
                "seq": i,
                "source_date": source_date,
                "evergreen": evergreen,
                "freshness_score": score,
            }
        )
    # 差距恰在 MIN_DIFF 附近：先用公式算出 100 天前的新分數，再造出 +0.0005（跳過）與 +0.0015（更新）的舊值
    target = compute_freshness_score(date_before(200), False, REF)
    for offset, label in ((0.0005, "within"), (0.0015, "beyond")):
        n = len(items) + 1
        items.append(
            {
                "id": f"{n:016x}",
                "seq": n,
                "source_date": date_before(200),
                "evergreen": False,
                "freshness_score": round(target + offset, 4),
            }
        )
    return items


def main() -> None:
    items = build_items()
    updates, skipped, evergreen_count = _compute_updates(items, REF)
    expected = {u["id"]: u["score"] for u in updates}
    final = {it["id"]: expected.get(it["id"], it["freshness_score"]) for it in items}
    golden = {
        "reference_time": REF.isoformat().replace("+00:00", "Z"),
        "half_life_days": HALF_LIFE_DAYS,
        "min_diff": MIN_DIFF,
        "grid": build_grid(),
        "items": items,
        "expected_updates": expected,
        "expected_skipped": skipped,
        "expected_evergreen": evergreen_count,
        "expected_final": final,
    }
    out = Path(__file__).with_name("golden.json")
    out.write_text(json.dumps(golden, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {out} items={len(items)} updates={len(updates)} skipped={skipped} evergreen={evergreen_count}")


if __name__ == "__main__":
    main()
