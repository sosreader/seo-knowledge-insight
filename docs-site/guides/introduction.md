# SEO Knowledge Insight API

SEO knowledge base API with RAG chat, semantic search, weekly reports, and ETL pipeline management.

## Features

- **QA Knowledge Base** -- 1,469+ SEO Q&A pairs from meetings and articles (8 sources)
- **Semantic Search** -- Hybrid search (pgvector embedding + keyword) with synonym expansion
- **RAG Chat** -- Single-turn RAG and multi-turn agent mode with inline citations
- **Weekly Reports** -- Automated SEO report generation from metrics snapshots (7 dimensions)
- **Pipeline Management** -- ETL pipeline for Notion, Medium, iThome, Google Case Studies, Ahrefs, SEJ, and Growth Memo
- **Session Management** -- Persistent multi-turn chat sessions with maturity-aware responses
- **Meeting Prep** -- Deep research reports for SEO consulting sessions

## Base URL

| Environment | URL |
|-------------|-----|
| Local | `http://localhost:8002` |
| Production | `https://pu4fsreadnjcsqnfuqpyzndm4m0nctua.lambda-url.ap-northeast-1.on.aws` |

## Quick Start

```bash
# Health check (no auth required)
curl http://localhost:8002/health

# Search the knowledge base
curl -X POST http://localhost:8002/api/v1/search \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-key" \
  -d '{"query": "Core Web Vitals", "top_k": 5}'
```

## API Documentation

The interactive API reference is available at the [root page](..) with full Try It functionality powered by [Scalar](https://github.com/scalar/scalar).
