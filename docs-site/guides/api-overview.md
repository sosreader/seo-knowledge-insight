# API Overview

The API has 10 routers and 42 endpoints. All endpoints under `/api/v1/*` require `X-API-Key` authentication.

## Endpoints Summary

### Health Check

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/health` | No | Server health check |

### QA Knowledge Base -- 4 endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/qa` | List Q&A items (paginated, filterable) |
| GET | `/api/v1/qa/{id}` | Get single Q&A detail |
| GET | `/api/v1/qa/categories` | List all categories |
| GET | `/api/v1/qa/collections` | List all source collections |

**QA Filters:**
- `category` -- Filter by SEO category (e.g. "Technical SEO", "Content Strategy")
- `keyword` -- Full-text keyword search
- `difficulty` -- `basic` / `advanced`
- `evergreen` -- `true` / `false`
- `source_type` -- `meeting` / `article`
- `source_collection` -- Specific collection name
- `maturity_relevance` -- `L1` / `L2` / `L3` / `L4`
- `limit` / `offset` -- Pagination
- `sort_by` / `sort_order` -- Sorting

### Search -- 1 endpoint

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/search` | Hybrid semantic + keyword search |

**Request body:**
```json
{
  "query": "How to optimize Core Web Vitals?",
  "top_k": 5,
  "category": "Technical SEO"
}
```

### Chat -- 1 endpoint

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/chat` | Single-turn RAG chat (supports agent mode) |

**Request body:**
```json
{
  "message": "What is canonical URL?",
  "history": [],
  "mode": "rag"
}
```

### Sessions -- 4 endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/sessions` | Create new chat session |
| GET | `/api/v1/sessions/{id}` | Get session with message history |
| POST | `/api/v1/sessions/{id}/messages` | Send message in session |
| DELETE | `/api/v1/sessions/{id}` | Delete session |

### Reports -- 3 endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/reports` | List all weekly reports |
| GET | `/api/v1/reports/{date}` | Get report by date (YYYYMMDD) |
| POST | `/api/v1/reports/generate` | Generate new report |

### Feedback -- 1 endpoint

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/feedback` | Submit feedback on search/chat responses |

### Synonyms -- 4 endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/synonyms` | List all synonyms (static + custom) |
| POST | `/api/v1/synonyms` | Add custom synonym |
| PUT | `/api/v1/synonyms/{term}` | Update custom synonym |
| DELETE | `/api/v1/synonyms/{term}` | Delete custom synonym |

### Pipeline -- 18 endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/pipeline/status` | Pipeline step completion status |
| GET | `/api/v1/pipeline/meetings` | List meetings with metadata |
| GET | `/api/v1/pipeline/meetings/{id}/preview` | Meeting markdown preview |
| GET | `/api/v1/pipeline/source-docs` | List all source documents |
| GET | `/api/v1/pipeline/source-docs/{collection}/{file}/preview` | Document preview |
| GET | `/api/v1/pipeline/unprocessed` | List unprocessed documents |
| GET | `/api/v1/pipeline/logs` | Fetch history logs |
| POST | `/api/v1/pipeline/fetch` | Trigger Notion incremental fetch |
| POST | `/api/v1/pipeline/fetch-articles` | Trigger article fetch |
| POST | `/api/v1/pipeline/extract-qa` | Trigger Q&A extraction |
| POST | `/api/v1/pipeline/dedupe-classify` | Trigger dedup + classification |
| POST | `/api/v1/pipeline/metrics` | Parse SEO metrics from Google Sheets |
| POST | `/api/v1/pipeline/metrics/save` | Save metrics snapshot |
| GET | `/api/v1/pipeline/metrics/snapshots` | List metrics snapshots |
| DELETE | `/api/v1/pipeline/metrics/snapshots/{id}` | Delete snapshot |
| GET | `/api/v1/pipeline/metrics/trends` | Timeseries anomaly detection |
| GET | `/api/v1/pipeline/llm-usage` | LLM cost/latency monitoring |
| POST | `/api/v1/pipeline/crawled-not-indexed` | Crawled-not-indexed analysis |

### Meeting Prep -- 3 endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/meeting-prep` | List all meeting prep reports |
| GET | `/api/v1/meeting-prep/maturity-trend` | SEO maturity trend timeseries |
| GET | `/api/v1/meeting-prep/{date}` | Get meeting prep report by date |

## Response Format

All API responses follow a consistent JSON structure:

```json
{
  "data": { ... },
  "error": null,
  "meta": {
    "request_id": "uuid",
    "version": "3.4.0"
  }
}
```

## Error Responses

| Status | Meaning |
|--------|---------|
| 400 | Invalid request (Zod validation failed) |
| 401 | Missing or invalid API key |
| 404 | Resource not found |
| 429 | Rate limit exceeded |
| 500 | Internal server error |

```json
{
  "error": "Validation failed",
  "details": "message: String must contain at least 1 character(s)"
}
```
