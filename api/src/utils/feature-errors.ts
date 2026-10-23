/**
 * 501 Not Implemented 類錯誤：功能在這個部署形態不提供，而不是壞掉。
 *
 *   - llm_disabled：線上沒有 OPENAI_API_KEY 也沒有 LLM_BASE_URL（2026-10-23 裁決：線上先不開 LLM）
 *   - run_locally：pipeline 觸發與本機檔案依賴的路由，rag-api 不執行（改用 make pipeline）
 *
 * 回應沿用 { data, error, meta } 信封，多一個給人看的 message；前端以 error 代碼分流。
 */

import { fail, type ApiResponse } from "../schemas/api-response.js";

export type FeatureUnavailableCode = "llm_disabled" | "run_locally";

export const FEATURE_MESSAGES: Readonly<Record<FeatureUnavailableCode, string>> = {
  llm_disabled: "線上未啟用 LLM，請在本機模式執行",
  run_locally: "此流程在本機執行，請用 make pipeline",
};

export class FeatureUnavailableError extends Error {
  readonly status = 501 as const;
  readonly code: FeatureUnavailableCode;

  constructor(code: FeatureUnavailableCode) {
    super(`${code}: ${FEATURE_MESSAGES[code]}`);
    this.name = "FeatureUnavailableError";
    this.code = code;
  }
}

export function isFeatureUnavailableError(err: unknown): err is FeatureUnavailableError {
  return err instanceof FeatureUnavailableError;
}

export interface FeatureUnavailableBody extends ApiResponse<null> {
  readonly message: string;
}

export function featureUnavailableBody(code: FeatureUnavailableCode): FeatureUnavailableBody {
  return { ...fail(code), message: FEATURE_MESSAGES[code] };
}
