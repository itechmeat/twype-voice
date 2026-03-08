import { renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { RoomEvent } from "livekit-client";
import { useDataChannel } from "./use-data-channel";

type DataReceivedHandler = (payload: Uint8Array, participant?: { identity?: string }) => void;

const listeners = new Map<string, DataReceivedHandler>();
const mockRoom = {
  localParticipant: {
    identity: "local-user",
  },
  off: vi.fn((event: string) => {
    listeners.delete(event);
  }),
  on: vi.fn((event: string, handler: DataReceivedHandler) => {
    listeners.set(event, handler);
  }),
};

vi.mock("@livekit/components-react", () => ({
  useRoomContext: () => mockRoom,
}));

describe("useDataChannel", () => {
  beforeEach(() => {
    listeners.clear();
    mockRoom.on.mockClear();
    mockRoom.off.mockClear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("dispatches known messages", () => {
    const handler = vi.fn();

    renderHook(() =>
      useDataChannel({
        chat_response: handler,
      }),
    );

    const callback = listeners.get(RoomEvent.DataReceived);
    expect(callback).toBeDefined();

    callback?.(
      new TextEncoder().encode('{"type":"chat_response","text":"Hello","is_final":true}'),
      { identity: "remote-user" },
    );

    expect(handler).toHaveBeenCalledWith({
      is_final: true,
      text: "Hello",
      type: "chat_response",
    });
  });

  it("ignores local and malformed payloads", () => {
    const handler = vi.fn();
    const warnSpy = vi.spyOn(console, "warn").mockImplementation(() => undefined);

    renderHook(() =>
      useDataChannel({
        chat_response: handler,
      }),
    );

    const callback = listeners.get(RoomEvent.DataReceived);
    callback?.(new TextEncoder().encode("not-json"), { identity: "remote-user" });
    callback?.(
      new TextEncoder().encode('{"type":"chat_response","text":"Hello","is_final":true}'),
      { identity: "local-user" },
    );
    callback?.(
      new TextEncoder().encode('{"type":"unknown","text":"Hello"}'),
      { identity: "remote-user" },
    );

    expect(handler).not.toHaveBeenCalled();
    expect(warnSpy).toHaveBeenCalledTimes(1);
  });
});
