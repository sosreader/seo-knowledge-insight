# Pattern: laminar-initialize-before-all-imports

## Confidence: 0.95

## Context

Python observability SDKs that rely on monkey-patching (Laminar, OpenTelemetry,
ddtrace, etc.) must be initialized **before** any of the libraries they patch are
imported. In a FastAPI application this is easy to get wrong because router
imports pull in the patched libraries transitively.

## Problem

```python
# WRONG — openai is monkey-patched too late
from lmnr import Laminar               # line A
from app.routers import chat           # line B: imports openai transitively
Laminar.initialize(project_api_key=…) # line C: patch arrives AFTER line B
```

Symptoms: spans appear in Laminar but Top LLM spans / Tokens / Cost panels show
"No data" — the auto-instrumentation hook never fired.

## Solution

```python
# app/main.py — very first lines, before ALL other imports
import os
_lmnr_key = os.getenv("LMNR_PROJECT_API_KEY", "")
try:
    from lmnr import Laminar
    if _lmnr_key:
        Laminar.initialize(project_api_key=_lmnr_key)
except ImportError:
    Laminar = None  # type: ignore

# — now safe to import everything else —
from fastapi import FastAPI
from app.routers import chat, qa, search
```

## Why

Laminar (via OpenTelemetry) replaces `openai.OpenAI.__init__` with a wrapped
version that injects tracing context. Once the original `openai` module is
loaded into `sys.modules`, importing it again returns the cached (un-patched)
version. The patch must happen during the **first** import.

## Generalisation

The same rule applies to any monkey-patching observability tool:

- OpenTelemetry `configure_opentelemetry()`
- Datadog `ddtrace.patch_all()`
- New Relic `newrelic.agent.initialize()`
- Sentry `sentry_sdk.init()`

**Rule**: In any entry-point file (FastAPI `main.py`, Celery `worker.py`,
Django `wsgi.py`), call the observability SDK initializer in the first ≤10
lines before any application imports.

## Related: OpenAI Instrumentor Compatibility Patch

As of lmnr 0.5.2 + opentelemetry-instrumentation-openai ≥0.44.0, an additional
compatibility patch is required before initialization. See
`utils/observability._patch_openai_instrumentor()` — it must be called between
the Laminar import and `Laminar.initialize()` to work around lmnr's outdated
parameter passing to OpenAIInstrumentor.

Updated initialization order in `app/main.py`:
```python
_lmnr_key = os.getenv("LMNR_PROJECT_API_KEY", "")
try:
    from lmnr import Laminar
    if _lmnr_key:
        from utils.observability import _patch_openai_instrumentor
        _patch_openai_instrumentor()  # patch BEFORE init
        Laminar.initialize(project_api_key=_lmnr_key)
except ImportError:
    Laminar = None
# — now safe to import everything else —
```

## Discovered

2026-03-01 — SEO Knowledge Insight project, debugging Laminar dashboard empty
panels despite spans being recorded successfully.

2026-03-03 — Same project, discovered lmnr 0.5.2 incompatibility with
opentelemetry-instrumentation-openai ≥0.44.0; added `_patch_openai_instrumentor()`.
