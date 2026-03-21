/**
 * OpenAPI 3.1 spec for SEO Knowledge Insight API.
 *
 * Hand-maintained to avoid zod-openapi compatibility issues with Zod v4.
 * Each path matches the routes in src/routes/*.ts.
 */

const API_VERSION = "3.6.0";

type OpenAPISpec = Record<string, unknown>;

function ref(name: string) {
  return { $ref: `#/components/schemas/${name}` };
}

function jsonContent(schema: Record<string, unknown>, description = "") {
  return { description, content: { "application/json": { schema } } };
}

function apiResponse(dataSchema: Record<string, unknown>) {
  return {
    type: "object",
    properties: {
      data: dataSchema,
      error: { type: "string", nullable: true },
      meta: ref("ApiResponseMeta"),
    },
  };
}

const schemas: Record<string, Record<string, unknown>> = {
  ApiResponseMeta: {
    type: "object",
    properties: {
      request_id: { type: "string", format: "uuid" },
      version: { type: "string" },
    },
  },
  QAItem: {
    type: "object",
    properties: {
      id: {
        type: "string",
        description: "16-char hex stable ID",
        example: "a1b2c3d4e5f67890",
      },
      seq: { type: "integer", description: "Sequential number" },
      question: { type: "string" },
      answer: { type: "string" },
      keywords: { type: "array", items: { type: "string" } },
      confidence: { type: "number" },
      category: { type: "string", example: "SEO" },
      difficulty: { type: "string", enum: ["basic", "advanced"] },
      evergreen: { type: "boolean" },
      source_title: { type: "string" },
      source_date: { type: "string" },
      is_merged: { type: "boolean" },
      notion_url: { type: "string", nullable: true },
      source_type: { type: "string", enum: ["meeting", "article"] },
      source_collection: { type: "string" },
      source_url: { type: "string" },
      extraction_model: { type: "string", nullable: true },
      maturity_relevance: {
        type: "string",
        enum: ["L1", "L2", "L3", "L4"],
        nullable: true,
        description: "SEO maturity level relevance",
      },
      freshness_score: { type: "number" },
    },
  },
  SearchResult: {
    type: "object",
    properties: {
      id: { type: "string" },
      question: { type: "string" },
      answer: { type: "string" },
      keywords: { type: "array", items: { type: "string" } },
      category: { type: "string" },
      difficulty: { type: "string" },
      evergreen: { type: "boolean" },
      source_title: { type: "string" },
      source_date: { type: "string" },
      source_type: { type: "string" },
      source_collection: { type: "string" },
      source_url: { type: "string" },
      extraction_model: { type: "string", nullable: true },
      maturity_relevance: {
        type: "string",
        enum: ["L1", "L2", "L3", "L4"],
        nullable: true,
      },
      score: { type: "number" },
    },
  },
  ChatRequest: {
    type: "object",
    required: ["message"],
    properties: {
      message: {
        type: "string",
        minLength: 1,
        maxLength: 2000,
        example: "What is Core Web Vitals?",
      },
      history: {
        type: "array",
        maxItems: 20,
        items: {
          type: "object",
          properties: {
            role: { type: "string", enum: ["user", "assistant"] },
            content: { type: "string" },
          },
        },
      },
      mode: {
        type: "string",
        enum: ["agent", "rag"],
        description: "對話模式（未指定時自動偵測）/ Chat mode (auto-detected if omitted)",
      },
      maturity_level: {
        type: "string",
        enum: ["L1", "L2", "L3", "L4"],
        description: "客戶 SEO 成熟度等級，用於調整回應深度 / Client SEO maturity level for response depth tuning",
      },
    },
  },
  ChatResponse: {
    type: "object",
    properties: {
      answer: { type: "string", nullable: true },
      sources: { type: "array", items: ref("SourceItem") },
      mode: { type: "string", enum: ["rag", "context-only", "agent"] },
      metadata: ref("MessageMetadata"),
    },
  },
  SourceItem: {
    type: "object",
    properties: {
      id: { type: "string" },
      question: { type: "string" },
      category: { type: "string" },
      source_title: { type: "string" },
      source_date: { type: "string" },
      score: { type: "number" },
      source_type: { type: "string" },
      source_collection: { type: "string" },
      source_url: { type: "string" },
    },
  },
  MessageMetadata: {
    type: "object",
    properties: {
      model: { type: "string" },
      provider: { type: "string" },
      mode: { type: "string" },
      embedding_model: { type: "string" },
      input_tokens: { type: "integer" },
      output_tokens: { type: "integer" },
      total_tokens: { type: "integer" },
      reasoning_tokens: { type: "integer" },
      duration_ms: { type: "integer" },
      retrieval_count: { type: "integer" },
      reranker_used: { type: "boolean" },
    },
  },
  ReportSummary: {
    type: "object",
    properties: {
      date: { type: "string", example: "20260307" },
      filename: { type: "string" },
      size_bytes: { type: "integer" },
      meta: ref("ReportMeta"),
    },
  },
  ReportMeta: {
    type: "object",
    properties: {
      weeks: { type: "integer" },
      generated_at: { type: "string" },
      generation_mode: { type: "string" },
      generation_label: { type: "string" },
      model: { type: "string" },
    },
  },
  SessionSummary: {
    type: "object",
    properties: {
      id: { type: "string", format: "uuid" },
      title: { type: "string" },
      created_at: { type: "string", format: "date-time" },
      updated_at: { type: "string", format: "date-time" },
    },
  },
  SessionDetail: {
    allOf: [
      ref("SessionSummary"),
      {
        type: "object",
        properties: {
          messages: {
            type: "array",
            items: {
              type: "object",
              properties: {
                role: { type: "string" },
                content: { type: "string" },
                sources: { type: "array", items: { type: "object" } },
                created_at: { type: "string", format: "date-time" },
                metadata: { type: "object" },
              },
            },
          },
        },
      },
    ],
  },
  PipelineStepStatus: {
    type: "object",
    properties: {
      name: { type: "string" },
      label: { type: "string" },
      count: { type: "integer" },
      detail: { type: "string" },
    },
  },
  SourceDocEntry: {
    type: "object",
    properties: {
      file: { type: "string" },
      title: { type: "string" },
      source_type: { type: "string", enum: ["meeting", "article"] },
      source_collection: { type: "string" },
      source_url: { type: "string" },
      created_time: { type: "string" },
      size_bytes: { type: "integer" },
      is_processed: { type: "boolean" },
    },
  },
  MetricsSnapshotMeta: {
    type: "object",
    properties: {
      id: {
        type: "string",
        pattern: "^[0-9]{8}-[0-9]{6}$",
        example: "20260307-120000",
      },
      created_at: { type: "string", format: "date-time" },
      label: { type: "string" },
      source: { type: "string" },
      tab: { type: "string" },
      weeks: { type: "integer" },
    },
  },
  SynonymEntry: {
    type: "object",
    properties: {
      term: { type: "string" },
      synonyms: { type: "array", items: { type: "string" } },
      source: { type: "string", enum: ["static", "custom"] },
    },
  },
  PipelineRunResult: {
    type: "object",
    properties: {
      success: { type: "boolean" },
      output: { type: "string" },
      duration_ms: { type: "integer" },
    },
  },
};

const paths: Record<string, Record<string, unknown>> = {
  // Health
  "/health": {
    get: {
      tags: ["Health"],
      summary: "健康檢查 / Health check",
      operationId: "healthCheck",
      security: [],
      responses: {
        "200": jsonContent(
          {
            type: "object",
            properties: {
              status: { type: "string", example: "healthy" },
              timestamp: { type: "string", format: "date-time" },
              version: { type: "string" },
              capabilities: {
                type: "object",
                description:
                  "有效能力偵測（考慮 caller）。llm 為本次請求的有效 LLM：server 有 OpenAI 則為 openai；Claude Code 呼叫時為 claude-code；其餘為 none。\n\nEffective capability detection (caller-aware). `llm` reflects the effective LLM for this request: `openai` if server has OpenAI key; `claude-code` when called by Claude Code; `none` otherwise.",
                properties: {
                  runtime: {
                    type: "string",
                    enum: ["lambda", "local-server"],
                    description: "執行環境 / Runtime environment",
                  },
                  llm: {
                    type: "string",
                    enum: ["openai", "claude-code", "none"],
                    description:
                      "有效 LLM。openai = server 內建；claude-code = Claude Code 作為 LLM 引擎；none = 無 LLM。\n\nEffective LLM. `openai` = server built-in; `claude-code` = Claude Code acts as LLM engine; `none` = no LLM available.",
                  },
                  store: {
                    type: "string",
                    enum: ["supabase", "file"],
                    description: "資料儲存後端 / Data store backend",
                  },
                  agent: {
                    type: "string",
                    enum: ["enabled", "disabled"],
                    description: "Agent mode 狀態 / Agent mode status",
                  },
                  caller: {
                    type: "string",
                    enum: ["browser", "cli", "claude-code", "lambda", "unknown"],
                    description:
                      "呼叫端身份（由 User-Agent 推斷）/ Caller identity (inferred from User-Agent)",
                  },
                },
                required: ["runtime", "llm", "store", "agent", "caller"],
              },
            },
          },
          "Server is healthy",
        ),
      },
    },
  },

  // QA
  "/api/v1/qa": {
    get: {
      tags: ["QA"],
      summary: "列出 QA 項目 / List QA items",
      operationId: "listQA",
      parameters: [
        { name: "category", in: "query", schema: { type: "string" } },
        {
          name: "keyword",
          in: "query",
          schema: { type: "string", maxLength: 100 },
        },
        {
          name: "difficulty",
          in: "query",
          schema: { type: "string", enum: ["basic", "advanced"] },
        },
        {
          name: "evergreen",
          in: "query",
          schema: { type: "string", enum: ["true", "false"] },
        },
        { name: "source_type", in: "query", schema: { type: "string" } },
        { name: "source_collection", in: "query", schema: { type: "string" } },
        {
          name: "maturity_relevance",
          in: "query",
          schema: { type: "string", enum: ["L1", "L2", "L3", "L4"] },
          description: "依成熟度等級篩選 / Filter by maturity level",
        },
        {
          name: "sort_by",
          in: "query",
          schema: { type: "string", enum: ["source_date", "confidence"] },
        },
        {
          name: "sort_order",
          in: "query",
          schema: { type: "string", enum: ["asc", "desc"], default: "desc" },
        },
        {
          name: "limit",
          in: "query",
          schema: { type: "integer", minimum: 1, maximum: 100, default: 20 },
        },
        {
          name: "offset",
          in: "query",
          schema: { type: "integer", minimum: 0, default: 0 },
        },
      ],
      responses: {
        "200": jsonContent(
          apiResponse({
            type: "object",
            properties: {
              items: { type: "array", items: ref("QAItem") },
              total: { type: "integer" },
              offset: { type: "integer" },
              limit: { type: "integer" },
            },
          }),
          "Paginated QA list",
        ),
      },
    },
  },
  "/api/v1/qa/categories": {
    get: {
      tags: ["QA"],
      summary: "列出所有分類 / List all categories",
      operationId: "listCategories",
      responses: {
        "200": jsonContent(
          apiResponse({
            type: "object",
            properties: {
              categories: { type: "array", items: { type: "string" } },
            },
          }),
        ),
      },
    },
  },
  "/api/v1/qa/collections": {
    get: {
      tags: ["QA"],
      summary: "列出所有來源集合 / List all source collections",
      operationId: "listCollections",
      responses: {
        "200": jsonContent(
          apiResponse({
            type: "object",
            properties: {
              collections: {
                type: "array",
                items: {
                  type: "object",
                  properties: {
                    source_type: { type: "string" },
                    source_collection: { type: "string" },
                    count: { type: "integer" },
                  },
                },
              },
            },
          }),
        ),
      },
    },
  },
  "/api/v1/qa/{item_id}": {
    get: {
      tags: ["QA"],
      summary: "依 ID 取得 QA 項目 / Get QA item by ID",
      operationId: "getQAById",
      parameters: [
        {
          name: "item_id",
          in: "path",
          required: true,
          schema: { type: "string" },
          description: "十六進位 stable_id (16 字元) 或整數 seq / Hex stable_id (16 chars) or integer seq",
        },
      ],
      responses: {
        "200": jsonContent(apiResponse(ref("QAItem")), "QA item found"),
        "404": jsonContent(apiResponse({ type: "null" }), "QA item not found"),
      },
    },
  },

  // Search
  "/api/v1/search": {
    post: {
      tags: ["Search"],
      summary: "搜尋 QA 知識庫 / Search QA knowledge base",
      operationId: "search",
      requestBody: jsonContent(
        {
          type: "object",
          required: ["query"],
          properties: {
            query: {
              type: "string",
              minLength: 1,
              maxLength: 500,
              example: "Core Web Vitals",
            },
            top_k: { type: "integer", minimum: 1, maximum: 20, default: 5 },
            category: { type: "string" },
            extraction_model: { type: "string", example: "claude-code" },
            maturity_level: {
              type: "string",
              enum: ["L1", "L2", "L3", "L4"],
              description: "提升符合此成熟度等級的結果排序 / Boost results matching this maturity level",
            },
          },
        },
        "Search parameters",
      ),
      responses: {
        "200": jsonContent(
          apiResponse({
            type: "object",
            properties: {
              results: { type: "array", items: ref("SearchResult") },
              total: { type: "integer" },
              mode: { type: "string", enum: ["hybrid", "keyword"] },
            },
          }),
        ),
      },
    },
  },

  // Chat
  "/api/v1/chat": {
    post: {
      tags: ["Chat"],
      summary: "RAG 對話（單輪或 Agent 模式）/ RAG chat (single-turn or agent mode)",
      operationId: "chat",
      requestBody: jsonContent(
        ref("ChatRequest"),
        "Chat message with optional history",
      ),
      responses: {
        "200": jsonContent(
          apiResponse(ref("ChatResponse")),
          "Chat response with sources",
        ),
      },
    },
  },

  "/api/v1/chat/stream": {
    post: {
      tags: ["Chat"],
      summary: "SSE 串流 RAG 對話 / SSE streaming RAG chat",
      operationId: "chatStream",
      description:
        "Server-Sent Events 串流模式。本地開發可用；Lambda 環境回傳 501。\n\nSSE streaming chat. Available in local dev; returns 501 on Lambda.",
      requestBody: jsonContent(
        ref("ChatRequest"),
        "Chat message (same schema as POST /chat)",
      ),
      responses: {
        "200": {
          description: "SSE event stream (sources → token* → metadata → done)",
          content: {
            "text/event-stream": {
              schema: {
                type: "string",
                description:
                  "SSE events: sources (JSON array), token (text chunk), metadata (JSON), done ([DONE]), error (string)",
              },
            },
          },
        },
        "501": jsonContent(
          apiResponse({ type: "null" }),
          "Streaming not available in Lambda environment",
        ),
      },
    },
  },

  // Reports
  "/api/v1/reports": {
    get: {
      tags: ["Reports"],
      summary: "列出所有週報 / List all weekly reports",
      operationId: "listReports",
      responses: {
        "200": jsonContent(
          apiResponse({
            type: "object",
            properties: {
              items: { type: "array", items: ref("ReportSummary") },
              total: { type: "integer" },
            },
          }),
        ),
      },
    },
  },
  "/api/v1/reports/{date}": {
    get: {
      tags: ["Reports"],
      summary: "依日期取得週報 / Get report by date",
      operationId: "getReport",
      parameters: [
        {
          name: "date",
          in: "path",
          required: true,
          schema: { type: "string", pattern: "^\\d{8}(?:_[0-9a-f]{8})?$" },
          description: "YYYYMMDD 或 YYYYMMDD_hash8 格式 / YYYYMMDD or YYYYMMDD_hash8",
        },
      ],
      responses: {
        "200": jsonContent(
          apiResponse({
            type: "object",
            properties: {
              date: { type: "string" },
              filename: { type: "string" },
              content: { type: "string" },
              size_bytes: { type: "integer" },
              meta: ref("ReportMeta"),
            },
          }),
        ),
        "404": jsonContent(apiResponse({ type: "null" }), "Report not found"),
      },
    },
  },
  "/api/v1/reports/generate": {
    post: {
      tags: ["Reports"],
      summary: "生成週報 / Generate weekly report",
      operationId: "generateReport",
      description:
        "支援三種模式：本地（snapshot_id）、OpenAI（snapshot_id + use_openai）、Legacy（metrics_url）\n\nSupports three modes: local (snapshot_id), OpenAI (snapshot_id + use_openai), legacy (metrics_url)",
      requestBody: jsonContent({
        type: "object",
        properties: {
          snapshot_id: { type: "string", pattern: "^[0-9]{8}-[0-9]{6}$" },
          metrics_url: {
            type: "string",
            format: "uri",
            description: "Google Sheets URL",
          },
          weeks: { type: "integer", minimum: 1, maximum: 12 },
          use_openai: { type: "boolean" },
          situation_analysis: { type: "string", maxLength: 2000 },
          traffic_analysis: { type: "string", maxLength: 2000 },
          technical_analysis: { type: "string", maxLength: 2000 },
          intent_analysis: { type: "string", maxLength: 2000 },
          action_analysis: { type: "string", maxLength: 2000 },
          maturity_context: {
            type: "object",
            additionalProperties: { type: "string" },
            description: "Maturity dimension levels (e.g. {strategy: 'L2', process: 'L2'}). Overridden by snapshot.maturity if present.",
          },
        },
      }),
      responses: {
        "200": jsonContent(
          apiResponse({
            type: "object",
            properties: {
              date: { type: "string" },
              filename: { type: "string" },
              size_bytes: { type: "integer" },
              cache_hit: { type: "boolean" },
            },
          }),
        ),
      },
    },
  },

  // Sessions
  "/api/v1/sessions": {
    get: {
      tags: ["Sessions"],
      summary: "列出對話 Sessions / List chat sessions",
      operationId: "listSessions",
      parameters: [
        {
          name: "limit",
          in: "query",
          schema: { type: "integer", minimum: 1, maximum: 100, default: 20 },
        },
        {
          name: "offset",
          in: "query",
          schema: { type: "integer", minimum: 0, default: 0 },
        },
      ],
      responses: {
        "200": jsonContent(
          apiResponse({
            type: "object",
            properties: {
              items: { type: "array", items: ref("SessionSummary") },
              total: { type: "integer" },
            },
          }),
        ),
      },
    },
    post: {
      tags: ["Sessions"],
      summary: "建立新對話 Session / Create a new chat session",
      operationId: "createSession",
      requestBody: jsonContent({
        type: "object",
        properties: {
          title: { type: "string", maxLength: 100 },
        },
      }),
      responses: {
        "200": jsonContent(apiResponse(ref("SessionDetail"))),
      },
    },
  },
  "/api/v1/sessions/{session_id}": {
    get: {
      tags: ["Sessions"],
      summary: "取得 Session 含訊息 / Get session with messages",
      operationId: "getSession",
      parameters: [
        {
          name: "session_id",
          in: "path",
          required: true,
          schema: { type: "string", format: "uuid" },
        },
      ],
      responses: {
        "200": jsonContent(apiResponse(ref("SessionDetail"))),
        "404": jsonContent(apiResponse({ type: "null" }), "Session not found"),
      },
    },
    delete: {
      tags: ["Sessions"],
      summary: "刪除 Session / Delete a session",
      operationId: "deleteSession",
      parameters: [
        {
          name: "session_id",
          in: "path",
          required: true,
          schema: { type: "string", format: "uuid" },
        },
      ],
      responses: {
        "200": jsonContent(
          apiResponse({
            type: "object",
            properties: {
              deleted: { type: "boolean" },
              session_id: { type: "string" },
            },
          }),
        ),
        "404": jsonContent(apiResponse({ type: "null" }), "Session not found"),
      },
    },
  },
  "/api/v1/sessions/{session_id}/messages": {
    post: {
      tags: ["Sessions"],
      summary: "在 Session 中發送訊息 / Send message in session",
      operationId: "sendMessage",
      parameters: [
        {
          name: "session_id",
          in: "path",
          required: true,
          schema: { type: "string", format: "uuid" },
        },
      ],
      requestBody: jsonContent({
        type: "object",
        required: ["message"],
        properties: {
          message: { type: "string", minLength: 1, maxLength: 2000 },
          mode: { type: "string", enum: ["agent", "rag"] },
          maturity_level: {
            type: "string",
            enum: ["L1", "L2", "L3", "L4"],
            description:
              "客戶 SEO 成熟度等級，用於調整回應深度 / Client SEO maturity level for response depth tuning",
          },
        },
      }),
      responses: {
        "200": jsonContent(
          apiResponse({
            type: "object",
            properties: {
              answer: { type: "string", nullable: true },
              sources: { type: "array", items: { type: "object" } },
              mode: { type: "string" },
              session: ref("SessionDetail"),
            },
          }),
        ),
      },
    },
  },

  // Feedback
  "/api/v1/feedback": {
    post: {
      tags: ["Feedback"],
      summary: "提交搜尋回饋 / Submit search feedback",
      operationId: "submitFeedback",
      requestBody: jsonContent({
        type: "object",
        required: ["query", "qa_id", "feedback"],
        properties: {
          query: { type: "string", minLength: 1, maxLength: 500 },
          qa_id: { type: "string", pattern: "^[0-9a-f]{16}$" },
          feedback: { type: "string", enum: ["helpful", "not_relevant"] },
          feedback_category: {
            type: "string",
            enum: [
              "wrong_answer",
              "missing_info",
              "wrong_source",
              "outdated",
              "too_basic",
              "too_advanced",
            ],
          },
          top_score: { type: "number" },
        },
      }),
      responses: {
        "200": jsonContent(
          apiResponse({
            type: "object",
            properties: {
              recorded: { type: "boolean" },
              qa_id: { type: "string" },
              feedback: { type: "string" },
            },
          }),
        ),
      },
    },
  },

  // Synonyms
  "/api/v1/synonyms": {
    get: {
      tags: ["Synonyms"],
      summary: "列出所有同義詞 / List all synonym entries",
      operationId: "listSynonyms",
      responses: {
        "200": jsonContent(
          apiResponse({
            type: "array",
            items: ref("SynonymEntry"),
          }),
        ),
      },
    },
    post: {
      tags: ["Synonyms"],
      summary: "建立自訂同義詞 / Create custom synonym",
      operationId: "createSynonym",
      requestBody: jsonContent({
        type: "object",
        required: ["term", "synonyms"],
        properties: {
          term: { type: "string", minLength: 1, maxLength: 100 },
          synonyms: {
            type: "array",
            items: { type: "string" },
            minItems: 1,
            maxItems: 50,
          },
        },
      }),
      responses: {
        "201": jsonContent(apiResponse(ref("SynonymEntry")), "Synonym created"),
        "409": jsonContent(
          apiResponse({ type: "null" }),
          "Term already exists",
        ),
      },
    },
  },
  "/api/v1/synonyms/{term}": {
    put: {
      tags: ["Synonyms"],
      summary: "更新同義詞 / Update synonym",
      operationId: "updateSynonym",
      parameters: [
        {
          name: "term",
          in: "path",
          required: true,
          schema: { type: "string" },
        },
      ],
      requestBody: jsonContent({
        type: "object",
        required: ["synonyms"],
        properties: {
          synonyms: {
            type: "array",
            items: { type: "string" },
            minItems: 1,
            maxItems: 50,
          },
        },
      }),
      responses: {
        "200": jsonContent(apiResponse(ref("SynonymEntry"))),
        "404": jsonContent(apiResponse({ type: "null" }), "Term not found"),
      },
    },
    delete: {
      tags: ["Synonyms"],
      summary: "刪除自訂同義詞 / Delete custom synonym",
      operationId: "deleteSynonym",
      parameters: [
        {
          name: "term",
          in: "path",
          required: true,
          schema: { type: "string" },
        },
      ],
      responses: {
        "200": jsonContent(
          apiResponse({
            type: "object",
            properties: {
              deleted: { type: "boolean" },
              term: { type: "string" },
            },
          }),
        ),
        "403": jsonContent(
          apiResponse({ type: "null" }),
          "Cannot delete built-in synonym",
        ),
        "404": jsonContent(apiResponse({ type: "null" }), "Term not found"),
      },
    },
  },

  // Pipeline
  "/api/v1/pipeline/status": {
    get: {
      tags: ["Pipeline"],
      summary: "Pipeline 各步驟完成狀態 / Pipeline step completion status",
      operationId: "getPipelineStatus",
      responses: {
        "200": jsonContent(
          apiResponse({
            type: "object",
            properties: {
              steps: { type: "array", items: ref("PipelineStepStatus") },
            },
          }),
        ),
      },
    },
  },
  "/api/v1/pipeline/meetings": {
    get: {
      tags: ["Pipeline"],
      summary: "列出 Notion 會議 / List Notion meetings",
      operationId: "listMeetings",
      responses: {
        "200": jsonContent(
          apiResponse({
            type: "object",
            properties: {
              items: { type: "array", items: { type: "object" } },
              total: { type: "integer" },
            },
          }),
        ),
      },
    },
  },
  "/api/v1/pipeline/meetings/{id}/preview": {
    get: {
      tags: ["Pipeline"],
      summary: "預覽會議 Markdown / Preview meeting markdown",
      operationId: "previewMeeting",
      parameters: [
        {
          name: "id",
          in: "path",
          required: true,
          schema: { type: "string", format: "uuid" },
        },
      ],
      responses: {
        "200": jsonContent(
          apiResponse({
            type: "object",
            properties: {
              id: { type: "string" },
              title: { type: "string" },
              content: { type: "string" },
              size_bytes: { type: "integer" },
            },
          }),
        ),
        "404": jsonContent(apiResponse({ type: "null" }), "Meeting not found"),
      },
    },
  },
  "/api/v1/pipeline/source-docs": {
    get: {
      tags: ["Pipeline"],
      summary: "列出來源文件 / List source documents",
      operationId: "listSourceDocs",
      parameters: [
        {
          name: "source_type",
          in: "query",
          schema: { type: "string", enum: ["meeting", "article"] },
        },
        { name: "source_collection", in: "query", schema: { type: "string" } },
        {
          name: "keyword",
          in: "query",
          schema: { type: "string", maxLength: 200 },
        },
        {
          name: "is_processed",
          in: "query",
          schema: { type: "string", enum: ["true", "false"] },
        },
        {
          name: "limit",
          in: "query",
          schema: { type: "integer", default: 20 },
        },
        {
          name: "offset",
          in: "query",
          schema: { type: "integer", default: 0 },
        },
      ],
      responses: {
        "200": jsonContent(
          apiResponse({
            type: "object",
            properties: {
              items: { type: "array", items: ref("SourceDocEntry") },
              total: { type: "integer" },
              offset: { type: "integer" },
              limit: { type: "integer" },
            },
          }),
        ),
      },
    },
  },
  "/api/v1/pipeline/source-docs/{collection}/{file}/preview": {
    get: {
      tags: ["Pipeline"],
      summary: "預覽來源文件 / Preview source document",
      operationId: "previewSourceDoc",
      parameters: [
        {
          name: "collection",
          in: "path",
          required: true,
          schema: { type: "string" },
        },
        {
          name: "file",
          in: "path",
          required: true,
          schema: { type: "string" },
        },
      ],
      responses: {
        "200": jsonContent(
          apiResponse({
            type: "object",
            properties: {
              file: { type: "string" },
              title: { type: "string" },
              collection: { type: "string" },
              content: { type: "string" },
              size_bytes: { type: "integer" },
            },
          }),
        ),
        "404": jsonContent(apiResponse({ type: "null" }), "File not found"),
      },
    },
  },
  "/api/v1/pipeline/unprocessed": {
    get: {
      tags: ["Pipeline"],
      summary: "列出未處理的 Markdown 檔案 / List unprocessed markdown files",
      operationId: "listUnprocessed",
      responses: {
        "200": jsonContent(
          apiResponse({
            type: "object",
            properties: {
              items: { type: "array", items: { type: "object" } },
              total: { type: "integer" },
            },
          }),
        ),
      },
    },
  },
  "/api/v1/pipeline/logs": {
    get: {
      tags: ["Pipeline"],
      summary: "取得擷取歷史日誌 / Fetch history logs",
      operationId: "getFetchLogs",
      parameters: [
        {
          name: "limit",
          in: "query",
          schema: { type: "integer", default: 200, maximum: 1000 },
        },
      ],
      responses: {
        "200": jsonContent(
          apiResponse({
            type: "object",
            properties: {
              files: { type: "array", items: { type: "string" } },
              entries: { type: "array", items: { type: "object" } },
              total: { type: "integer" },
            },
          }),
        ),
      },
    },
  },
  "/api/v1/pipeline/fetch": {
    post: {
      tags: ["Pipeline"],
      summary: "觸發 Notion 增量擷取 / Trigger Notion incremental fetch",
      operationId: "triggerFetch",
      requestBody: jsonContent({
        type: "object",
        properties: {
          since: { type: "string", description: "YYYY-MM-DD or Nd format" },
        },
      }),
      responses: {
        "200": jsonContent(apiResponse(ref("PipelineRunResult"))),
      },
    },
  },
  "/api/v1/pipeline/fetch-articles": {
    post: {
      tags: ["Pipeline"],
      summary: "觸發外部文章擷取 / Trigger external article fetch",
      operationId: "triggerFetchArticles",
      responses: {
        "200": jsonContent(
          apiResponse({
            type: "object",
            properties: {
              success: { type: "boolean" },
              results: {
                type: "array",
                items: {
                  type: "object",
                  properties: {
                    source: { type: "string" },
                    success: { type: "boolean" },
                    output: { type: "string" },
                    duration_ms: { type: "integer" },
                  },
                },
              },
            },
          }),
        ),
      },
    },
  },
  "/api/v1/pipeline/extract-qa": {
    post: {
      tags: ["Pipeline"],
      summary: "觸發 QA 萃取 / Trigger QA extraction",
      operationId: "triggerExtractQA",
      requestBody: jsonContent({
        type: "object",
        properties: {
          limit: { type: "integer", minimum: 1 },
          file: { type: "string", description: "Specific .md filename" },
        },
      }),
      responses: {
        "200": jsonContent(apiResponse(ref("PipelineRunResult"))),
      },
    },
  },
  "/api/v1/pipeline/dedupe-classify": {
    post: {
      tags: ["Pipeline"],
      summary: "觸發去重 + 分類 / Trigger dedup + classification",
      operationId: "triggerDedupeClassify",
      requestBody: jsonContent({
        type: "object",
        properties: {
          skip_dedup: { type: "boolean" },
          skip_classify: { type: "boolean" },
          limit: { type: "integer", minimum: 1 },
        },
      }),
      responses: {
        "200": jsonContent(apiResponse(ref("PipelineRunResult"))),
      },
    },
  },
  "/api/v1/pipeline/metrics": {
    post: {
      tags: ["Pipeline"],
      summary: "解析 Google Sheets SEO 指標 / Parse SEO metrics from Google Sheets",
      operationId: "loadMetrics",
      requestBody: jsonContent({
        type: "object",
        required: ["source"],
        properties: {
          source: {
            type: "string",
            format: "uri",
            description: "Google Sheets URL",
          },
          tab: { type: "string", default: "vocus" },
        },
      }),
      responses: {
        "200": jsonContent(apiResponse({ type: "object" })),
      },
    },
  },
  "/api/v1/pipeline/metrics/save": {
    post: {
      tags: ["Pipeline"],
      summary: "儲存指標快照 / Save metrics snapshot",
      operationId: "saveMetricsSnapshot",
      requestBody: jsonContent({
        type: "object",
        required: ["metrics", "source", "tab", "label", "weeks"],
        properties: {
          metrics: { type: "object" },
          source: { type: "string", maxLength: 500 },
          tab: { type: "string", minLength: 1, maxLength: 50 },
          label: { type: "string", maxLength: 60 },
          weeks: { type: "integer", minimum: 1, maximum: 12 },
        },
      }),
      responses: {
        "201": jsonContent(
          apiResponse({
            type: "object",
            properties: {
              id: { type: "string" },
              created_at: { type: "string" },
              label: { type: "string" },
            },
          }),
          "Snapshot saved",
        ),
      },
    },
  },
  "/api/v1/pipeline/metrics/snapshots": {
    get: {
      tags: ["Pipeline"],
      summary: "列出指標快照 / List metrics snapshots",
      operationId: "listSnapshots",
      responses: {
        "200": jsonContent(
          apiResponse({
            type: "object",
            properties: {
              items: { type: "array", items: ref("MetricsSnapshotMeta") },
              total: { type: "integer" },
            },
          }),
        ),
      },
    },
  },
  "/api/v1/pipeline/metrics/snapshots/{id}": {
    delete: {
      tags: ["Pipeline"],
      summary: "刪除指標快照 / Delete metrics snapshot",
      operationId: "deleteSnapshot",
      parameters: [
        {
          name: "id",
          in: "path",
          required: true,
          schema: { type: "string", pattern: "^[0-9]{8}-[0-9]{6}$" },
        },
      ],
      responses: {
        "200": jsonContent(
          apiResponse({
            type: "object",
            properties: {
              deleted: { type: "boolean" },
              id: { type: "string" },
            },
          }),
        ),
        "404": jsonContent(apiResponse({ type: "null" }), "Snapshot not found"),
      },
    },
  },
  "/api/v1/pipeline/llm-usage": {
    get: {
      tags: ["Pipeline"],
      summary: "LLM 用量統計 / LLM usage statistics",
      operationId: "getLlmUsage",
      description:
        "取得指定天數內的 LLM 呼叫統計（按 endpoint + model 分群）。\n\nGet LLM call statistics grouped by endpoint and model for the specified period.",
      parameters: [
        {
          name: "days",
          in: "query",
          schema: { type: "integer", minimum: 1, maximum: 90, default: 30 },
          description: "統計天數（1–90，預設 30）/ Number of days (1–90, default 30)",
        },
      ],
      responses: {
        "200": jsonContent(
          apiResponse({
            type: "object",
            properties: {
              days: { type: "integer" },
              total_calls: { type: "integer" },
              summary: {
                type: "array",
                items: {
                  type: "object",
                  properties: {
                    endpoint: { type: "string" },
                    model: { type: "string" },
                    calls: { type: "integer" },
                    input_tokens: { type: "integer" },
                    output_tokens: { type: "integer" },
                    avg_latency_ms: { type: "number" },
                  },
                },
              },
            },
          }),
        ),
      },
    },
  },
  "/api/v1/pipeline/metrics/trends": {
    get: {
      tags: ["Pipeline"],
      summary: "指標趨勢異常偵測 / Metrics trend anomaly detection",
      operationId: "getMetricsTrends",
      description:
        "分析指標快照的時間序列趨勢，偵測異常（MA 偏離 / 連續下降 / 線性趨勢）。需至少 4 週快照。\n\nAnalyze metrics snapshot timeseries for anomalies (MA deviation / consecutive decline / linear trend). Requires at least 4 weekly snapshots.",
      parameters: [
        {
          name: "metric",
          in: "query",
          schema: { type: "string" },
          description: "篩選特定指標名稱 / Filter by metric name (e.g. 'CTR')",
        },
        {
          name: "weeks",
          in: "query",
          schema: { type: "integer", minimum: 4, maximum: 12, default: 8 },
          description: "分析週數（4–12，預設 8）/ Number of weeks to analyze (4–12, default 8)",
        },
      ],
      responses: {
        "200": jsonContent(
          apiResponse({
            type: "object",
            properties: {
              snapshots_count: { type: "integer" },
              metrics_analyzed: { type: "integer" },
              anomalies: { type: "array", items: { type: "object" } },
            },
          }),
        ),
      },
    },
  },
  "/api/v1/pipeline/crawled-not-indexed": {
    post: {
      tags: ["Pipeline"],
      summary: "分析已爬取未索引的路徑 / Analyze crawled-not-indexed path segments",
      operationId: "analyzeCrawledNotIndexed",
      description:
        "解析並分析 Google Search Console「已爬取但未索引」的資料。支援 URL 模式（Google Sheets）和 raw TSV 模式（直接輸入）。\n\nParse and analyze Google Search Console 'Crawled - currently not indexed' data by path segment. Supports URL mode (Google Sheets) and raw TSV mode (inline data).",
      requestBody: jsonContent({
        type: "object",
        properties: {
          source: {
            type: "string",
            format: "uri",
            description:
              "Google Sheets published CSV URL (mutually exclusive with raw_tsv)",
          },
          raw_tsv: {
            type: "string",
            minLength: 10,
            maxLength: 50000,
            description: "Raw TSV data string (mutually exclusive with source)",
          },
          tab: {
            type: "string",
            default: "vocus",
            description: "Sheet tab name (only used with source)",
          },
        },
      }),
      responses: {
        "200": jsonContent(
          apiResponse({
            type: "object",
            properties: {
              data: {
                type: "object",
                description:
                  "Parsed crawled-not-indexed result (domain, not_indexed_total, paths, etc.)",
              },
              insight: {
                type: "object",
                description:
                  "Analysis insight (overall_severity, domain_change_pct, not_indexed_change_pct, worsening/improving/stable paths, summary_text)",
              },
              markdown: {
                type: "string",
                description: "Formatted Markdown analysis report",
              },
            },
          }),
        ),
        "400": jsonContent(
          apiResponse({ type: "null" }),
          "Invalid request (provide either source or raw_tsv)",
        ),
      },
    },
  },

  // Meeting Prep
  "/api/v1/meeting-prep": {
    get: {
      tags: ["Meeting Prep"],
      summary: "列出所有會議準備報告 / List all meeting prep reports",
      operationId: "listMeetingPrep",
      responses: {
        "200": jsonContent(
          apiResponse({
            type: "object",
            properties: {
              items: {
                type: "array",
                items: {
                  type: "object",
                  properties: {
                    date: { type: "string" },
                    filename: { type: "string" },
                    size_bytes: { type: "integer" },
                    meta: { type: "object", nullable: true, description: "Parsed meeting prep metadata (scores, alert_down_count, etc.)" },
                  },
                },
              },
              total: { type: "integer" },
            },
          }),
        ),
      },
    },
  },
  "/api/v1/meeting-prep/maturity-trend": {
    get: {
      tags: ["Meeting Prep"],
      summary: "SEO 成熟度趨勢 / SEO maturity trend timeseries",
      operationId: "getMeetingPrepMaturityTrend",
      description:
        "從歷次會議準備報告中萃取成熟度評分，回傳時間序列與趨勢摘要。\n\nExtract maturity scores from meeting prep reports and return timeseries with trend summary.",
      responses: {
        "200": jsonContent(
          apiResponse({
            type: "object",
            properties: {
              data_points: {
                type: "array",
                items: {
                  type: "object",
                  properties: {
                    date: { type: "string", format: "date" },
                    maturity: { type: "object" },
                    eeat: { type: "object" },
                    alert_down_count: { type: "integer" },
                  },
                },
              },
              summary: {
                type: "object",
                nullable: true,
                properties: {
                  improved: { type: "array", items: { type: "string" } },
                  stagnant: { type: "array", items: { type: "string" } },
                  regressed: { type: "array", items: { type: "string" } },
                },
              },
              total: { type: "integer" },
            },
          }),
        ),
      },
    },
  },
  "/api/v1/meeting-prep/{date}": {
    get: {
      tags: ["Meeting Prep"],
      summary: "取得單篇會議準備報告 / Get meeting prep report by date",
      operationId: "getMeetingPrep",
      parameters: [
        {
          name: "date",
          in: "path",
          required: true,
          schema: { type: "string", pattern: "^\\d{8}(?:_[0-9a-f]{8})?$" },
          description: "YYYYMMDD 或 YYYYMMDD_hash8 格式 / YYYYMMDD or YYYYMMDD_hash8",
        },
      ],
      responses: {
        "200": jsonContent(
          apiResponse({
            type: "object",
            properties: {
              date: { type: "string" },
              filename: { type: "string" },
              content: { type: "string" },
              size_bytes: { type: "integer" },
              meta: { type: "object", nullable: true, description: "Parsed meeting prep metadata (scores, alert_down_count, etc.)" },
            },
          }),
        ),
        "404": jsonContent(apiResponse({ type: "null" }), "Meeting prep report not found"),
      },
    },
  },
};

export function buildOpenAPISpec(): OpenAPISpec {
  return {
    openapi: "3.1.0",
    info: {
      title: "SEO Knowledge Insight API",
      version: API_VERSION,
      description:
        "具備 RAG 對話、語意搜尋、週報生成與 Pipeline 管理功能的 SEO 知識庫 API。\n\nSEO knowledge base API with RAG chat, search, reports, and pipeline management.",
    },
    servers: [
      { url: "http://localhost:8002", description: "本地開發環境 / Local development" },
      {
        url: "https://pu4fsreadnjcsqnfuqpyzndm4m0nctua.lambda-url.ap-northeast-1.on.aws",
        description: "正式環境 (Lambda) / Production (Lambda)",
      },
    ],
    tags: [
      { name: "Health", description: "伺服器健康檢查\n\nServer health check" },
      { name: "QA", description: "QA 知識庫 CRUD 操作\n\nQA knowledge base CRUD" },
      { name: "Search", description: "語意搜尋 / 關鍵字搜尋\n\nSemantic / keyword search" },
      { name: "Chat", description: "RAG 對話與 Agent 模式\n\nRAG chat and agent mode" },
      { name: "Reports", description: "SEO 週報管理\n\nWeekly SEO reports" },
      { name: "Sessions", description: "多輪對話管理\n\nMulti-turn chat sessions" },
      { name: "Feedback", description: "搜尋相關性回饋\n\nSearch relevance feedback" },
      { name: "Synonyms", description: "同義詞管理\n\nSynonym management" },
      { name: "Pipeline", description: "ETL Pipeline 管理\n\nETL pipeline management" },
      { name: "Meeting Prep", description: "顧問會議準備報告\n\nConsulting meeting preparation reports" },
    ],
    paths,
    components: {
      schemas,
      securitySchemes: {
        apiKey: {
          type: "apiKey",
          in: "header",
          name: "X-API-Key",
          description: "API 認證金鑰（/health 不需要）\n\nAPI key for authentication (not required for /health)",
        },
      },
    },
    security: [{ apiKey: [] }],
  };
}
