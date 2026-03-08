import { renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ConnectionState } from "livekit-client";
import { useSendDataChannel } from "./use-send-data-channel";

const publishData = vi.fn();
const mockRoom = {
  localParticipant: {
    publishData,
  },
  state: ConnectionState.Connected,
};

vi.mock("@livekit/components-react", () => ({
  useRoomContext: () => mockRoom,
}));

describe("useSendDataChannel", () => {
  beforeEach(() => {
    publishData.mockReset();
    mockRoom.state = ConnectionState.Connected;
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("publishes reliable chat messages when connected", async () => {
    publishData.mockResolvedValue(undefined);
    const { result } = renderHook(() => useSendDataChannel());

    await expect(result.current("chat_message", { text: "Hello" })).resolves.toBe(true);

    const [payload, options] = publishData.mock.calls[0] as [Uint8Array, { reliable: boolean }];
    expect(new TextDecoder().decode(payload)).toBe('{"type":"chat_message","text":"Hello"}');
    expect(options).toEqual({ reliable: true });
  });

  it("returns false without publishing when disconnected", async () => {
    vi.spyOn(console, "warn").mockImplementation(() => undefined);
    mockRoom.state = ConnectionState.Disconnected;
    const { result } = renderHook(() => useSendDataChannel());

    await expect(result.current("chat_message", { text: "Hello" })).resolves.toBe(false);
    expect(publishData).not.toHaveBeenCalled();
  });
});
