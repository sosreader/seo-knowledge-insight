# Laminar Instrumentation — SEO QA Pipeline

## Rule: Every LLM / Token Call MUST Be Traced

Any code that calls an OpenAI (or other LLM) API — completions, embeddings,
or chat — MUST have Laminar tracing active BEFORE it is considered complete.
Non-instrumented LLM calls are treated as incomplete work.

---

## Checklist — Before Committing Any LLM-Related Code

### 1. Function-level tracing

- [ ] Every function that calls `client.chat.completions.create()` or
      `client.embeddings.create()` is decorated with `@observe()`.
- [ ] Every async function that calls an OpenAI API is decorated with
      `@observe()` (async decorators work the same way).
- [ ] Custom span names are used (`@observe(name="my_step")`) so the UI is
      readable.

### 2. CLI / pipeline scripts

- [ ] `init_laminar()` is called once at the start of `main()`.
- [ ] `flush_laminar()` is called in the `finally` block of `main()`.
- [ ] Both are imported from `utils.observability`.

### 3. FastAPI / API layer

- [ ] `Laminar.initialize()` is called once at module load time
      (currently in `app/main.py` — do NOT duplicate).
- [ ] **CRITICAL**: `_patch_openai_instrumentor()` from `utils.observability` is called
      **BEFORE** `Laminar.initialize()` to fix lmnr 0.5.x + opentelemetry-instrumentation-openai ≥0.44.0
      compatibility. Without this, OpenAI traces will not appear in Laminar dashboard.
- [ ] Functions in `app/core/` that touch OpenAI are decorated with
      `@observe()` imported from `lmnr`.

### 4. Online scoring (rag_chat only)

- [ ] `score_rag_response(answer=..., sources=..., query=...)` is called
      **inside** the `@observe(name="rag_chat")` function body, before it returns.
- [ ] `score_rag_response` is imported from `utils.laminar_scoring`.
- [ ] No `LaminarClient` or `trace_id` plumbing is needed — `Laminar.event()`
      attaches to the current span automatically.

### 5. Offline evaluations

- [ ] A corresponding `evals/eval_*.py` file exists and is registered under
      `group_name` matching the capability name.
- [ ] Eval scripts use `lmnr.evaluate()` (NOT a bare Python assertion).
- [ ] Each eval has at least **two evaluators** (one binary, one continuous).

---

## Patterns

### Pattern A — Pipeline script (CLI)

```python
from utils.observability import init_laminar, flush_laminar, observe

@observe(name="step_name")
def my_step(input_data: str) -> dict:
    client = _client()
    resp = client.chat.completions.create(...)
    return {"result": resp.choices[0].message.content}

def main(args):
    init_laminar()
    try:
        result = my_step(args.input)
    finally:
        flush_laminar()
```

### Pattern B — FastAPI / async

```python
from lmnr import Laminar, observe
from utils.laminar_scoring import score_rag_response

@observe(name="rag_chat")
async def rag_chat(message: str, history: list[dict] | None = None) -> dict:
    # ... do work ...
    answer = resp.choices[0].message.content or ""
    sources = [...]

    # score_rag_response uses Laminar.event() internally — no trace_id needed
    score_rag_response(answer=answer, sources=sources, query=message)
    return {"answer": answer, "sources": sources}
```

### Pattern C — New offline eval script

```python
# evals/eval_<capability>.py
from lmnr import evaluate

data = [
    {"data": {"input": "..."}, "target": {"expected": "..."}},
]

def executor(data: dict) -> dict:
    # Call the function under test (no raw OpenAI client here)
    result = my_function(data["input"])
    return {"output": result}

def binary_check(output: dict, target: dict) -> float:
    return 1.0 if output["output"] == target["expected"] else 0.0

def continuous_score(output: dict, target: dict) -> float:
    # Return a 0–1 float
    return some_metric(output, target)

evaluate(
    data=data,
    executor=executor,
    evaluators={"binary_check": binary_check, "continuous_score": continuous_score},
    group_name="<capability>_quality",
)
```

---

## Project Eval Coverage Map

| Capability | Eval file | Group name | Evaluators |
|------------|-----------|------------|------------|
| Retrieval (keyword search) | `evals/eval_retrieval.py` | `retrieval_quality` | keyword_hit_rate, top1_category_match, top5_category_coverage |
| Q&A extraction | `evals/eval_extraction.py` | `extraction_quality` | qa_count_in_range, keyword_coverage, no_admin_content, avg_confidence |
| RAG chat (E2E) | `evals/eval_chat.py` | `chat_quality` | has_answer, has_sources, answer_keyword_coverage, top_source_in_expected_category |
| LLM judge (05_evaluate.py) | (uses Laminar tracing only) | — | Existing `@observe` on `_llm_judge*` functions |

---

## Online Scoring — rag_chat trace scores

Each `rag_chat` trace automatically receives four scores posted via
`utils/laminar_scoring.py`:

| Evaluator | Type | Description |
|-----------|------|-------------|
| `answer_length` | binary | 1 if answer > 50 chars |
| `has_sources` | binary | 1 if >= 1 source retrieved |
| `top_source_score` | continuous | cosine similarity of top-ranked source |
| `source_count` | continuous | #sources / 5, capped at 1.0 |

---

## Running Evals Locally

```bash
# Install lmnr CLI (one-time)
pip install 'lmnr>=0.5.0'

# Export project key
export LMNR_PROJECT_API_KEY=<your-key>

# Run all evals
lmnr eval

# Run individual
python evals/eval_retrieval.py
python evals/eval_extraction.py
python evals/eval_chat.py   # also needs OPENAI_API_KEY
```

## Environment Variables Required

| Variable | Required for | Notes |
|----------|-------------|-------|
| `LMNR_PROJECT_API_KEY` | All tracing + all evals | Get from https://lmnr.ai dashboard |
| `OPENAI_API_KEY` | `eval_chat.py`, pipeline scripts | Standard OpenAI key |

---

## Violation Examples

```python
# WRONG — LLM call without @observe
def classify(text: str) -> str:
    resp = client.chat.completions.create(...)   # no trace!
    return resp.choices[0].message.content

# CORRECT
@observe(name="classify")
def classify(text: str) -> str:
    resp = client.chat.completions.create(...)
    return resp.choices[0].message.content
```

```python
# WRONG — pipeline script exits without flush
def main():
    init_laminar()
    result = extract_qa(text)   # spans not flushed on exit!

# CORRECT
def main():
    init_laminar()
    try:
        result = extract_qa(text)
    finally:
        flush_laminar()         # always flush
```
