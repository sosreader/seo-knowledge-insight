import { z } from "zod";

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export const sessionIdSchema = z.string().regex(UUID_RE, "Invalid session ID format");

export const createSessionSchema = z.object({
  title: z.string().max(100).optional(),
});

export const sendMessageSchema = z.object({
  message: z.string().min(1).max(2000),
  mode: z.enum(["agent", "rag"]).optional(),
});

export const sessionListParamsSchema = z.object({
  limit: z.coerce.number().int().min(1).max(100).default(20),
  offset: z.coerce.number().int().min(0).default(0),
});

export interface SessionMessageOut {
  readonly role: string;
  readonly content: string;
  readonly sources: readonly Record<string, unknown>[];
  readonly created_at: string;
  readonly metadata?: Record<string, unknown>;
}

export interface SessionSummaryOut {
  readonly id: string;
  readonly title: string;
  readonly created_at: string;
  readonly updated_at: string;
}

export interface SessionDetailOut extends SessionSummaryOut {
  readonly messages: readonly SessionMessageOut[];
}
