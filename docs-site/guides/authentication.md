# Authentication

All API endpoints (except `/health`) require the `X-API-Key` header.

## Header

```
X-API-Key: your-api-key
```

## Configuration

Set `SEO_API_KEY` in `.env`:

```env
SEO_API_KEY=your-secret-key
```

When `SEO_API_KEY` is not set, authentication is disabled (development mode only). In production, requests without a valid key receive `401 Unauthorized`.

## Example

```bash
curl http://localhost:8002/api/v1/qa \
  -H "X-API-Key: your-api-key"
```

## Rate Limits

| Endpoint Group | Limit |
|----------------|-------|
| Default (QA, Search, Feedback, Pipeline, Synonyms) | Configurable |
| Chat | Lower limit |
| Report Generation | Lowest limit |
