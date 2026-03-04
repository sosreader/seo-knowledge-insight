"""
GET  /api/v1/reports          — 列出所有週報
GET  /api/v1/reports/{date}   — 取得單篇週報（Markdown 原文）
POST /api/v1/reports/generate — 觸發週報生成（同步執行，回傳新報告）
"""
from __future__ import annotations

import logging
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app import config
from app.core.limiter import limiter
from app.core.schemas import ApiResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])

_REPORT_DIR = config.OUTPUT_DIR
_REPORT_PATTERN = re.compile(r"^report_(\d{8})\.md$")
_DATE_RE = re.compile(r"^\d{8}$")
_ALLOWED_URL_SCHEMES = frozenset({"https", "http"})
_ALLOWED_URL_HOSTS = frozenset({"docs.google.com", "sheets.google.com"})


# ──────────── schema ────────────

class ReportSummary(BaseModel):
    date: str
    filename: str
    size_bytes: int


class ReportListResponse(BaseModel):
    items: list[ReportSummary]
    total: int


class ReportDetail(BaseModel):
    date: str
    filename: str
    content: str
    size_bytes: int


class GenerateRequest(BaseModel):
    metrics_url: Optional[str] = None


class GenerateResponse(BaseModel):
    date: str
    filename: str
    size_bytes: int


# ──────────── helpers ────────────

def _list_reports() -> list[ReportSummary]:
    """掃描 output/ 下所有 report_YYYYMMDD.md 檔案。"""
    if not _REPORT_DIR.exists():
        return []
    reports: list[ReportSummary] = []
    for f in sorted(_REPORT_DIR.glob("report_*.md"), reverse=True):
        m = _REPORT_PATTERN.match(f.name)
        if m:
            reports.append(ReportSummary(
                date=m.group(1),
                filename=f.name,
                size_bytes=f.stat().st_size,
            ))
    return reports


# ──────────── routes ────────────

@router.get("", response_model=ApiResponse[ReportListResponse])
@limiter.limit("60/minute")
def list_reports(request: Request) -> ApiResponse[ReportListResponse]:
    items = _list_reports()
    return ApiResponse.ok(ReportListResponse(items=items, total=len(items)))


@router.get("/{date}", response_model=ApiResponse[ReportDetail])
@limiter.limit("60/minute")
def get_report(request: Request, date: str) -> ApiResponse[ReportDetail]:
    if not _DATE_RE.match(date):
        raise HTTPException(status_code=400, detail="Invalid date format, expected YYYYMMDD")
    filename = f"report_{date}.md"
    filepath = _REPORT_DIR / filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail=f"Report {filename} not found")
    content = filepath.read_text(encoding="utf-8")
    return ApiResponse.ok(ReportDetail(
        date=date,
        filename=filename,
        content=content,
        size_bytes=filepath.stat().st_size,
    ))


@router.post("/generate", response_model=ApiResponse[GenerateResponse])
@limiter.limit("5/minute")
def generate_report(req: GenerateRequest, request: Request) -> ApiResponse[GenerateResponse]:
    """同步執行 scripts/04_generate_report.py 生成週報。"""
    cmd = [
        sys.executable,
        str(config.ROOT_DIR / "scripts" / "04_generate_report.py"),
    ]
    if req.metrics_url:
        parsed = urlparse(req.metrics_url)
        if parsed.scheme not in _ALLOWED_URL_SCHEMES:
            raise HTTPException(status_code=400, detail="metrics_url must use http or https")
        if parsed.netloc not in _ALLOWED_URL_HOSTS:
            raise HTTPException(status_code=400, detail="metrics_url host not allowed")
        cmd.extend(["--input", req.metrics_url])

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(config.ROOT_DIR),
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Report generation timed out")

    if result.returncode != 0:
        logger.error("Report generation failed: %s", result.stderr[-500:] if result.stderr else "")
        raise HTTPException(
            status_code=500,
            detail="Report generation failed",
        )

    # 找到最新生成的報告
    reports = _list_reports()
    if not reports:
        raise HTTPException(status_code=500, detail="No report found after generation")

    latest = reports[0]
    return ApiResponse.ok(GenerateResponse(
        date=latest.date,
        filename=latest.filename,
        size_bytes=latest.size_bytes,
    ))
