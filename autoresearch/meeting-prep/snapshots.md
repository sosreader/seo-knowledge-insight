# Meeting-Prep Autoresearch — 輸入 Fixture Registry

autoresearch loop 用 `--report` 模式讀取已存在的 golden fixture（跳過 web research），確保確定性。

## 可用 Fixtures

| # | Fixture ID | Fixture Path | ALERT_DOWN 數 | Baseline Composite | 狀態 |
|---|-----------|-------------|---------------|-------------------|------|
| 0 | 20260220_25caf520 | `eval/fixtures/meeting_prep/meeting_prep_20260220_25caf520.md` | 6 | 0.8738 | ✓ Valid |
| 1 | 20260227_765384ce | `eval/fixtures/meeting_prep/meeting_prep_20260227_765384ce.md` | 16 | 0.8397 | ✓ Valid |
| 2 | 20260306_ea576a4f | `eval/fixtures/meeting_prep/meeting_prep_20260306_ea576a4f.md` | 9 | 0.8095 | ✓ Valid |
| 3 | 20260309_49530993 | `eval/fixtures/meeting_prep/meeting_prep_20260309_49530993.md` | 9 | 0.7989 | ✓ Valid |

**Valid count: 4**

**Rotation**: `round_number % 4` → cycles through fixtures 0-3.

## 排除

| ID | Path | 原因 |
|----|------|------|
| calibration_anchor_low | `eval/fixtures/meeting_prep/calibration_anchor_low.md` | 校準用低品質樣本，不可用於 autoresearch eval |
