import { useQuery } from "@tanstack/react-query";
import { getSessionMessages } from "../lib/api-sessions";

export function useSessionMessages(sessionId: string | null) {
  return useQuery({
    enabled: sessionId !== null && sessionId.length > 0,
    queryFn: () => {
      if (!sessionId) {
        throw new Error("sessionId is required but was falsy");
      }
      return getSessionMessages(sessionId);
    },
    queryKey: ["sessions", sessionId, "messages"],
    staleTime: Number.POSITIVE_INFINITY,
  });
}
