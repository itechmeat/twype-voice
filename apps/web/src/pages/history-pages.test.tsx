import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { renderWithRouter } from "../test/test-utils";
import { HistoryPage } from "./HistoryPage";
import { SessionDetailPage } from "./SessionDetailPage";

const useSessionHistoryMock = vi.fn();
const useSessionMessagesMock = vi.fn();

vi.mock("../hooks/use-session-history", () => ({
  useSessionHistory: (offset: number, limit: number) => useSessionHistoryMock(offset, limit),
}));

vi.mock("../hooks/use-session-messages", () => ({
  useSessionMessages: (sessionId: string | null) => useSessionMessagesMock(sessionId),
}));

describe("HistoryPage", () => {
  beforeEach(() => {
    useSessionHistoryMock.mockReset();
    useSessionMessagesMock.mockReset();
  });

  it("renders a loading state", () => {
    useSessionHistoryMock.mockReturnValue({
      data: undefined,
      error: null,
      isError: false,
      isFetching: false,
      isPending: true,
      refetch: vi.fn(),
    });

    renderWithRouter([{ path: "/history", element: <HistoryPage /> }], ["/history"]);

    expect(screen.getByText("Loading your previous sessions...")).toBeInTheDocument();
  });

  it("renders an empty state", () => {
    useSessionHistoryMock.mockReturnValue({
      data: { items: [], total: 0 },
      error: null,
      isError: false,
      isFetching: false,
      isPending: false,
      refetch: vi.fn(),
    });

    renderWithRouter([{ path: "/history", element: <HistoryPage /> }], ["/history"]);

    expect(screen.getByText("No past sessions are available yet.")).toBeInTheDocument();
  });

  it("renders an error state with retry", async () => {
    const user = userEvent.setup();
    const refetch = vi.fn();
    const errorState = {
      data: undefined,
      error: new Error("History failed"),
      isError: true,
      isFetching: false,
      isPending: false,
      refetch,
    };

    useSessionHistoryMock.mockReturnValue(errorState);

    renderWithRouter([{ path: "/history", element: <HistoryPage /> }], ["/history"]);

    expect(screen.getByText("History failed")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Retry" }));
    expect(refetch).toHaveBeenCalledTimes(1);
  });

  it("supports pagination and navigation to session details", async () => {
    const user = userEvent.setup();
    const historyRefetch = vi.fn();
    const firstPage = {
      data: {
        items: [
          {
            endedAt: "2026-03-07T10:30:00Z",
            id: "session-1",
            roomName: "Session one",
            startedAt: "2026-03-07T10:00:00Z",
            status: "completed",
          },
        ],
        total: 2,
      },
      error: null,
      isError: false,
      isFetching: false,
      isPending: false,
      refetch: historyRefetch,
    };
    const secondPage = {
      data: {
        items: [
          {
            endedAt: null,
            id: "session-2",
            roomName: "Session two",
            startedAt: "2026-03-07T09:00:00Z",
            status: "active",
          },
        ],
        total: 2,
      },
      error: null,
      isError: false,
      isFetching: false,
      isPending: false,
      refetch: historyRefetch,
    };

    useSessionHistoryMock.mockImplementation((offset: number) => {
      return offset === 0 ? firstPage : secondPage;
    });

    const detailState = {
      data: [
        {
          content: "Historical reply",
          createdAt: "2026-03-07T10:05:00Z",
          id: "message-1",
          mode: "text",
          role: "assistant",
          sourceIds: ["chunk-1"],
        },
      ],
      error: null,
      isError: false,
      isPending: false,
      refetch: vi.fn(),
    };

    useSessionMessagesMock.mockReturnValue(detailState);

    renderWithRouter(
      [
        {
          path: "/history",
          element: <HistoryPage />,
        },
        {
          path: "/history/:sessionId",
          element: <SessionDetailPage />,
        },
      ],
      ["/history"],
    );

    expect(screen.getByRole("link", { name: /Session one/i })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Load more" }));
    expect(screen.getByRole("link", { name: /Session two/i })).toBeInTheDocument();

    await user.click(screen.getByRole("link", { name: /Session one/i }));
    expect(await screen.findByRole("heading", { name: "Session details" })).toBeInTheDocument();
    expect(screen.getByText("Historical reply")).toBeInTheDocument();
  });
});

describe("SessionDetailPage", () => {
  beforeEach(() => {
    useSessionMessagesMock.mockReset();
  });

  it("renders a loading state", () => {
    const loadingState = {
      data: undefined,
      error: null,
      isError: false,
      isPending: true,
      refetch: vi.fn(),
    };

    useSessionMessagesMock.mockReturnValue(loadingState);

    renderWithRouter([{ path: "/history/:sessionId", element: <SessionDetailPage /> }], [
      "/history/session-1",
    ]);

    expect(screen.getByText("Loading session messages...")).toBeInTheDocument();
  });

  it("renders an error state", () => {
    const refetch = vi.fn();
    const errorState = {
      data: undefined,
      error: new Error("Messages failed"),
      isError: true,
      isPending: false,
      refetch,
    };

    useSessionMessagesMock.mockReturnValue(errorState);

    renderWithRouter([{ path: "/history/:sessionId", element: <SessionDetailPage /> }], [
      "/history/session-1",
    ]);

    expect(screen.getByText("Messages failed")).toBeInTheDocument();
  });

  it("retries from the error state", async () => {
    const user = userEvent.setup();
    const refetch = vi.fn();
    const errorState = {
      data: undefined,
      error: new Error("Messages failed"),
      isError: true,
      isPending: false,
      refetch,
    };

    useSessionMessagesMock.mockReturnValue(errorState);

    renderWithRouter([{ path: "/history/:sessionId", element: <SessionDetailPage /> }], [
      "/history/session-1",
    ]);

    await user.click(screen.getByRole("button", { name: "Retry" }));
    expect(refetch).toHaveBeenCalledTimes(1);
  });

  it("renders an empty state", () => {
    const emptyState = {
      data: [],
      error: null,
      isError: false,
      isPending: false,
      refetch: vi.fn(),
    };

    useSessionMessagesMock.mockReturnValue(emptyState);

    renderWithRouter([{ path: "/history/:sessionId", element: <SessionDetailPage /> }], [
      "/history/session-1",
    ]);

    expect(screen.getByText("No messages were found for this session.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Back to history" })).toBeInTheDocument();
  });
});
