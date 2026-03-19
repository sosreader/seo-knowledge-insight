# Search & Chat

These are the most commonly used endpoints for frontend integration.

## Semantic Search

`POST /api/v1/search`

Search the knowledge base using hybrid semantic + keyword search with synonym expansion.

### Request

```json
{
  "query": "How to improve Core Web Vitals",
  "top_k": 5,
  "category": "Technical SEO"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `query` | string | Yes | Search query (1-500 chars) |
| `top_k` | number | No | Number of results (default: 5, max: 20) |
| `category` | string | No | Filter by category |
| `extraction_model` | string | No | Filter by extraction model (e.g. `"claude-code"`) |
| `maturity_level` | string | No | Boost results matching this maturity level (`"L1"`-`"L4"`) |

### Response

```json
{
  "results": [
    {
      "question": "What are Core Web Vitals and how do they impact SEO?",
      "answer": "Core Web Vitals are a set of metrics...",
      "score": 0.89,
      "source_type": "meeting",
      "source_collection": "weekly-meetings",
      "category": "Technical SEO",
      "difficulty": "advanced",
      "id": "a1b2c3d4e5f67890"
    }
  ],
  "total": 5,
  "mode": "hybrid"
}
```

### Search Modes (automatic)

| Condition | Mode | Description |
|-----------|------|-------------|
| Supabase configured | `hybrid` | pgvector embedding + keyword boost |
| OpenAI key only | `hybrid` | Embedding similarity + keyword boost |
| No OpenAI key | `keyword` | Keyword-only search with synonym expansion |

### Frontend Example

```typescript
async function searchKnowledgeBase(query: string, category?: string) {
  const res = await fetch("/api/proxy/search", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, top_k: 10, category }),
  });
  const data = await res.json();
  return data.results; // { question, answer, score, source_type, category }[]
}
```

---

## RAG Chat

`POST /api/v1/chat`

Single-turn question answering with automatic knowledge base retrieval.

### Request

```json
{
  "message": "What is the difference between canonical URL and 301 redirect?",
  "history": [
    { "role": "user", "content": "What is canonical URL?" },
    { "role": "assistant", "content": "A canonical URL is..." }
  ],
  "mode": "rag"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `message` | string | Yes | User message (1-2000 chars) |
| `history` | array | No | Previous messages for context (max 20) |
| `mode` | string | No | `"rag"` or `"agent"` (default: auto) |
| `maturity_level` | string | No | Client SEO maturity level (`"L1"`-`"L4"`) for response depth tuning |

### Response

```json
{
  "answer": "Canonical URLs and 301 redirects serve different purposes...",
  "sources": [
    {
      "question": "What is canonical URL?",
      "answer": "...",
      "source_type": "meeting",
      "category": "Technical SEO",
      "id": "abc123def456"
    }
  ],
  "mode": "rag",
  "metadata": {
    "model": "gpt-5.2",
    "provider": "openai",
    "mode": "rag",
    "input_tokens": 1250,
    "output_tokens": 380,
    "total_tokens": 1630,
    "duration_ms": 2340,
    "retrieval_count": 5
  }
}
```

### Mode Comparison

| Mode | Behavior | Latency | Use Case |
|------|----------|---------|----------|
| `rag` | Single retrieval + generation | ~2-3s | Simple factual questions |
| `agent` | Multi-turn search (up to 5 rounds) | ~5-15s | Complex comparison questions |
| `context-only` | No LLM, returns sources only | ~0.5s | When no OpenAI key |

### Frontend Example

```typescript
interface ChatResponse {
  answer: string | null;
  sources: Array<{
    question: string;
    answer: string;
    source_type: string;
    category: string;
    id: string;
  }>;
  mode: "rag" | "agent" | "context-only";
  metadata?: {
    model: string;
    duration_ms: number;
    total_tokens: number;
  };
}

async function askQuestion(message: string, mode?: "rag" | "agent") {
  const res = await fetch("/api/proxy/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, mode }),
  });
  return (await res.json()) as ChatResponse;
}
```

---

## Session-Based Chat

For multi-turn conversations where context needs to be preserved across messages.

### Create Session

```typescript
const session = await fetch("/api/proxy/sessions", { method: "POST" });
const { id } = await session.json();
// id: "550e8400-e29b-41d4-a716-446655440000"
```

### Send Message

```typescript
const response = await fetch(`/api/proxy/sessions/${sessionId}/messages`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ message: "What is structured data?", mode: "rag" }),
});
```

### Response includes metadata

```json
{
  "role": "assistant",
  "content": "Structured data is...",
  "metadata": {
    "model": "gpt-5.2",
    "mode": "rag",
    "duration_ms": 1820,
    "retrieval_count": 3
  }
}
```

### Get Session History

```typescript
const session = await fetch(`/api/proxy/sessions/${sessionId}`);
const { messages } = await session.json();
// messages: Array<{ role, content, metadata?, created_at }>
```
