import { apiFetch } from "./api-client";

export type SourceType = "book" | "video" | "podcast" | "article" | "post";

export type ResolvedSource = {
  chunkId: string;
  sourceType: SourceType;
  title: string;
  author: string | null;
  url: string | null;
  section: string | null;
  pageRange: string | null;
};

type RawResolveSourcesResponse = {
  items: RawSourceItem[];
};

type RawSourceItem = {
  chunk_id: string;
  source_type: SourceType;
  title: string;
  author?: string | null;
  url?: string | null;
  section?: string | null;
  page_range?: string | null;
};

function isSourceType(value: unknown): value is SourceType {
  return (
    value === "book" ||
    value === "video" ||
    value === "podcast" ||
    value === "article" ||
    value === "post"
  );
}

function isRawSourceItem(value: unknown): value is RawSourceItem {
  return (
    typeof value === "object" &&
    value !== null &&
    "chunk_id" in value &&
    typeof value.chunk_id === "string" &&
    "source_type" in value &&
    isSourceType(value.source_type) &&
    "title" in value &&
    typeof value.title === "string" &&
    (!("author" in value) || value.author === null || typeof value.author === "string") &&
    (!("url" in value) || value.url === null || typeof value.url === "string") &&
    (!("section" in value) || value.section === null || typeof value.section === "string") &&
    (!("page_range" in value) ||
      value.page_range === null ||
      typeof value.page_range === "string")
  );
}

function isRawResolveSourcesResponse(value: unknown): value is RawResolveSourcesResponse {
  return (
    typeof value === "object" &&
    value !== null &&
    "items" in value &&
    Array.isArray(value.items) &&
    value.items.every(isRawSourceItem)
  );
}

function toResolvedSource(item: RawSourceItem): ResolvedSource {
  return {
    author: item.author ?? null,
    chunkId: item.chunk_id,
    pageRange: item.page_range ?? null,
    section: item.section ?? null,
    sourceType: item.source_type,
    title: item.title,
    url: item.url ?? null,
  };
}

export async function resolveSources(chunkIds: string[]): Promise<ResolvedSource[]> {
  if (chunkIds.length === 0) {
    return [];
  }

  const response = await apiFetch<unknown>("/sources/resolve", {
    body: {
      chunk_ids: chunkIds,
    },
    method: "POST",
  });

  if (!isRawResolveSourcesResponse(response)) {
    throw new Error("Resolved sources response is invalid.");
  }

  return response.items.map(toResolvedSource);
}
