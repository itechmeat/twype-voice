import type { ChatMessageEntry } from "./chat-state";
import type { SessionMessageItem } from "./api-sessions";

type StructuredContent = {
  items: Array<{
    text: string;
    chunk_ids: string[];
  }>;
};

function isStructuredContent(value: unknown): value is StructuredContent {
  return (
    typeof value === "object" &&
    value !== null &&
    "items" in value &&
    Array.isArray(value.items) &&
    value.items.every(
      (item) =>
        typeof item === "object" &&
        item !== null &&
        "text" in item &&
        typeof item.text === "string" &&
        "chunk_ids" in item &&
        Array.isArray(item.chunk_ids) &&
        item.chunk_ids.every((chunkId: unknown) => typeof chunkId === "string"),
    )
  );
}

function parseStructuredContent(content: string): StructuredContent | null {
  try {
    const parsed = JSON.parse(content) as unknown;
    return isStructuredContent(parsed) ? parsed : null;
  } catch {
    return null;
  }
}

function toAgentMessage(message: SessionMessageItem): ChatMessageEntry {
  const structuredContent = parseStructuredContent(message.content);
  const sourceIds = message.sourceIds ?? undefined;

  if (structuredContent !== null) {
    return {
      actor: "agent",
      createdAt: message.createdAt,
      id: message.id,
      items: structuredContent.items,
      mode: message.mode,
      ...(sourceIds === undefined ? {} : { sourceIds }),
      type: "agent-structured",
    };
  }

  return {
    actor: "agent",
    createdAt: message.createdAt,
    id: message.id,
    mode: message.mode,
    ...(sourceIds === undefined ? {} : { sourceIds }),
    text: message.content,
    type: "agent-plain",
  };
}

function toUserMessage(message: SessionMessageItem): ChatMessageEntry {
  if (message.mode === "voice") {
    return {
      actor: "user",
      createdAt: message.createdAt,
      id: message.id,
      mode: "voice",
      text: message.content,
      type: "user-voice",
    };
  }

  return {
    actor: "user",
    createdAt: message.createdAt,
    deliveryStatus: "sent",
    id: message.id,
    mode: "text",
    text: message.content,
    type: "user-text",
  };
}

export function transformMessageItem(message: SessionMessageItem): ChatMessageEntry {
  switch (message.role) {
    case "assistant":
      return toAgentMessage(message);
    case "user":
      return toUserMessage(message);
    default: {
      const exhaustiveCheck: never = message.role;
      throw new Error(`Unsupported message role: ${String(exhaustiveCheck)}`);
    }
  }
}
