import { beforeEach, describe, expect, it } from "vitest";
import { recordFeedbackPg, recordMissPg } from "../../src/store/pg-learning-store.js";
import { pgAvailable, usePgFixture } from "../pg/pg-fixture.js";

const fx = usePgFixture("learn");

describe.skipIf(!pgAvailable)("pg-learning-store against app_learning (warehouse_rag)", () => {
  beforeEach(() => fx.activate());

  it("inserts feedback and miss rows that satisfy the type CHECK", async () => {
    await recordFeedbackPg({ query: "LCP", qa_id: "0000000000000001", feedback: "not_relevant", top_score: 0.42 });
    await recordFeedbackPg({ query: "CLS", qa_id: "0000000000000002", feedback: "helpful" });
    await recordMissPg({ query: "unknown topic", top_score: 0.05, context: "search" });
    const { rows } = await fx
      .admin()
      .query("SELECT type, query, qa_id, feedback, top_score, context FROM app_learning ORDER BY id");
    expect(rows).toEqual([
      { type: "feedback", query: "LCP", qa_id: "0000000000000001", feedback: "not_relevant", top_score: 0.42, context: null },
      { type: "feedback", query: "CLS", qa_id: "0000000000000002", feedback: "helpful", top_score: null, context: null },
      { type: "miss", query: "unknown topic", qa_id: null, feedback: null, top_score: 0.05, context: "search" },
    ]);
  });
});
