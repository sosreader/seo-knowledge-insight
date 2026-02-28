"""Laminar observability utilities for pipeline CLI scripts.

app/main.py already calls Laminar.initialize() at startup.
Pipeline scripts (02–05) must call init_laminar() explicitly before
any @observe-decorated functions run, and flush_laminar() before exit.

Usage in a pipeline script:
    from utils.observability import init_laminar, flush_laminar, observe

    @observe(name="my_step")
    def my_step(...):
        ...

    def main(args):
        init_laminar()
        try:
            ...do work...
        finally:
            flush_laminar()
"""
from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

_initialized: bool = False

# ---------------------------------------------------------------------------
# observe — re-exported from lmnr with a no-op fallback
# ---------------------------------------------------------------------------
try:
    from lmnr import observe  # type: ignore[import]
except ImportError:
    def observe(name: str | None = None, **_kwargs):  # type: ignore[misc]
        """No-op shim when lmnr is not installed."""
        def decorator(fn):
            return fn
        return decorator


def init_laminar() -> None:
    """Initialize Laminar for pipeline CLI scripts.

    Safe to call multiple times — subsequent calls after the first are no-ops.
    If LMNR_PROJECT_API_KEY is unset, the call is silently skipped so the
    pipeline works without Laminar credentials.
    """
    global _initialized
    if _initialized:
        return

    api_key = os.getenv("LMNR_PROJECT_API_KEY", "")
    if not api_key:
        logger.debug(
            "LMNR_PROJECT_API_KEY unset — skipping Laminar init (traces won't be sent)"
        )
        return

    try:
        from lmnr import Laminar  # type: ignore[import]

        Laminar.initialize(project_api_key=api_key)
        _initialized = True
        logger.debug("Laminar initialized for pipeline script")
    except ImportError:
        logger.warning(
            "lmnr package not installed; skipping Laminar init. "
            "Run: pip install 'lmnr>=0.5.0'"
        )
    except Exception as exc:
        logger.warning("Laminar.initialize() failed: %s", exc)


def flush_laminar() -> None:
    """Flush pending Laminar spans before process exit.

    Call this at the end of every pipeline script's main() so in-flight spans
    are delivered before the interpreter shuts down.
    """
    if not _initialized:
        return
    try:
        from lmnr import Laminar  # type: ignore[import]

        Laminar.flush()
    except Exception as exc:
        logger.debug("Laminar.flush() raised: %s", exc)
