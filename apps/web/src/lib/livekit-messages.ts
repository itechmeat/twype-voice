export type LiveKitMessageType =
  | "chat_message"
  | "chat_response"
  | "structured_response"
  | "transcript"
  | "emotional_state";

export type ChatMessageOutbound = {
  type: "chat_message";
  text: string;
};

export type ChatResponseMessage = {
  type: "chat_response";
  text: string;
  is_final: boolean;
  message_id?: string;
};

export type StructuredResponseItem = {
  text: string;
  chunk_ids: string[];
};

export type StructuredResponseMessage = {
  type: "structured_response";
  items: StructuredResponseItem[];
  is_final: boolean;
  message_id?: string;
};

export type TranscriptMessage = {
  type: "transcript";
  role: "user" | "assistant";
  text: string;
  is_final: boolean;
  language: string;
  message_id?: string;
  sentiment_raw?: number;
};

export type EmotionalStateMessage = {
  type: "emotional_state";
  quadrant: string;
  valence: number;
  arousal: number;
  trend_valence: string;
  trend_arousal: string;
  is_refined: boolean;
  message_id?: string;
};

export type IncomingLiveKitMessage =
  | ChatResponseMessage
  | StructuredResponseMessage
  | TranscriptMessage
  | EmotionalStateMessage;

export type OutgoingLiveKitMessage = ChatMessageOutbound;

type UnknownRecord = Record<string, unknown>;
const textEncoder = new TextEncoder();

function isRecord(value: unknown): value is UnknownRecord {
  return typeof value === "object" && value !== null;
}

function hasStringField(value: UnknownRecord, key: string): value is UnknownRecord & Record<string, string> {
  return typeof value[key] === "string";
}

function hasBooleanField(
  value: UnknownRecord,
  key: string,
): value is UnknownRecord & Record<string, boolean> {
  return typeof value[key] === "boolean";
}

function hasOptionalStringField(value: UnknownRecord, key: string): boolean {
  return value[key] === undefined || typeof value[key] === "string";
}

function isStructuredResponseItem(value: unknown): value is StructuredResponseItem {
  if (!isRecord(value) || !hasStringField(value, "text")) {
    return false;
  }

  const { chunk_ids: chunkIds } = value;

  return Array.isArray(chunkIds) && chunkIds.every((item) => typeof item === "string");
}

function isChatResponseMessage(value: unknown): value is ChatResponseMessage {
  return (
    isRecord(value) &&
    value.type === "chat_response" &&
    hasStringField(value, "text") &&
    hasBooleanField(value, "is_final") &&
    hasOptionalStringField(value, "message_id")
  );
}

function isStructuredResponseMessage(value: unknown): value is StructuredResponseMessage {
  return (
    isRecord(value) &&
    value.type === "structured_response" &&
    Array.isArray(value.items) &&
    value.items.every(isStructuredResponseItem) &&
    hasBooleanField(value, "is_final") &&
    hasOptionalStringField(value, "message_id")
  );
}

function isTranscriptRole(value: unknown): value is "user" | "assistant" {
  return value === "user" || value === "assistant";
}

function isTranscriptMessage(value: unknown): value is TranscriptMessage {
  return (
    isRecord(value) &&
    value.type === "transcript" &&
    hasStringField(value, "text") &&
    hasBooleanField(value, "is_final") &&
    hasStringField(value, "language") &&
    isTranscriptRole(value.role) &&
    hasOptionalStringField(value, "message_id") &&
    (value.sentiment_raw === undefined || typeof value.sentiment_raw === "number")
  );
}

function isEmotionalStateMessage(value: unknown): value is EmotionalStateMessage {
  return (
    isRecord(value) &&
    value.type === "emotional_state" &&
    hasStringField(value, "quadrant") &&
    typeof value.valence === "number" &&
    typeof value.arousal === "number" &&
    hasStringField(value, "trend_valence") &&
    hasStringField(value, "trend_arousal") &&
    hasBooleanField(value, "is_refined") &&
    hasOptionalStringField(value, "message_id")
  );
}

export function isIncomingLiveKitMessage(value: unknown): value is IncomingLiveKitMessage {
  return (
    isChatResponseMessage(value) ||
    isStructuredResponseMessage(value) ||
    isTranscriptMessage(value) ||
    isEmotionalStateMessage(value)
  );
}

export function encodeLiveKitMessage<TMessage extends OutgoingLiveKitMessage>(
  message: TMessage,
): Uint8Array {
  return textEncoder.encode(JSON.stringify(message));
}
