import { describe, it, expect, vi, beforeEach } from "vitest";
import { MeetingPrepSyncer } from "../../src/sync/meeting-prep-sync.js";

// Mock dependencies
vi.mock("../../src/utils/meeting-prep-file.js", () => ({
  listMeetingPrepFiles: vi.fn(),
  readMeetingPrepFile: vi.fn(),
  parseMeetingPrepMeta: vi.fn(),
  MEETING_PREP_PATTERN: /^meeting_prep_(\d{8})_([0-9a-f]{8})\.md$/,
}));

import {
  listMeetingPrepFiles,
  readMeetingPrepFile,
} from "../../src/utils/meeting-prep-file.js";

const mockList = vi.fn();
const mockSave = vi.fn();

function createSyncer(): MeetingPrepSyncer {
  const fakeStore = { list: mockList, save: mockSave } as never;
  return new MeetingPrepSyncer(fakeStore);
}

function makeFile(dateKey: string, mtime = 1700000000000) {
  const [date, hash] = dateKey.split("_");
  return {
    dateKey,
    filename: `meeting_prep_${date}_${hash}.md`,
    filepath: `/tmp/meeting_prep_${date}_${hash}.md`,
    size_bytes: 1234,
    mtime,
  };
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("MeetingPrepSyncer.computeDiff", () => {
  it("identifies local-only, remote-only, and both items", async () => {
    vi.mocked(listMeetingPrepFiles).mockReturnValue([
      makeFile("20260413_9aeb7339"),
      makeFile("20260427_50472c79"),
    ]);
    mockList.mockResolvedValue([
      { date: "20260413_9aeb7339", maturity: {} as never, eeat: {} as never } as never,
      { date: "20260420_aabbccdd", maturity: {} as never, eeat: {} as never } as never,
    ]);

    const syncer = createSyncer();
    const diff = await syncer.computeDiff();

    expect(diff.localOnly).toHaveLength(1);
    expect(diff.localOnly[0]!.key).toBe("20260427_50472c79");

    expect(diff.remoteOnly).toHaveLength(1);
    expect(diff.remoteOnly[0]!.key).toBe("20260420_aabbccdd");

    expect(diff.both).toHaveLength(1);
    expect(diff.both[0]!.key).toBe("20260413_9aeb7339");
  });

  it("handles empty local and remote", async () => {
    vi.mocked(listMeetingPrepFiles).mockReturnValue([]);
    mockList.mockResolvedValue([]);

    const syncer = createSyncer();
    const diff = await syncer.computeDiff();

    expect(diff.localOnly).toHaveLength(0);
    expect(diff.remoteOnly).toHaveLength(0);
    expect(diff.both).toHaveLength(0);
  });

  it("all local already in remote (fully synced)", async () => {
    vi.mocked(listMeetingPrepFiles).mockReturnValue([
      makeFile("20260413_9aeb7339"),
    ]);
    mockList.mockResolvedValue([
      { date: "20260413_9aeb7339" } as never,
    ]);

    const syncer = createSyncer();
    const diff = await syncer.computeDiff();

    expect(diff.localOnly).toHaveLength(0);
    expect(diff.both).toHaveLength(1);
  });
});

describe("MeetingPrepSyncer.upload", () => {
  it("uploads local-only items (default: skip existing)", async () => {
    vi.mocked(listMeetingPrepFiles).mockReturnValue([
      makeFile("20260413_9aeb7339"),
      makeFile("20260427_50472c79"),
    ]);
    mockList.mockResolvedValue([
      { date: "20260413_9aeb7339" } as never,
    ]);
    vi.mocked(readMeetingPrepFile).mockReturnValue({
      content: "# Meeting prep",
      meta: undefined,
    });
    mockSave.mockResolvedValue(undefined);

    const syncer = createSyncer();
    const result = await syncer.upload({ dryRun: false, force: false });

    expect(result.uploaded).toBe(1);
    expect(result.skipped).toBe(1);
    expect(result.errors).toHaveLength(0);
    expect(mockSave).toHaveBeenCalledTimes(1);
    expect(mockSave).toHaveBeenCalledWith(
      "20260427_50472c79",
      "meeting_prep_20260427_50472c79.md",
      "# Meeting prep",
      undefined,
    );
  });

  it("uploads all items when force=true", async () => {
    vi.mocked(listMeetingPrepFiles).mockReturnValue([
      makeFile("20260413_9aeb7339"),
      makeFile("20260427_50472c79"),
    ]);
    mockList.mockResolvedValue([
      { date: "20260413_9aeb7339" } as never,
    ]);
    vi.mocked(readMeetingPrepFile).mockReturnValue({
      content: "# Meeting prep",
      meta: undefined,
    });
    mockSave.mockResolvedValue(undefined);

    const syncer = createSyncer();
    const result = await syncer.upload({ dryRun: false, force: true });

    expect(result.uploaded).toBe(2);
    expect(result.skipped).toBe(0);
    expect(mockSave).toHaveBeenCalledTimes(2);
  });

  it("returns zero uploads on dry-run", async () => {
    vi.mocked(listMeetingPrepFiles).mockReturnValue([
      makeFile("20260427_50472c79"),
    ]);
    mockList.mockResolvedValue([]);

    const syncer = createSyncer();
    const result = await syncer.upload({ dryRun: true, force: false });

    expect(result.uploaded).toBe(0);
    expect(mockSave).not.toHaveBeenCalled();
  });

  it("collects errors without stopping", async () => {
    vi.mocked(listMeetingPrepFiles).mockReturnValue([
      makeFile("20260413_9aeb7339"),
      makeFile("20260427_50472c79"),
    ]);
    mockList.mockResolvedValue([]);
    vi.mocked(readMeetingPrepFile).mockReturnValue({
      content: "# Meeting prep",
      meta: undefined,
    });
    mockSave
      .mockRejectedValueOnce(new Error("Network error"))
      .mockResolvedValueOnce(undefined);

    const syncer = createSyncer();
    const result = await syncer.upload({ dryRun: false, force: false });

    expect(result.uploaded).toBe(1);
    expect(result.errors).toHaveLength(1);
    expect(result.errors[0]).toContain("Network error");
    expect(result.errors[0]).toContain("20260413_9aeb7339");
  });

  it("returns zero when nothing to upload", async () => {
    vi.mocked(listMeetingPrepFiles).mockReturnValue([
      makeFile("20260413_9aeb7339"),
    ]);
    mockList.mockResolvedValue([
      { date: "20260413_9aeb7339" } as never,
    ]);

    const syncer = createSyncer();
    const result = await syncer.upload({ dryRun: false, force: false });

    expect(result.uploaded).toBe(0);
    expect(result.skipped).toBe(1);
    expect(mockSave).not.toHaveBeenCalled();
  });
});

