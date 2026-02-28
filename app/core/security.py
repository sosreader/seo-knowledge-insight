"""
API Key 認證 — Phase A

所有 /api/v1/* endpoint 都需要帶 X-API-Key header；
health endpoint 不需要。
"""
from __future__ import annotations

import hmac
import logging
from typing import Optional

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

logger = logging.getLogger(__name__)

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: Optional[str] = Security(_api_key_header)) -> str:
    # lazy import 防止 circular import
    from app import config as app_config

    expected: str = app_config.API_KEY
    if not expected:
        # SEO_API_KEY 未設，視為開發模式（local-only 環境），直接放行並警告
        logger.warning(
            "SEO_API_KEY is not set — API authentication is DISABLED. "
            "Set this variable in production."
        )
        return ""

    # 明確處理 None（header 未傳）與空字串，再做 constant-time 比較防 timing attack
    if api_key is None or not hmac.compare_digest(api_key, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    return api_key
