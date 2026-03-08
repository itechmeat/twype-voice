import { useQuery } from "@tanstack/react-query";
import { getSessionHistory } from "../lib/api-sessions";

export function useSessionHistory(offset: number, limit: number) {
  return useQuery({
    queryFn: () => getSessionHistory(offset, limit),
    queryKey: ["sessions", "history", offset, limit],
    staleTime: 30 * 1000,
  });
}
