import { describe, expect, it } from "vitest";
import { encodeLiveKitMessage, isIncomingLiveKitMessage } from "./livekit-messages";

describe("livekit-messages", () => {
  it("accepts valid incoming payloads", () => {
    expect(
      isIncomingLiveKitMessage({
        is_final: true,
        text: "Hello",
        type: "chat_response",
      }),
    ).toBe(true);

    expect(
      isIncomingLiveKitMessage({
        is_final: false,
        language: "en",
        role: "user",
        text: "Hi",
        type: "transcript",
      }),
    ).toBe(true);

    expect(
      isIncomingLiveKitMessage({
        arousal: 0.2,
        is_refined: false,
        quadrant: "calm",
        trend_arousal: "stable",
        trend_valence: "up",
        type: "emotional_state",
        valence: 0.8,
      }),
    ).toBe(true);
  });

  it("rejects malformed payloads", () => {
    expect(isIncomingLiveKitMessage(null)).toBe(false);
    expect(
      isIncomingLiveKitMessage({
        is_final: true,
        text: 123,
        type: "chat_response",
      }),
    ).toBe(false);
    expect(
      isIncomingLiveKitMessage({
        items: [{ chunk_ids: [1], text: "Wrong" }],
        is_final: true,
        type: "structured_response",
      }),
    ).toBe(false);
  });

  it("encodes outgoing payloads as utf-8 JSON", () => {
    const payload = encodeLiveKitMessage({
      text: "Hello",
      type: "chat_message",
    });

    expect(JSON.parse(new TextDecoder().decode(payload))).toEqual({
      text: "Hello",
      type: "chat_message",
    });
  });
});
