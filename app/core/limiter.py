"""
Rate Limiter 單例 — Phase B

獨立模組避免 app.main ← routers 循環相依。
"""
from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
