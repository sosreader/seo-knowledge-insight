"""_is_evergreen / _classify_qa_locally 的時效性判定

原本 _TIME_SENSITIVE_MARKERS 逐年列舉 "2023"-"2026"，2027 起新年份
不再命中而被誤判 evergreen；改用 20\\d{2} 正則後任何 20xx 年份皆命中。
"""
import pytest

from utils.openai_helper import _classify_qa_locally, _is_evergreen


@pytest.mark.parametrize("year", ["2023", "2024", "2025", "2026", "2027", "2031", "2099"])
def test_any_20xx_year_is_time_sensitive(year):
    assert _is_evergreen(f"google 在 {year} 年的搜尋趨勢") is False


@pytest.mark.parametrize("marker", ["核心更新", "ai overview", "trend", "統計"])
def test_existing_markers_unchanged(marker):
    assert _is_evergreen(f"這段內容提到 {marker} 相關主題") is False


def test_plain_content_is_evergreen():
    assert _is_evergreen("title 標籤應該描述頁面主要內容") is True


def test_classify_qa_locally_flags_future_year_not_evergreen():
    result = _classify_qa_locally("2027 年的演算法變化？", "屆時再觀察。")
    assert result["evergreen"] is False


def test_classify_qa_locally_evergreen_passthrough():
    result = _classify_qa_locally("什麼是 title 標籤？", "HTML 的頁面標題元素。")
    assert result["evergreen"] is True
