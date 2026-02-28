"""
統一 API 回應 Envelope — Phase D

符合 Microsoft REST API Guidelines (2024) 的標準格式：
{
    "data": { ... },
    "error": null,
    "meta": { "request_id": "uuid", "version": "1.0" }
}
"""
from __future__ import annotations

import uuid
from typing import Generic, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")

_API_VERSION = "1.0"


class ApiResponse(BaseModel, Generic[T]):
    data: Optional[T] = None
    error: Optional[str] = None
    meta: dict[str, str] = Field(default_factory=dict)

    @classmethod
    def ok(cls, data: T) -> "ApiResponse[T]":
        """成功回應工廠方法。"""
        return cls(
            data=data,
            error=None,
            meta={"request_id": str(uuid.uuid4()), "version": _API_VERSION},
        )

    @classmethod
    def fail(cls, message: str) -> "ApiResponse[None]":
        """錯誤回應工廠方法。"""
        return cls(
            data=None,
            error=message,
            meta={"request_id": str(uuid.uuid4()), "version": _API_VERSION},
        )
