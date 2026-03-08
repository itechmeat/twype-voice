import { describe, expect, it } from "vitest";
import {
  chatStateReducer,
  createInitialChatState,
  type ChatState,
} from "./chat-state";

function reduce(actions: Parameters<typeof chatStateReducer>[1][]): ChatState {
  return actions.reduce(chatStateReducer, createInitialChatState());
}

describe("chatStateReducer", () => {
  it("appends messages in order and updates mode from user input", () => {
    const state = reduce([
      {
        type: "add-message",
        message: {
          actor: "user",
          createdAt: "2026-03-07T10:00:00.000Z",
          id: "voice-1",
          mode: "voice",
          text: "Hello there",
          type: "user-voice",
        },
      },
      {
        type: "add-message",
        message: {
          actor: "agent",
          createdAt: "2026-03-07T10:00:01.000Z",
          id: "agent-1",
          mode: "voice",
          text: "Hi",
          type: "agent-plain",
        },
      },
      {
        type: "add-message",
        message: {
          actor: "user",
          createdAt: "2026-03-07T10:00:02.000Z",
          deliveryStatus: "sending",
          id: "text-1",
          mode: "text",
          text: "Switch to text",
          type: "user-text",
        },
      },
    ]);

    expect(state.messages.map((message) => message.id)).toEqual(["voice-1", "agent-1", "text-1"]);
    expect(state.currentMode).toBe("text");
  });

  it("updates user text message delivery status", () => {
    const state = reduce([
      {
        type: "add-message",
        message: {
          actor: "user",
          createdAt: "2026-03-07T10:00:02.000Z",
          deliveryStatus: "sending",
          id: "text-1",
          mode: "text",
          text: "Switch to text",
          type: "user-text",
        },
      },
      {
        type: "update-user-text-message-status",
        deliveryStatus: "failed",
        id: "text-1",
      },
    ]);

    expect(state.messages).toEqual([
      expect.objectContaining({
        deliveryStatus: "failed",
        id: "text-1",
      }),
    ]);
  });

  it("tracks and clears interim transcript", () => {
    const state = reduce([
      {
        type: "set-interim-transcript",
        text: "partial text",
      },
      {
        type: "clear-interim-transcript",
      },
    ]);

    expect(state.interimTranscript).toBeNull();
  });

  it("tracks streaming responses and emotional state", () => {
    const state = reduce([
      {
        type: "set-streaming-response",
        streamingResponse: {
          text: "typing",
          type: "plain",
        },
      },
      {
        type: "set-emotional-state",
        emotionalState: {
          arousal: 0.34,
          is_refined: false,
          message_id: "emotion-1",
          quadrant: "calm",
          trend_arousal: "stable",
          trend_valence: "up",
          valence: 0.68,
        },
      },
    ]);

    expect(state.streamingResponse).toEqual({
      text: "typing",
      type: "plain",
    });
    expect(state.emotionalState?.quadrant).toBe("calm");
  });

  it("clears streaming responses", () => {
    const state = reduce([
      {
        type: "set-streaming-response",
        streamingResponse: {
          items: [],
          type: "structured",
        },
      },
      {
        type: "clear-streaming-response",
      },
    ]);

    expect(state.streamingResponse).toBeNull();
  });
});
