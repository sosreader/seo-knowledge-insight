#!/usr/bin/env python3
"""臨時評估腳本：評估新萃取的 3 份 Q&A 的 Completeness"""
import sys
sys.path.insert(0, str(__import__('pathlib').Path(__file__).parent.parent))

import json
import time
import importlib.util
from pathlib import Path

# 動態載入 05_evaluate.py
spec = importlib.util.spec_from_file_location(
    "evaluate",
    Path(__file__).parent / "05_evaluate.py"
)
ev = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ev)

new_files = [
    # 2024 早中晚末 + 2026（新增驗證批次）
    "output/qa_per_meeting/SEO_會議_2024_01_03_qa.json",
    "output/qa_per_meeting/SEO_會議_2024_06_13_qa.json",
    "output/qa_per_meeting/SEO_會議_2024_09_09_qa.json",
    "output/qa_per_meeting/SEO_會議_2024_12_09_qa.json",
    "output/qa_per_meeting/SEO_會議_20260112_qa.json",
    "output/qa_per_meeting/SEO_會議_20260209_qa.json",
    "output/qa_per_meeting/SEO_會議_20260223_qa.json",
]

all_qa = []
for f in new_files:
    p = Path(f)
    data = json.loads(p.read_text(encoding="utf-8"))
    qa_list = data.get("qa_pairs", [])
    for qa in qa_list:
        qa["_source_file"] = p.name
    all_qa.extend(qa_list)

print(f"共 {len(all_qa)} 筆新 Q&A")
results = []
for i, qa in enumerate(all_qa, 1):
    print(f"  [{i}/{len(all_qa)}] {qa['question'][:55]}...")
    r = ev.evaluate_qa_quality(qa)
    results.append(r)
    time.sleep(0.5)

dims = ["relevance", "accuracy", "completeness", "granularity"]
print()
print("=== 新 Q&A 評估結果（新 prompt） ===")
for d in dims:
    scores = [r[d]["score"] for r in results if d in r and "score" in r.get(d, {})]
    if scores:
        avg = sum(scores) / len(scores)
        print(f"  {d}: {avg:.2f}  (n={len(scores)})")
        if d == "completeness":
            if avg >= 4.0:
                print(f"  ✅ Completeness {avg:.2f} ≥ 4.0，通過驗證！")
            else:
                print(f"  ❌ Completeness {avg:.2f} < 4.0，未通過")

# 印出每個 Q&A 的 Completeness 明細
print()
print("=== Completeness 明細 ===")
for i, (qa, r) in enumerate(zip(all_qa, results), 1):
    c = r.get("completeness", {})
    score = c.get("score", "?")
    reason = c.get("reason", "")[:60]
    print(f"  [{i}] {score} — {qa['question'][:45]}...")
    print(f"       {reason}")
