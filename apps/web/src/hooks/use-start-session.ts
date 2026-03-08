import { useMutation } from "@tanstack/react-query";
import { apiFetch } from "../lib/api-client";

export type StartSessionResponse = {
  sessionId: string;
  roomName: string;
  livekitToken: string;
};

type RawStartSessionResponse = {
  session_id: string;
  room_name: string;
  livekit_token: string;
};

function isRawStartSessionResponse(value: unknown): value is RawStartSessionResponse {
  return (
    typeof value === "object" &&
    value !== null &&
    "session_id" in value &&
    typeof value.session_id === "string" &&
    "room_name" in value &&
    typeof value.room_name === "string" &&
    "livekit_token" in value &&
    typeof value.livekit_token === "string"
  );
}

function toStartSessionResponse(value: unknown): StartSessionResponse {
  if (!isRawStartSessionResponse(value)) {
    throw new Error("Session start response is invalid.");
  }

  return {
    sessionId: value.session_id,
    roomName: value.room_name,
    livekitToken: value.livekit_token,
  };
}

export function useStartSession() {
  return useMutation({
    mutationFn: async (): Promise<StartSessionResponse> => {
      const response = await apiFetch<unknown>("/sessions/start", {
        method: "POST",
      });

      return toStartSessionResponse(response);
    },
  });
}
