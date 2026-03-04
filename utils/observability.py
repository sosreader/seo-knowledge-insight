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

import inspect
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


def _patch_openai_instrumentor() -> None:
    """Patch lmnr's internal OpenAI instrumentor init.

    lmnr 0.5.x passes ``enrich_token_usage`` to ``OpenAIInstrumentor()``,
    but opentelemetry-instrumentation-openai >= 0.44.0 removed that param.
    This patch drops the unsupported kwarg so the latest instrumentor works.

    Remove this patch once lmnr ships a compatible release.
    """
    try:
        import lmnr.openllmetry_sdk.tracing.tracing as _tracing  # type: ignore[import]
        from opentelemetry.instrumentation.openai import OpenAIInstrumentor

        sig = inspect.signature(OpenAIInstrumentor.__init__)
        if "enrich_token_usage" in sig.parameters:
            return  # native support — no patch needed

        def _patched_init(should_enrich_metrics: bool) -> bool:
            try:
                # enrich_token_usage dropped — removed in
                # opentelemetry-instrumentation-openai >= 0.44.0
                instrumentor = OpenAIInstrumentor(
                    enrich_assistant=should_enrich_metrics,
                    upload_base64_image=None,
                )
                if not instrumentor.is_instrumented_by_opentelemetry:
                    instrumentor.instrument()
                return True
            except Exception as exc:
                logger.warning("Patched OpenAI instrumentor init failed: %s", exc)
                return False

        _tracing.init_openai_instrumentor = _patched_init
        logger.debug("Patched lmnr init_openai_instrumentor (dropped enrich_token_usage)")
    except Exception as exc:
        logger.debug("_patch_openai_instrumentor skipped: %s", exc)


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
        logger.info(
            "LMNR_PROJECT_API_KEY unset — skipping Laminar init (traces won't be sent)"
        )
        return

    try:
        from lmnr import Laminar  # type: ignore[import]

        _patch_openai_instrumentor()
        Laminar.initialize(project_api_key=api_key)
        _initialized = True
        logger.info("Laminar initialized for pipeline script")
    except ImportError:
        logger.warning(
            "lmnr package not installed; skipping Laminar init. "
            "Run: pip install 'lmnr>=0.5.0'"
        )
    except Exception as exc:
        logger.warning("Laminar.initialize() failed: %s", exc)


def start_cli_span(
    name: str, input_data: str = ""
) -> "contextlib.AbstractContextManager[object]":
    """Context manager for CLI command spans (TOOL type).

    Returns Laminar.start_as_current_span if available, else a no-op context manager.
    """
    import contextlib

    if not _initialized:
        return contextlib.nullcontext()
    try:
        from lmnr import Laminar  # type: ignore[import]

        return Laminar.start_as_current_span(
            name=name,
            input=input_data,
            span_type="TOOL",
        )
    except Exception:
        logger.debug("start_cli_span(%s) failed, falling back to no-op", name)
        return contextlib.nullcontext()


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
