"""
freshness — Q&A 時效性衰減計算

指數衰減公式：score = exp(-0.693 * age_days / half_life_days)
  - evergreen=True → 1.0（永不衰減）
  - 0 天舊 → 1.0
  - 等於 half_life_days 舊 → 0.5
  - min_score 保底（防止過舊資料完全被排除）

學術依據：
  Dong et al. "Towards Recency Ranking in Web Search" (WWW 2010)
  Manning et al. "Introduction to IR" Ch.6 temporal factors

SEO 場景說明：
  Google 演算法年更，2023 年的建議在 2026 年可能有害（如 AMP 策略）。
  使用 18 個月（540 天）半衰期，超過此時間的非 evergreen 建議分數降至 0.5。
"""
from __future__ import annotations

import math
from datetime import date


def compute_freshness_score(
    source_date: str,
    is_evergreen: bool,
    half_life_days: float = 540.0,
    min_score: float = 0.5,
) -> float:
    """
    計算 Q&A 的時效性分數（0.0 ~ 1.0）。

    Args:
        source_date:    Q&A 來源日期（ISO 格式 "YYYY-MM-DD"）
        is_evergreen:   是否為常青內容（True → 永遠回傳 1.0）
        half_life_days: 半衰期天數（預設 540 天 ≈ 18 個月）
        min_score:      最低分數保底（預設 0.5）

    Returns:
        時效性分數（float，範圍 [min_score, 1.0]）
    """
    if is_evergreen:
        return 1.0

    try:
        d = date.fromisoformat(source_date)
    except (ValueError, TypeError):
        return 1.0

    age_days = (date.today() - d).days
    if age_days <= 0:
        return 1.0

    decay = math.exp(-0.693 * age_days / half_life_days)
    return max(min_score, round(decay, 4))
