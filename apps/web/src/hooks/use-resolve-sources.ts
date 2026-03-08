import { useQuery } from "@tanstack/react-query";
import { resolveSources } from "../lib/api-sources";

export function getResolveSourcesQueryKey(chunkIds: string[]) {
  return ["sources", "resolve", [...chunkIds].sort()] as const;
}

export function useResolveSources(chunkIds: string[]) {
  return useQuery({
    enabled: false,
    queryFn: () => resolveSources(chunkIds),
    queryKey: getResolveSourcesQueryKey(chunkIds),
    staleTime: 5 * 60 * 1000,
  });
}
