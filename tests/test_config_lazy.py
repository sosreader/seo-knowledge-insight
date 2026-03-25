"""
tests/test_config_lazy.py — config.py lazy loading 測試

驗證 PEP 562 lazy env var 存取行為：
- 未設定必需 env var → ValueError
- 有預設值的 env var → 回傳預設值
- 數值型 env var helper 的邊界條件
"""
from __future__ import annotations

import importlib
import os

import pytest


class TestLazyEnvAccess:
    """PEP 562 __getattr__ for lazy env vars"""

    def test_missing_required_env_raises_value_error(self, monkeypatch):
        """未設定 NOTION_TOKEN 時存取應拋出 ValueError"""
        monkeypatch.delenv("NOTION_TOKEN", raising=False)
        # 重新載入 config 以重設 _LazyEnv 內部狀態
        import config

        config._LAZY_ATTRS["NOTION_TOKEN"]._resolved = False
        with pytest.raises(ValueError, match="NOTION_TOKEN"):
            _ = config.NOTION_TOKEN

    def test_default_env_returns_default(self, monkeypatch):
        """OPENAI_MODEL 有預設值 → 即使未設定也回傳預設"""
        monkeypatch.delenv("OPENAI_MODEL", raising=False)
        import config

        config._LAZY_ATTRS["OPENAI_MODEL"]._resolved = False
        assert config.OPENAI_MODEL == "gpt-5.4-nano"

    def test_set_env_returns_value(self, monkeypatch):
        """已設定的 env var 應回傳設定值"""
        monkeypatch.setenv("NOTION_TOKEN", "test-token-123")
        import config

        config._LAZY_ATTRS["NOTION_TOKEN"]._resolved = False
        assert config.NOTION_TOKEN == "test-token-123"

    def test_whitespace_only_required_raises(self, monkeypatch):
        """只有空白的必需 env var 應拋出 ValueError"""
        monkeypatch.setenv("OPENAI_API_KEY", "   ")
        import config

        config._LAZY_ATTRS["OPENAI_API_KEY"]._resolved = False
        with pytest.raises(ValueError, match="OPENAI_API_KEY"):
            _ = config.OPENAI_API_KEY

    def test_whitespace_only_optional_returns_empty(self, monkeypatch):
        """只有空白的可選 env var（有 default）應回傳空字串"""
        monkeypatch.setenv("SHEETS_URL", "   ")
        import config

        config._LAZY_ATTRS["SHEETS_URL"]._resolved = False
        # default="" 表示非必需，空白 strip 後為 ""
        assert config.SHEETS_URL == ""

    def test_nonexistent_attr_raises_attribute_error(self):
        """存取不存在的 attr 應拋出 AttributeError"""
        import config

        with pytest.raises(AttributeError, match="NO_SUCH_ATTR"):
            _ = config.NO_SUCH_ATTR

    def test_dir_includes_lazy_attrs(self):
        """dir(config) 應包含所有 lazy attrs"""
        import config

        attrs = dir(config)
        for key in ("NOTION_TOKEN", "OPENAI_API_KEY", "OPENAI_MODEL"):
            assert key in attrs


class TestFloatEnvHelper:
    """_get_float_env 邊界條件"""

    def test_valid_float(self, monkeypatch):
        monkeypatch.setenv("KW_BOOST", "0.15")
        import config

        result = config._get_float_env("KW_BOOST", "0.10")
        assert result == 0.15

    def test_invalid_float_raises(self, monkeypatch):
        monkeypatch.setenv("KW_BOOST", "abc")
        import config

        with pytest.raises(ValueError, match="必須是數字"):
            config._get_float_env("KW_BOOST", "0.10")

    def test_negative_float_raises(self, monkeypatch):
        monkeypatch.setenv("KW_BOOST", "-0.5")
        import config

        with pytest.raises(ValueError, match="非負有限數字"):
            config._get_float_env("KW_BOOST", "0.10")

    def test_infinity_raises(self, monkeypatch):
        monkeypatch.setenv("KW_BOOST", "inf")
        import config

        with pytest.raises(ValueError, match="非負有限數字"):
            config._get_float_env("KW_BOOST", "0.10")


class TestIntEnvHelper:
    """_get_int_env 邊界條件"""

    def test_valid_int(self, monkeypatch):
        monkeypatch.setenv("KW_BOOST_MAX_HITS", "5")
        import config

        result = config._get_int_env("KW_BOOST_MAX_HITS", "3")
        assert result == 5

    def test_invalid_int_raises(self, monkeypatch):
        monkeypatch.setenv("KW_BOOST_MAX_HITS", "3.5")
        import config

        with pytest.raises(ValueError, match="必須是整數"):
            config._get_int_env("KW_BOOST_MAX_HITS", "3")

    def test_below_min_raises(self, monkeypatch):
        monkeypatch.setenv("KW_BOOST_MAX_HITS", "0")
        import config

        with pytest.raises(ValueError, match=">= 1"):
            config._get_int_env("KW_BOOST_MAX_HITS", "3")
