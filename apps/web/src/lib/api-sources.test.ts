import { describe, expect, it, vi, beforeEach } from "vitest";
import { resolveSources } from "./api-sources";

const apiFetchMock = vi.fn<(path: string, options?: unknown) => Promise<unknown>>();

vi.mock("./api-client", () => ({
  apiFetch: (path: string, options?: unknown) => apiFetchMock(path, options),
}));

describe("resolveSources", () => {
  beforeEach(() => {
    apiFetchMock.mockReset();
  });

  it("returns an empty array without calling the API for empty chunk IDs", async () => {
    await expect(resolveSources([])).resolves.toEqual([]);
    expect(apiFetchMock).not.toHaveBeenCalled();
  });

  it("maps snake_case API fields to frontend shape", async () => {
    apiFetchMock.mockResolvedValueOnce({
      items: [
        {
          author: "Dr. Smith",
          chunk_id: "chunk-1",
          page_range: "45-47",
          section: "Chapter 3",
          source_type: "book",
          title: "Medical Guide",
          url: "https://example.com/medical-guide",
        },
      ],
    });

    await expect(resolveSources(["chunk-1"])).resolves.toEqual([
      {
        author: "Dr. Smith",
        chunkId: "chunk-1",
        pageRange: "45-47",
        section: "Chapter 3",
        sourceType: "book",
        title: "Medical Guide",
        url: "https://example.com/medical-guide",
      },
    ]);

    expect(apiFetchMock).toHaveBeenCalledWith("/sources/resolve", {
      body: {
        chunk_ids: ["chunk-1"],
      },
      method: "POST",
    });
  });

  it("preserves nullable optional source fields", async () => {
    apiFetchMock.mockResolvedValueOnce({
      items: [
        {
          author: null,
          chunk_id: "chunk-2",
          page_range: null,
          section: null,
          source_type: "article",
          title: "Clinical Notes",
          url: null,
        },
      ],
    });

    await expect(resolveSources(["chunk-2"])).resolves.toEqual([
      {
        author: null,
        chunkId: "chunk-2",
        pageRange: null,
        section: null,
        sourceType: "article",
        title: "Clinical Notes",
        url: null,
      },
    ]);
  });

  it("rejects invalid payloads", async () => {
    apiFetchMock.mockResolvedValueOnce({
      items: [{ chunk_id: "chunk-1" }],
    });

    await expect(resolveSources(["chunk-1"])).rejects.toThrow(
      "Resolved sources response is invalid.",
    );
  });
});
