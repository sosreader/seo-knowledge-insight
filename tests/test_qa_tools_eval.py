"""tests/test_qa_tools_eval.py — qa_tools.py eval-sample / eval-retrieval-local / eval-save 測試"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
QA_TOOLS = PROJECT_ROOT / "scripts" / "qa_tools.py"
PYTHON = PROJECT_ROOT / ".venv" / "bin" / "python"

# 直接 import 被測函式
sys.path.insert(0, str(PROJECT_ROOT))
from scripts.qa_tools import (
    _kw_fuzzy_hit,
    _keyword_search,
    _validate_eval_result,
)


# ──────────────────────────────────────────────────────
# _kw_fuzzy_hit
# ──────────────────────────────────────────────────────

class TestKwFuzzyHit:
    """子字串雙向匹配邊界情況。"""

    def test_exact_match(self):
        assert _kw_fuzzy_hit("Discover", {"discover", "amp"}) is True

    def test_substring_expected_in_retrieved(self):
        """'流量' in '探索流量' → True"""
        assert _kw_fuzzy_hit("流量", {"探索流量", "seo"}) is True

    def test_substring_retrieved_in_expected(self):
        """'探索' in '探索流量'（retrieved rkw='探索' in kw='探索流量'）→ True"""
        assert _kw_fuzzy_hit("探索流量", {"探索", "seo"}) is True

    def test_no_match(self):
        assert _kw_fuzzy_hit("canonical", {"amp", "discover"}) is False

    def test_single_char_rkw_not_match(self):
        """單字元 rkw（長度 < 2）不應以 'rkw in kw' 方向匹配。"""
        assert _kw_fuzzy_hit("索引", {"索"}) is False

    def test_empty_retrieved_kws(self):
        assert _kw_fuzzy_hit("AMP", set()) is False

    def test_case_insensitive(self):
        assert _kw_fuzzy_hit("AMP", {"amp", "discover"}) is True


# ──────────────────────────────────────────────────────
# _keyword_search
# ──────────────────────────────────────────────────────

class TestKeywordSearch:
    """關鍵字搜尋邏輯。"""

    @pytest.fixture()
    def sample_qas(self):
        return [
            {"question": "AMP 的好處", "answer": "加速", "keywords": ["AMP", "速度"]},
            {"question": "canonical 設定", "answer": "指向正確", "keywords": ["canonical", "索引"]},
            {"question": "Discover 流量", "answer": "流量增加", "keywords": ["Discover", "流量"]},
        ]

    def test_returns_sorted_by_score(self, sample_qas):
        results = _keyword_search("AMP 速度", sample_qas, top_k=3)
        assert len(results) >= 1
        # AMP 命中 keyword(×3) + question(×2)，應排第一
        assert "AMP" in results[0][0]["question"]

    def test_top_k_limits(self, sample_qas):
        results = _keyword_search("AMP canonical Discover", sample_qas, top_k=2)
        assert len(results) <= 2

    def test_no_match_returns_empty(self, sample_qas):
        results = _keyword_search("xyz不存在", sample_qas, top_k=5)
        assert results == []


# ──────────────────────────────────────────────────────
# eval-sample（CLI 整合測試）
# ──────────────────────────────────────────────────────

class TestEvalSampleCLI:
    """eval-sample 子命令整合測試。"""

    def test_size_and_seed_consistency(self):
        """固定 seed 應產出相同抽樣。"""
        result1 = subprocess.run(
            [str(PYTHON), str(QA_TOOLS), "eval-sample", "--size", "5", "--seed", "123"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT),
        )
        result2 = subprocess.run(
            [str(PYTHON), str(QA_TOOLS), "eval-sample", "--size", "5", "--seed", "123"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT),
        )
        assert result1.returncode == 0
        assert result2.returncode == 0

        data1 = json.loads(result1.stdout)
        data2 = json.loads(result2.stdout)
        ids1 = [i["stable_id"] for i in data1["items"]]
        ids2 = [i["stable_id"] for i in data2["items"]]
        assert ids1 == ids2

    def test_json_structure(self):
        """輸出 JSON 欄位完整性。"""
        result = subprocess.run(
            [str(PYTHON), str(QA_TOOLS), "eval-sample", "--size", "3", "--seed", "42"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT),
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["sample_size"] == 3
        assert data["seed"] == 42
        assert "items" in data
        item = data["items"][0]
        for key in ["stable_id", "question", "answer", "keywords", "category"]:
            assert key in item, f"Missing key: {key}"

    def test_different_seed_different_sample(self):
        """不同 seed 應產出不同抽樣。"""
        r1 = subprocess.run(
            [str(PYTHON), str(QA_TOOLS), "eval-sample", "--size", "10", "--seed", "1"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT),
        )
        r2 = subprocess.run(
            [str(PYTHON), str(QA_TOOLS), "eval-sample", "--size", "10", "--seed", "999"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT),
        )
        ids1 = [i["stable_id"] for i in json.loads(r1.stdout)["items"]]
        ids2 = [i["stable_id"] for i in json.loads(r2.stdout)["items"]]
        assert ids1 != ids2


# ──────────────────────────────────────────────────────
# eval-retrieval-local（CLI 整合測試）
# ──────────────────────────────────────────────────────

class TestEvalRetrievalLocalCLI:
    """eval-retrieval-local 子命令整合測試。"""

    def test_metrics_output(self):
        """確認輸出包含 KW Hit Rate / MRR / Cat Hit Rate。"""
        result = subprocess.run(
            [str(PYTHON), str(QA_TOOLS), "eval-retrieval-local", "--top-k", "3"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT),
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "avg_keyword_hit_rate" in data
        assert "avg_mrr" in data
        assert "avg_category_hit_rate" in data
        assert data["search_engine"] == "keyword"
        golden = json.loads((PROJECT_ROOT / "eval" / "golden_retrieval.json").read_text())
        assert data["total_cases"] == len(golden)

    def test_case_details_structure(self):
        """每個 case 都有 top1_question / top1_answer。"""
        result = subprocess.run(
            [str(PYTHON), str(QA_TOOLS), "eval-retrieval-local"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT),
        )
        data = json.loads(result.stdout)
        for case in data["case_details"]:
            assert "top1_question" in case
            assert "top1_answer" in case
            assert "keyword_hit_rate" in case
            assert "mrr" in case


# ──────────────────────────────────────────────────────
# _validate_eval_result
# ──────────────────────────────────────────────────────

class TestValidateEvalResult:
    """eval-save 的 JSON 結構驗證。"""

    @pytest.fixture()
    def valid_data(self):
        return {
            "generation": {"relevance": 4.5, "accuracy": 4.0, "completeness": 3.9, "granularity": 4.6},
            "retrieval": {"kw_hit_rate": 0.78, "mrr": 0.75},
            "classification": {"category_accuracy": 0.68},
        }

    def test_valid_passes(self, valid_data):
        assert _validate_eval_result(valid_data) == []

    def test_missing_section(self, valid_data):
        del valid_data["retrieval"]
        errors = _validate_eval_result(valid_data)
        assert any("retrieval" in e for e in errors)

    def test_missing_generation_dim(self, valid_data):
        del valid_data["generation"]["accuracy"]
        errors = _validate_eval_result(valid_data)
        assert any("accuracy" in e for e in errors)

    def test_generation_score_out_of_range(self, valid_data):
        invalid = {**valid_data, "generation": {**valid_data["generation"], "relevance": 6}}
        errors = _validate_eval_result(invalid)
        assert any("relevance" in e for e in errors)

    def test_missing_retrieval_key(self, valid_data):
        invalid = {**valid_data, "retrieval": {"kw_hit_rate": 0.5}}
        errors = _validate_eval_result(invalid)
        assert any("mrr" in e for e in errors)

    def test_missing_classification_key(self, valid_data):
        invalid = {**valid_data, "classification": {}}
        errors = _validate_eval_result(invalid)
        assert any("category_accuracy" in e for e in errors)


# ──────────────────────────────────────────────────────
# eval-save（CLI 整合測試）
# ──────────────────────────────────────────────────────

class TestEvalSaveCLI:
    """eval-save 子命令整合測試。"""

    @pytest.fixture(autouse=True)
    def _cleanup_eval_files(self):
        yield
        for f in (PROJECT_ROOT / "output" / "evals").glob("*_claude-code_claude-code.json"):
            f.unlink(missing_ok=True)

    def test_versioned_filename(self, tmp_path):
        """儲存的檔名格式：{date}_claude-code_{engine}.json"""
        input_data = {
            "generation": {"relevance": 4.5, "accuracy": 4.0, "completeness": 3.9, "granularity": 4.6},
            "retrieval": {"kw_hit_rate": 0.61, "mrr": 0.88},
            "classification": {"category_accuracy": 0.70},
        }
        input_file = tmp_path / "test_input.json"
        input_file.write_text(json.dumps(input_data), encoding="utf-8")

        result = subprocess.run(
            [str(PYTHON), str(QA_TOOLS), "eval-save", "--input", str(input_file)],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT),
        )
        assert result.returncode == 0
        assert "已儲存" in result.stdout

        # 確認有產出檔案
        evals_dir = PROJECT_ROOT / "output" / "evals"
        saved = list(evals_dir.glob("*_claude-code_claude-code.json"))
        assert len(saved) >= 1

        # 讀取確認 provider
        saved_data = json.loads(saved[-1].read_text(encoding="utf-8"))
        assert saved_data["provider"] == "claude-code"

    def test_baseline_comparison_output(self, tmp_path):
        """有基準線時應顯示比較。"""
        input_data = {
            "generation": {"relevance": 4.8, "accuracy": 4.0, "completeness": 3.9, "granularity": 4.7},
            "retrieval": {"kw_hit_rate": 0.78, "mrr": 0.75},
            "classification": {"category_accuracy": 0.68},
        }
        input_file = tmp_path / "test_input.json"
        input_file.write_text(json.dumps(input_data), encoding="utf-8")

        result = subprocess.run(
            [str(PYTHON), str(QA_TOOLS), "eval-save", "--input", str(input_file)],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT),
        )
        assert result.returncode == 0
        assert "基準線比較" in result.stdout
