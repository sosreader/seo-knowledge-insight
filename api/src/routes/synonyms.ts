import { Hono } from "hono";
import { ok, fail } from "../schemas/api-response.js";
import { createSynonymSchema, updateSynonymSchema } from "../schemas/synonyms.js";
import { synonymsStore } from "../store/synonyms-store.js";

export const synonymsRoute = new Hono();

// GET /api/v1/synonyms — list all terms (static + custom, with source annotation)
synonymsRoute.get("/", (c) => {
  const items = synonymsStore.list();
  return c.json(ok(items));
});

// POST /api/v1/synonyms — create a new custom term
synonymsRoute.post("/", async (c) => {
  const body = await c.req.json().catch(() => ({}));
  const parsed = createSynonymSchema.safeParse(body);

  if (!parsed.success) {
    return c.json(fail("Invalid request body"), 400);
  }

  const { term, synonyms } = parsed.data;

  // Reject if term already exists in custom layer
  if (synonymsStore.isCustom(term)) {
    return c.json(fail(`Term '${term}' already exists. Use PUT to update.`), 409);
  }

  const item = await synonymsStore.create(term, synonyms);
  return c.json(ok(item), 201);
});

// PUT /api/v1/synonyms/:term — overwrite synonyms (works for static or custom)
synonymsRoute.put("/:term", async (c) => {
  const term = decodeURIComponent(c.req.param("term"));

  const body = await c.req.json().catch(() => ({}));
  const parsed = updateSynonymSchema.safeParse(body);

  if (!parsed.success) {
    return c.json(fail("Invalid request body"), 400);
  }

  // Term must exist (static or custom)
  const existing = synonymsStore.get(term);
  if (!existing) {
    return c.json(fail(`Term '${term}' not found`), 404);
  }

  const { synonyms } = parsed.data;
  const item = await synonymsStore.update(term, synonyms);
  return c.json(ok(item));
});

// DELETE /api/v1/synonyms/:term — remove custom override
// Static-only terms return 403; non-existent terms return 404
synonymsRoute.delete("/:term", async (c) => {
  const term = decodeURIComponent(c.req.param("term"));

  const existing = synonymsStore.get(term);
  if (!existing) {
    return c.json(fail(`Term '${term}' not found`), 404);
  }

  // Cannot delete static-only term
  if (!synonymsStore.isCustom(term)) {
    return c.json(fail(`Term '${term}' is a built-in entry and cannot be deleted`), 403);
  }

  await synonymsStore.delete(term);
  return c.json(ok({ deleted: true, term }));
});
