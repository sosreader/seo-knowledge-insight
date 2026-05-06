import { describe, it, expect } from "vitest";
import { parseMeetingPrepMeta } from "../../src/utils/meeting-prep-file.js";

describe("parseMeetingPrepMeta — JSON code block format", () => {
  it("parses canonical schema with scores.eeat + scores.maturity", () => {
    const content = `
some content here
\`\`\`json
{
  "meeting_prep_meta": {
    "date": "20260427_50472c79",
    "generation_mode": "claude-code-semantic",
    "alert_down_count": 15,
    "question_count": 18,
    "scores": {
      "eeat": {
        "experience": 3,
        "expertise": 3,
        "authoritativeness": 2,
        "trustworthiness": 3
      },
      "maturity": {
        "strategy": "L2",
        "process": "L3",
        "keywords": "L3",
        "metrics": "L3"
      }
    }
  }
}
\`\`\`
`;
    const meta = parseMeetingPrepMeta(content);
    expect(meta).toBeDefined();
    expect(meta!.date).toBe("20260427_50472c79");
    expect(meta!.scores.eeat.authoritativeness).toBe(2);
    expect(meta!.scores.maturity.process).toBe("L3");
    expect(meta!.alert_down_count).toBe(15);
    expect(meta!.question_count).toBe(18);
  });

  it("falls back to per-dimension shorthand (eeat_e/ex/a/t + maturity flat)", () => {
    const content = `
\`\`\`json
{
  "meeting_prep_meta": {
    "date": "20260413",
    "generation_mode": "claude-code-semantic",
    "alert_down_count": 33,
    "s9_questions": 15,
    "eeat_avg": 2.75,
    "eeat_e": 3,
    "eeat_ex": 3,
    "eeat_a": 2,
    "eeat_t": 3,
    "maturity": {
      "strategy": "L2",
      "process": "L2",
      "keywords": "L3",
      "metrics": "L2"
    }
  }
}
\`\`\`
`;
    const meta = parseMeetingPrepMeta(content);
    expect(meta).toBeDefined();
    expect(meta!.scores.eeat).toEqual({
      experience: 3,
      expertise: 3,
      authoritativeness: 2,
      trustworthiness: 3,
    });
    expect(meta!.scores.maturity.metrics).toBe("L2");
    expect(meta!.question_count).toBe(15); // s9_questions fallback
  });

  it("derives source_report_date from source_report filename", () => {
    const content = `
\`\`\`json
{
  "meeting_prep_meta": {
    "date": "20260427_50472c79",
    "generation_mode": "claude-code-semantic",
    "alert_down_count": 15,
    "s9_questions": 15,
    "source_report": "report_20260427_11af1555.md",
    "scores": {
      "eeat": { "experience": 3, "expertise": 3, "authoritativeness": 2, "trustworthiness": 3 },
      "maturity": { "strategy": "L2", "process": "L3", "keywords": "L3", "metrics": "L3" }
    }
  }
}
\`\`\`
`;
    const meta = parseMeetingPrepMeta(content);
    expect(meta?.source_report_date).toBe("20260427");
  });

  it("returns undefined when meta block is missing", () => {
    const meta = parseMeetingPrepMeta("# Just markdown, no meta");
    expect(meta).toBeUndefined();
  });

  it("returns undefined when JSON is malformed", () => {
    const content = "```json\n{\"meeting_prep_meta\": {\"date\": malformed}}\n```";
    const meta = parseMeetingPrepMeta(content);
    expect(meta).toBeUndefined();
  });

  it("returns undefined when date field is missing", () => {
    const content = `
\`\`\`json
{
  "meeting_prep_meta": {
    "generation_mode": "claude-code-semantic"
  }
}
\`\`\`
`;
    const meta = parseMeetingPrepMeta(content);
    expect(meta).toBeUndefined();
  });

  it("falls back to L1 defaults when maturity is absent", () => {
    const content = `
\`\`\`json
{
  "meeting_prep_meta": {
    "date": "20260101_aabbccdd",
    "generation_mode": "test",
    "alert_down_count": 0,
    "question_count": 0
  }
}
\`\`\`
`;
    const meta = parseMeetingPrepMeta(content);
    expect(meta?.scores.maturity).toEqual({
      strategy: "L1",
      process: "L1",
      keywords: "L1",
      metrics: "L1",
    });
  });
});

describe("parseMeetingPrepMeta — legacy HTML comment format", () => {
  it("parses HTML comment when JSON code block is absent", () => {
    const content = `
some content
<!-- meeting_prep_meta {"date":"20260101","generation_mode":"legacy","alert_down_count":5,"question_count":10,"scores":{"eeat":{"experience":2,"expertise":2,"authoritativeness":2,"trustworthiness":2},"maturity":{"strategy":"L1","process":"L1","keywords":"L1","metrics":"L1"}}} -->
`;
    const meta = parseMeetingPrepMeta(content);
    expect(meta?.date).toBe("20260101");
    expect(meta?.generation_mode).toBe("legacy");
  });
});
