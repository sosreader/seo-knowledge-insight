/**
 * OpenAPI 3.1 spec for SEO Knowledge Insight API.
 *
 * Hand-maintained to avoid zod-openapi compatibility issues with Zod v4.
 * Each path matches the routes in src/routes/*.ts.
 */

const API_VERSION = "3.4.0";

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
        description: "Chat mode (auto-detected if omitted)",
      },
      maturity_level: {
        type: "string",
        enum: ["L1", "L2", "L3", "L4"],
        description: "Client SEO maturity level for response depth tuning",
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
      summary: "Health check",
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
      summary: "List QA items",
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
          description: "Filter by maturity level",
        },
        {
          name: "sort_by",
          in: "query",
          schema: { type: "string", enum: ["source_date"] },
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
      summary: "List all categories",
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
      summary: "List all source collections",
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
      summary: "Get QA item by ID",
      operationId: "getQAById",
      parameters: [
        {
          name: "item_id",
          in: "path",
          required: true,
          schema: { type: "string" },
          description: "Hex stable_id (16 chars) or integer seq",
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
      summary: "Search QA knowledge base",
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
              description: "Boost results matching this maturity level",
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
      summary: "RAG chat (single-turn or agent mode)",
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

  // Reports
  "/api/v1/reports": {
    get: {
      tags: ["Reports"],
      summary: "List all weekly reports",
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
      summary: "Get report by date",
      operationId: "getReport",
      parameters: [
        {
          name: "date",
          in: "path",
          required: true,
          schema: { type: "string", pattern: "^\\d{8}(?:_[0-9a-f]{8})?$" },
          description: "YYYYMMDD or YYYYMMDD_hash8",
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
      summary: "Generate weekly report",
      operationId: "generateReport",
      description:
        "Supports three modes: local (snapshot_id), OpenAI (snapshot_id + use_openai), legacy (metrics_url)",
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
      summary: "List chat sessions",
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
      summary: "Create a new chat session",
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
      summary: "Get session with messages",
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
      summary: "Delete a session",
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
      summary: "Send message in session",
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
              "Client maturity level (persisted to session on first use)",
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
      summary: "Submit search feedback",
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
      summary: "List all synonym entries",
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
      summary: "Create custom synonym",
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
      summary: "Update synonym",
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
      summary: "Delete custom synonym",
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
      summary: "Pipeline step completion status",
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
      summary: "List Notion meetings",
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
      summary: "Preview meeting markdown",
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
      summary: "List source documents",
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
      summary: "Preview source document",
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
      summary: "List unprocessed markdown files",
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
      summary: "Fetch history logs",
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
      summary: "Trigger Notion incremental fetch",
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
      summary:
        "Trigger external article fetch (Medium + iThome + Google Cases)",
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
      summary: "Trigger QA extraction",
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
      summary: "Trigger dedup + classification",
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
      summary: "Parse SEO metrics from Google Sheets",
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
      summary: "Save metrics snapshot",
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
      summary: "List metrics snapshots",
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
      summary: "Delete metrics snapshot",
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
  "/api/v1/pipeline/crawled-not-indexed": {
    post: {
      tags: ["Pipeline"],
      summary: "Analyze crawled-not-indexed path segments",
      operationId: "analyzeCrawledNotIndexed",
      description:
        "Parse and analyze Google Search Console 'Crawled - currently not indexed' data by path segment. Supports URL mode (Google Sheets) and raw TSV mode (inline data).",
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
};

export function buildOpenAPISpec(): OpenAPISpec {
  return {
    openapi: "3.1.0",
    info: {
      title: "SEO Knowledge Insight API",
      version: API_VERSION,
      description:
        "SEO knowledge base API with RAG chat, search, reports, and pipeline management.",
    },
    servers: [
      { url: "http://localhost:8002", description: "Local development" },
      {
        url: "https://pu4fsreadnjcsqnfuqpyzndm4m0nctua.lambda-url.ap-northeast-1.on.aws",
        description: "Production (Lambda)",
      },
    ],
    tags: [
      { name: "Health", description: "Server health check" },
      { name: "QA", description: "QA knowledge base CRUD" },
      { name: "Search", description: "Semantic / keyword search" },
      { name: "Chat", description: "RAG chat and agent mode" },
      { name: "Reports", description: "Weekly SEO reports" },
      { name: "Sessions", description: "Multi-turn chat sessions" },
      { name: "Feedback", description: "Search relevance feedback" },
      { name: "Synonyms", description: "Synonym management" },
      { name: "Pipeline", description: "ETL pipeline management" },
    ],
    paths,
    components: {
      schemas,
      securitySchemes: {
        apiKey: {
          type: "apiKey",
          in: "header",
          name: "X-API-Key",
          description: "API key for authentication (not required for /health)",
        },
      },
    },
    security: [{ apiKey: [] }],
  };
}
