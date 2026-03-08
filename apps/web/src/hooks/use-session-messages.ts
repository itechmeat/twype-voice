import { useQuery } from "@tanstack/react-query";
import { getSessionMessages } from "../lib/api-sessions";

export function useSessionMessages(sessionId: string | null) {
  return useQuery({
    enabled: sessionId !== null,
    queryFn: () => getSessionMessages(sessionId ?? ""),
    queryKey: ["sessions", sessionId, "messages"],
    staleTime: Number.POSITIVE_INFINITY,
  });
}
