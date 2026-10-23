/**
 * Store 層錯誤型別與 HTTP 對應。
 *
 * 路由不需要逐一 try/catch：未攔截的錯誤進 middleware/error-handler.ts，
 * 由 storeErrorResponse() 轉成 503／504／410；其餘錯誤維持 500。
 * 訊息只用固定代碼，不帶 DB 細節或憑證。
 */

export class DbUnavailableError extends Error {
  readonly status = 503 as const;
  readonly code = "db_unavailable" as const;
  constructor(reason: string, options?: { cause?: unknown }) {
    super(`db_unavailable: ${reason}`, options);
    this.name = "DbUnavailableError";
  }
}

export class DbTimeoutError extends Error {
  readonly status = 504 as const;
  readonly code = "db_timeout" as const;
  constructor(options?: { cause?: unknown }) {
    super("db_timeout", options);
    this.name = "DbTimeoutError";
  }
}

/** rag-api 不提供的能力（週報、會議準備改走 warehouse-api /internal/app）。 */
export class NotAvailableInRagApiError extends Error {
  readonly status = 410 as const;
  readonly code = "not_available_in_rag_api" as const;
  constructor(feature: string) {
    super(`not_available_in_rag_api: ${feature}`);
    this.name = "NotAvailableInRagApiError";
  }
}

export type StoreError = DbUnavailableError | DbTimeoutError | NotAvailableInRagApiError;

export function isStoreError(err: unknown): err is StoreError {
  return (
    err instanceof DbUnavailableError ||
    err instanceof DbTimeoutError ||
    err instanceof NotAvailableInRagApiError
  );
}

/** 給路由與 error handler 用：store 錯誤回 { status, code }，其他錯誤回 null。 */
export function storeErrorResponse(
  err: unknown,
): { readonly status: 503 | 504 | 410; readonly code: string } | null {
  return isStoreError(err) ? { status: err.status, code: err.code } : null;
}
