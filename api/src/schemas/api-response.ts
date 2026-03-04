import { v4 as uuidv4 } from "uuid";

const API_VERSION = "1.0";

export interface ApiResponseMeta {
  readonly request_id: string;
  readonly version: string;
}

export interface ApiResponse<T> {
  readonly data: T | null;
  readonly error: string | null;
  readonly meta: ApiResponseMeta;
}

export function ok<T>(data: T): ApiResponse<T> {
  return {
    data,
    error: null,
    meta: { request_id: uuidv4(), version: API_VERSION },
  };
}

export function fail(message: string): ApiResponse<null> {
  return {
    data: null,
    error: message,
    meta: { request_id: uuidv4(), version: API_VERSION },
  };
}
