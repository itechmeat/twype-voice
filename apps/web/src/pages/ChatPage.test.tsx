import { fireEvent, render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ConnectionState } from "livekit-client";
import { ConnectionStateBanner } from "./ChatPage";

let connectionState = ConnectionState.Connected;

vi.mock("@livekit/components-react", () => ({
  LiveKitRoom: ({ children }: { children: ReactNode }) => <>{children}</>,
  RoomAudioRenderer: () => null,
  useConnectionState: () => connectionState,
}));

vi.mock("../components/AgentStateIndicator", () => ({
  AgentStateIndicator: () => null,
}));

vi.mock("../components/AudioLevelIndicator", () => ({
  AudioLevelIndicator: () => null,
}));

vi.mock("../components/ChatFeed", () => ({
  ChatFeed: () => null,
}));

vi.mock("../components/MicToggle", () => ({
  MicToggle: () => null,
}));

vi.mock("../components/TextInput", () => ({
  TextInput: () => null,
}));

vi.mock("../hooks/use-data-channel", () => ({
  useDataChannel: () => undefined,
}));

vi.mock("../hooks/use-send-data-channel", () => ({
  useSendDataChannel: () => vi.fn(),
}));

vi.mock("../hooks/use-start-session", () => ({
  useStartSession: () => ({
    data: undefined,
    error: null,
    isError: false,
    isPending: false,
    mutate: vi.fn(),
    reset: vi.fn(),
    status: "success",
  }),
}));

vi.mock("../lib/livekit-url", () => ({
  resolveLiveKitUrl: () => "wss://example.livekit",
}));

describe("ConnectionStateBanner", () => {
  beforeEach(() => {
    connectionState = ConnectionState.Connected;
  });

  it("requests a remount reconnect without reloading the page", () => {
    connectionState = ConnectionState.Disconnected;
    const onReconnect = vi.fn();

    render(<ConnectionStateBanner onReconnect={onReconnect} />);

    fireEvent.click(screen.getByRole("button", { name: "Reconnect" }));

    expect(onReconnect).toHaveBeenCalledTimes(1);
  });
});
