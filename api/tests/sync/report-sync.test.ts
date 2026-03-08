import { describe, it, expect, vi, beforeEach } from "vitest";
import { ReportSyncer } from "../../src/sync/report-sync.js";

// Mock dependencies
vi.mock("../../src/utils/report-file.js", () => ({
  listReportFiles: vi.fn(),
  parseReportMeta: vi.fn(),
  REPORT_PATTERN: /^report_(\d{8}(?:_[0-9a-f]{8})?)\.md$/,
  REPORT_META_RE: /<!-- report_meta ({[\s\S]*?}) -->/,
}));

vi.mock("node:fs", () => ({
  readFileSync: vi.fn(() => "# Report content"),
  existsSync: vi.fn(() => true),
  readdirSync: vi.fn(() => []),
  statSync: vi.fn(() => ({ size: 100, mtimeMs: Date.now() })),
  openSync: vi.fn(() => 3),
  readSync: vi.fn(),
  closeSync: vi.fn(),
}));

import { listReportFiles, parseReportMeta } from "../../src/utils/report-file.js";

const mockList = vi.fn();
const mockSave = vi.fn();

function createSyncer(): ReportSyncer {
  const fakeStore = { list: mockList, save: mockSave } as any;
  return new ReportSyncer(fakeStore);
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("ReportSyncer.computeDiff", () => {
  it("identifies local-only, remote-only, and both items", async () => {
    vi.mocked(listReportFiles).mockReturnValue([
      { date: "20260305", filename: "report_20260305.md", size_bytes: 100 },
      { date: "20260306_abc12345", filename: "report_20260306_abc12345.md", size_bytes: 200 },
    ]);
    mockList.mockResolvedValue([
      { date: "20260305", filename: "report_20260305.md", size_bytes: 100 },
      { date: "20260307_def67890", filename: "report_20260307_def67890.md", size_bytes: 300 },
    ]);

    const syncer = createSyncer();
    const diff = await syncer.computeDiff();

    expect(diff.localOnly).toHaveLength(1);
    expect(diff.localOnly[0]!.key).toBe("20260306_abc12345");

    expect(diff.remoteOnly).toHaveLength(1);
    expect(diff.remoteOnly[0]!.key).toBe("20260307_def67890");

    expect(diff.both).toHaveLength(1);
    expect(diff.both[0]!.key).toBe("20260305");
  });

  it("handles empty local and remote", async () => {
    vi.mocked(listReportFiles).mockReturnValue([]);
    mockList.mockResolvedValue([]);

    const syncer = createSyncer();
    const diff = await syncer.computeDiff();

    expect(diff.localOnly).toHaveLength(0);
    expect(diff.remoteOnly).toHaveLength(0);
    expect(diff.both).toHaveLength(0);
  });

  it("all local are also remote (fully synced)", async () => {
    vi.mocked(listReportFiles).mockReturnValue([
      { date: "20260305", filename: "report_20260305.md", size_bytes: 100 },
    ]);
    mockList.mockResolvedValue([
      { date: "20260305", filename: "report_20260305.md", size_bytes: 100 },
    ]);

    const syncer = createSyncer();
    const diff = await syncer.computeDiff();

    expect(diff.localOnly).toHaveLength(0);
    expect(diff.remoteOnly).toHaveLength(0);
    expect(diff.both).toHaveLength(1);
  });
});

describe("ReportSyncer.upload", () => {
  it("uploads local-only items (default: skip existing)", async () => {
    vi.mocked(listReportFiles).mockReturnValue([
      { date: "20260305", filename: "report_20260305.md", size_bytes: 100 },
      { date: "20260306_abc12345", filename: "report_20260306_abc12345.md", size_bytes: 200 },
    ]);
    mockList.mockResolvedValue([
      { date: "20260305", filename: "report_20260305.md", size_bytes: 100 },
    ]);
    mockSave.mockResolvedValue(undefined);
    vi.mocked(parseReportMeta).mockReturnValue(undefined);

    const syncer = createSyncer();
    const result = await syncer.upload({ dryRun: false, force: false });

    expect(result.uploaded).toBe(1);
    expect(result.skipped).toBe(1);
    expect(result.errors).toHaveLength(0);
    expect(mockSave).toHaveBeenCalledTimes(1);
    expect(mockSave).toHaveBeenCalledWith("20260306_abc12345", "# Report content", undefined);
  });

  it("uploads all items when force=true", async () => {
    vi.mocked(listReportFiles).mockReturnValue([
      { date: "20260305", filename: "report_20260305.md", size_bytes: 100 },
      { date: "20260306_abc12345", filename: "report_20260306_abc12345.md", size_bytes: 200 },
    ]);
    mockList.mockResolvedValue([
      { date: "20260305", filename: "report_20260305.md", size_bytes: 100 },
    ]);
    mockSave.mockResolvedValue(undefined);
    vi.mocked(parseReportMeta).mockReturnValue(undefined);

    const syncer = createSyncer();
    const result = await syncer.upload({ dryRun: false, force: true });

    expect(result.uploaded).toBe(2);
    expect(result.skipped).toBe(0);
    expect(mockSave).toHaveBeenCalledTimes(2);
  });

  it("returns zero uploads on dry-run", async () => {
    vi.mocked(listReportFiles).mockReturnValue([
      { date: "20260306_abc12345", filename: "report_20260306_abc12345.md", size_bytes: 200 },
    ]);
    mockList.mockResolvedValue([]);

    const syncer = createSyncer();
    const result = await syncer.upload({ dryRun: true, force: false });

    expect(result.uploaded).toBe(0);
    expect(mockSave).not.toHaveBeenCalled();
  });

  it("collects errors without stopping", async () => {
    vi.mocked(listReportFiles).mockReturnValue([
      { date: "20260305", filename: "report_20260305.md", size_bytes: 100 },
      { date: "20260306", filename: "report_20260306.md", size_bytes: 200 },
    ]);
    mockList.mockResolvedValue([]);
    mockSave
      .mockRejectedValueOnce(new Error("Network error"))
      .mockResolvedValueOnce(undefined);
    vi.mocked(parseReportMeta).mockReturnValue(undefined);

    const syncer = createSyncer();
    const result = await syncer.upload({ dryRun: false, force: false });

    expect(result.uploaded).toBe(1);
    expect(result.errors).toHaveLength(1);
    expect(result.errors[0]).toContain("Network error");
  });

  it("returns zero when nothing to upload", async () => {
    vi.mocked(listReportFiles).mockReturnValue([
      { date: "20260305", filename: "report_20260305.md", size_bytes: 100 },
    ]);
    mockList.mockResolvedValue([
      { date: "20260305", filename: "report_20260305.md", size_bytes: 100 },
    ]);

    const syncer = createSyncer();
    const result = await syncer.upload({ dryRun: false, force: false });

    expect(result.uploaded).toBe(0);
    expect(result.skipped).toBe(1);
    expect(mockSave).not.toHaveBeenCalled();
  });
});
