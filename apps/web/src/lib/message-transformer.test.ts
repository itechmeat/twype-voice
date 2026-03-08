import { describe, expect, it } from "vitest";
import { transformMessageItem } from "./message-transformer";

describe("transformMessageItem", () => {
  it("maps user voice messages to user-voice entries", () => {
    expect(
      transformMessageItem({
        content: "How are you?",
        createdAt: "2026-03-07T10:00:00Z",
        id: "message-user-voice",
        mode: "voice",
        role: "user",
        sourceIds: null,
      }),
    ).toEqual({
      actor: "user",
      createdAt: "2026-03-07T10:00:00Z",
      id: "message-user-voice",
      mode: "voice",
      text: "How are you?",
      type: "user-voice",
    });
  });

  it("maps user text messages to user-text entries", () => {
    expect(
      transformMessageItem({
        content: "Tell me more.",
        createdAt: "2026-03-07T10:01:00Z",
        id: "message-user-text",
        mode: "text",
        role: "user",
        sourceIds: null,
      }),
    ).toEqual({
      actor: "user",
      createdAt: "2026-03-07T10:01:00Z",
      deliveryStatus: "sent",
      id: "message-user-text",
      mode: "text",
      text: "Tell me more.",
      type: "user-text",
    });
  });

  it("maps plain text assistant messages to agent-plain entries", () => {
    expect(
      transformMessageItem({
        content: "Blood pressure is elevated.",
        createdAt: "2026-03-07T10:05:00Z",
        id: "message-1",
        mode: "text",
        role: "assistant",
        sourceIds: ["chunk-1"],
      }),
    ).toEqual({
      actor: "agent",
      createdAt: "2026-03-07T10:05:00Z",
      id: "message-1",
      mode: "text",
      sourceIds: ["chunk-1"],
      text: "Blood pressure is elevated.",
      type: "agent-plain",
    });
  });

  it("maps structured JSON assistant messages to agent-structured entries", () => {
    expect(
      transformMessageItem({
        content: JSON.stringify({
          items: [
            {
              chunk_ids: ["chunk-1"],
              text: "First detail",
            },
          ],
        }),
        createdAt: "2026-03-07T10:05:00Z",
        id: "message-2",
        mode: "text",
        role: "assistant",
        sourceIds: ["chunk-1"],
      }),
    ).toEqual({
      actor: "agent",
      createdAt: "2026-03-07T10:05:00Z",
      id: "message-2",
      items: [
        {
          chunk_ids: ["chunk-1"],
          text: "First detail",
        },
      ],
      mode: "text",
      sourceIds: ["chunk-1"],
      type: "agent-structured",
    });
  });

  it("falls back to plain text when assistant content is malformed JSON", () => {
    expect(
      transformMessageItem({
        content: "{invalid json",
        createdAt: "2026-03-07T10:05:00Z",
        id: "message-3",
        mode: "text",
        role: "assistant",
        sourceIds: null,
      }),
    ).toEqual({
      actor: "agent",
      createdAt: "2026-03-07T10:05:00Z",
      id: "message-3",
      mode: "text",
      text: "{invalid json",
      type: "agent-plain",
    });
  });

  it("falls back to plain text when assistant JSON does not match the structured schema", () => {
    expect(
      transformMessageItem({
        content: '{"items":[{"text":"Broken"}]}',
        createdAt: "2026-03-07T10:05:00Z",
        id: "message-4",
        mode: "text",
        role: "assistant",
        sourceIds: null,
      }),
    ).toEqual({
      actor: "agent",
      createdAt: "2026-03-07T10:05:00Z",
      id: "message-4",
      mode: "text",
      text: '{"items":[{"text":"Broken"}]}',
      type: "agent-plain",
    });
  });
});
