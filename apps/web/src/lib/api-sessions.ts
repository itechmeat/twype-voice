import { apiFetch } from "./api-client";

export type SessionStatus = "active" | "ended" | "error";
export type SessionMessageRole = "user" | "assistant";
export type SessionMessageMode = "voice" | "text";

export type SessionHistoryItem = {
  id: string;
  roomName: string;
  status: SessionStatus;
  startedAt: string;
  endedAt: string | null;
};

export type SessionHistoryResponse = {
  items: SessionHistoryItem[];
  total: number;
};

export type SessionMessageItem = {
  id: string;
  role: SessionMessageRole;
  mode: SessionMessageMode;
  content: string;
  sourceIds: string[] | null;
  createdAt: string;
};

type RawSessionHistoryResponse = {
  items: RawSessionHistoryItem[];
  total: number;
};

type RawSessionHistoryItem = {
  id: string;
  room_name: string;
  status: SessionStatus;
  started_at: string;
  ended_at?: string | null;
};

type RawSessionMessageItem = {
  id: string;
  role: SessionMessageRole;
  mode: SessionMessageMode;
  content: string;
  source_ids?: string[] | null;
  created_at: string;
};

function isSessionMessageRole(value: unknown): value is SessionMessageRole {
  return value === "user" || value === "assistant";
}

function isSessionMessageMode(value: unknown): value is SessionMessageMode {
  return value === "voice" || value === "text";
}

function isSessionStatus(value: unknown): value is SessionStatus {
  return value === "active" || value === "ended" || value === "error";
}

function isRawSessionHistoryItem(value: unknown): value is RawSessionHistoryItem {
  return (
    typeof value === "object" &&
    value !== null &&
    "id" in value &&
    typeof value.id === "string" &&
    "room_name" in value &&
    typeof value.room_name === "string" &&
    "status" in value &&
    isSessionStatus(value.status) &&
    "started_at" in value &&
    typeof value.started_at === "string" &&
    (!("ended_at" in value) || value.ended_at === null || typeof value.ended_at === "string")
  );
}

function isRawSessionHistoryResponse(value: unknown): value is RawSessionHistoryResponse {
  return (
    typeof value === "object" &&
    value !== null &&
    "items" in value &&
    Array.isArray(value.items) &&
    value.items.every(isRawSessionHistoryItem) &&
    "total" in value &&
    typeof value.total === "number"
  );
}

function isRawSessionMessageItem(value: unknown): value is RawSessionMessageItem {
  return (
    typeof value === "object" &&
    value !== null &&
    "id" in value &&
    typeof value.id === "string" &&
    "role" in value &&
    isSessionMessageRole(value.role) &&
    "mode" in value &&
    isSessionMessageMode(value.mode) &&
    "content" in value &&
    typeof value.content === "string" &&
    "created_at" in value &&
    typeof value.created_at === "string" &&
    (!("source_ids" in value) ||
      value.source_ids === null ||
      (Array.isArray(value.source_ids) && value.source_ids.every((item) => typeof item === "string")))
  );
}

function toSessionHistoryItem(item: RawSessionHistoryItem): SessionHistoryItem {
  return {
    endedAt: item.ended_at ?? null,
    id: item.id,
    roomName: item.room_name,
    startedAt: item.started_at,
    status: item.status,
  };
}

function toSessionMessageItem(item: RawSessionMessageItem): SessionMessageItem {
  return {
    content: item.content,
    createdAt: item.created_at,
    id: item.id,
    mode: item.mode,
    role: item.role,
    sourceIds: item.source_ids ?? null,
  };
}

export async function getSessionHistory(
  offset: number,
  limit: number,
): Promise<SessionHistoryResponse> {
  const query = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
  });
  const response = await apiFetch<unknown>(`/sessions/history?${query.toString()}`);

  if (!isRawSessionHistoryResponse(response)) {
    throw new Error("Session history response is invalid.");
  }

  return {
    items: response.items.map(toSessionHistoryItem),
    total: response.total,
  };
}

export async function getSessionMessages(sessionId: string): Promise<SessionMessageItem[]> {
  const response = await apiFetch<unknown>(`/sessions/${sessionId}/messages`);

  if (!Array.isArray(response) || !response.every(isRawSessionMessageItem)) {
    throw new Error("Session messages response is invalid.");
  }

  return response.map(toSessionMessageItem);
}
