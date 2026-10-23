import { v4 as uuidv4 } from "uuid";

const API_VERSION = "1.0";

export interface ApiResponseMeta {
  readonly request_id: string;
  readonly version: string;
  readonly [extra: string]: unknown;
}

export interface ApiResponse<T> {
  readonly data: T | null;
  readonly error: string | null;
  readonly meta: ApiResponseMeta;
}

/** extraMeta：路由附加的回應層資訊（例如 search 的 mode、llm_disabled），不可覆寫 request_id／version。 */
export function ok<T>(data: T, extraMeta: Readonly<Record<string, unknown>> = {}): ApiResponse<T> {
  return {
    data,
    error: null,
    meta: { ...extraMeta, request_id: uuidv4(), version: API_VERSION },
  };
}

export function fail(message: string): ApiResponse<null> {
  return {
    data: null,
    error: message,
    meta: { request_id: uuidv4(), version: API_VERSION },
  };
}
