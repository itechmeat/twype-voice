import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";
import { useStartSession } from "./use-start-session";

const apiFetchMock = vi.fn<(path: string, options?: unknown) => Promise<unknown>>();

vi.mock("../lib/api-client", () => ({
  apiFetch: (path: string, options?: unknown) => apiFetchMock(path, options),
}));

function Wrapper({ children }: { children: ReactNode }) {
  const queryClient = new QueryClient({
    defaultOptions: {
      mutations: {
        retry: false,
      },
    },
  });

  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}

describe("useStartSession", () => {
  it("maps API response into frontend shape", async () => {
    apiFetchMock.mockResolvedValueOnce({
      livekit_token: "token-123",
      room_name: "session-room",
      session_id: "session-id",
    });

    const { result } = renderHook(() => useStartSession(), {
      wrapper: Wrapper,
    });

    await expect(result.current.mutateAsync()).resolves.toEqual({
      livekitToken: "token-123",
      roomName: "session-room",
      sessionId: "session-id",
    });
    expect(apiFetchMock).toHaveBeenCalledWith("/sessions/start", { method: "POST" });
  });

  it("rejects invalid payloads", async () => {
    apiFetchMock.mockResolvedValueOnce({
      room_name: "session-room",
    });

    const { result } = renderHook(() => useStartSession(), {
      wrapper: Wrapper,
    });

    await expect(result.current.mutateAsync()).rejects.toThrow("Session start response is invalid.");
  });
});
