/**
 * OpenAI embedding wrapper — returns L2-normalized Float32Array.
 */

import OpenAI from "openai";
import { config } from "../config.js";
import { normalizeL2 } from "../utils/cosine-similarity.js";

let client: OpenAI | null = null;

function getClient(): OpenAI {
  if (!client) {
    client = new OpenAI({ apiKey: config.OPENAI_API_KEY });
  }
  return client;
}

export async function getEmbedding(text: string): Promise<Float32Array> {
  const resp = await getClient().embeddings.create({
    model: config.OPENAI_EMBEDDING_MODEL,
    input: text.trim(),
  });
  const vec = new Float32Array(resp.data[0]!.embedding);
  return normalizeL2(vec);
}
