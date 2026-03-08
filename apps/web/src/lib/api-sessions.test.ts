import { beforeEach, describe, expect, it, vi } from "vitest";
import { getSessionHistory, getSessionMessages } from "./api-sessions";

const apiFetchMock = vi.fn<(path: string, options?: unknown) => Promise<unknown>>();

vi.mock("./api-client", () => ({
  apiFetch: (path: string, options?: unknown) => apiFetchMock(path, options),
}));

describe("session API clients", () => {
  beforeEach(() => {
    apiFetchMock.mockReset();
  });

  it("maps session history payloads into frontend shape", async () => {
    apiFetchMock.mockResolvedValueOnce({
      items: [
        {
          ended_at: "2026-03-07T10:30:00Z",
          id: "session-1",
          room_name: "room-1",
          started_at: "2026-03-07T10:00:00Z",
          status: "completed",
        },
      ],
      total: 1,
    });

    await expect(getSessionHistory(20, 10)).resolves.toEqual({
      items: [
        {
          endedAt: "2026-03-07T10:30:00Z",
          id: "session-1",
          roomName: "room-1",
          startedAt: "2026-03-07T10:00:00Z",
          status: "completed",
        },
      ],
      total: 1,
    });

    expect(apiFetchMock).toHaveBeenCalledWith("/sessions/history?limit=10&offset=20", undefined);
  });

  it("maps session messages payloads into frontend shape", async () => {
    apiFetchMock.mockResolvedValueOnce([
      {
        content: "Hello",
        created_at: "2026-03-07T10:05:00Z",
        id: "message-1",
        mode: "text",
        role: "assistant",
        source_ids: ["chunk-1"],
      },
    ]);

    await expect(getSessionMessages("session-1")).resolves.toEqual([
      {
        content: "Hello",
        createdAt: "2026-03-07T10:05:00Z",
        id: "message-1",
        mode: "text",
        role: "assistant",
        sourceIds: ["chunk-1"],
      },
    ]);

    expect(apiFetchMock).toHaveBeenCalledWith("/sessions/session-1/messages", undefined);
  });

  it("rejects invalid session payloads", async () => {
    apiFetchMock.mockResolvedValueOnce({
      items: "invalid",
      total: 1,
    });

    await expect(getSessionHistory(0, 20)).rejects.toThrow("Session history response is invalid.");
  });

  it("rejects invalid session messages payloads", async () => {
    apiFetchMock.mockResolvedValueOnce([
      {
        content: "Hello",
        created_at: "2026-03-07T10:05:00Z",
        id: "message-1",
        mode: "text",
        role: "assistant",
        source_ids: [123],
      },
    ]);

    await expect(getSessionMessages("session-1")).rejects.toThrow(
      "Session messages response is invalid.",
    );
  });
});
