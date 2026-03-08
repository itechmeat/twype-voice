import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

function jsonResponse(body: unknown, init?: ResponseInit): Response {
  return new Response(JSON.stringify(body), {
    headers: {
      "Content-Type": "application/json",
    },
    ...init,
  });
}

function textResponse(body: string, init?: ResponseInit): Response {
  return new Response(body, init);
}

describe("apiFetch", () => {
  beforeEach(() => {
    vi.resetModules();
    window.localStorage.clear();
    window.history.pushState({}, "", "/");
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("serializes JSON bodies and injects auth headers", async () => {
    const fetchMock = vi
      .fn<(input: string, init?: RequestInit) => Promise<Response>>()
      .mockResolvedValue(
        jsonResponse({
          ok: true,
        }),
      );
    vi.stubGlobal("fetch", fetchMock);

    const { apiFetch } = await import("./api-client");
    const { setTokens } = await import("./auth-tokens");
    setTokens("access-token", "refresh-token");

    await expect(
      apiFetch<{ ok: boolean }>("/sessions/history", {
        method: "POST",
        body: { page: 1 },
      }),
    ).resolves.toEqual({ ok: true });

    const firstCall = fetchMock.mock.calls[0];
    expect(firstCall).toBeDefined();
    expect(firstCall?.[0]).toBe("/api/sessions/history");

    const requestInit = firstCall?.[1];
    expect(requestInit?.method).toBe("POST");
    expect(requestInit?.body).toBe(JSON.stringify({ page: 1 }));

    const headers = requestInit?.headers;
    expect(headers).toBeInstanceOf(Headers);
    expect((headers as Headers).get("Authorization")).toBe("Bearer access-token");
    expect((headers as Headers).get("Content-Type")).toBe("application/json");
  });

  it("omits Authorization header when no access token exists", async () => {
    const fetchMock = vi
      .fn<(input: string, init?: RequestInit) => Promise<Response>>()
      .mockResolvedValue(jsonResponse({ ok: true }));
    vi.stubGlobal("fetch", fetchMock);

    const { apiFetch } = await import("./api-client");

    await expect(apiFetch<{ ok: boolean }>("/sessions/history")).resolves.toEqual({ ok: true });

    const headers = fetchMock.mock.calls[0]?.[1]?.headers;
    expect(headers).toBeInstanceOf(Headers);
    expect((headers as Headers).get("Authorization")).toBeNull();
  });

  it("throws ApiError with FastAPI detail", async () => {
    const fetchMock = vi
      .fn<(input: string, init?: RequestInit) => Promise<Response>>()
      .mockResolvedValue(
        jsonResponse(
          {
            detail: "Email is already registered",
          },
          {
            status: 409,
            statusText: "Conflict",
          },
        ),
      );
    vi.stubGlobal("fetch", fetchMock);

    const { apiFetch } = await import("./api-client");

    await expect(apiFetch("/auth/register", { method: "POST", body: {} })).rejects.toMatchObject({
      name: "ApiError",
      status: 409,
      message: "Email is already registered",
    });
  });

  it("falls back to status text for non-JSON error responses", async () => {
    const fetchMock = vi
      .fn<(input: string, init?: RequestInit) => Promise<Response>>()
      .mockResolvedValue(
        textResponse("Internal Server Error", {
          status: 500,
          statusText: "Internal Server Error",
        }),
      );
    vi.stubGlobal("fetch", fetchMock);

    const { apiFetch } = await import("./api-client");

    await expect(apiFetch("/auth/register", { method: "POST", body: {} })).rejects.toMatchObject({
      status: 500,
      message: "Internal Server Error",
    });
  });

  it("refreshes tokens after a 401 and retries the original request once", async () => {
    const fetchMock = vi
      .fn<(input: string, init?: RequestInit) => Promise<Response>>()
      .mockResolvedValueOnce(
        jsonResponse(
          {
            detail: "Expired access token",
          },
          {
            status: 401,
            statusText: "Unauthorized",
          },
        ),
      )
      .mockResolvedValueOnce(
        jsonResponse({
          access_token: "new-access",
          refresh_token: "new-refresh",
          token_type: "bearer",
        }),
      )
      .mockResolvedValueOnce(
        jsonResponse({
          items: [],
        }),
      );
    vi.stubGlobal("fetch", fetchMock);

    const { apiFetch } = await import("./api-client");
    const { getTokens, setTokens } = await import("./auth-tokens");
    setTokens("old-access", "old-refresh");

    await expect(apiFetch<{ items: unknown[] }>("/sessions/history")).resolves.toEqual({
      items: [],
    });

    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      "/api/auth/refresh",
      expect.objectContaining({
        method: "POST",
      }),
    );
    expect(getTokens()).toEqual({
      accessToken: "new-access",
      refreshToken: "new-refresh",
    });
    expect(fetchMock).toHaveBeenCalledTimes(3);
  });

  it("deduplicates concurrent refresh requests and redirects to login on refresh failure", async () => {
    const fetchMock = vi
      .fn<(input: string, init?: RequestInit) => Promise<Response>>()
      .mockResolvedValueOnce(
        jsonResponse(
          { detail: "Unauthorized" },
          {
            status: 401,
            statusText: "Unauthorized",
          },
        ),
      )
      .mockResolvedValueOnce(
        jsonResponse(
          { detail: "Unauthorized" },
          {
            status: 401,
            statusText: "Unauthorized",
          },
        ),
      )
      .mockResolvedValueOnce(
        jsonResponse(
          { detail: "Refresh token expired" },
          {
            status: 401,
            statusText: "Unauthorized",
          },
        ),
      );
    vi.stubGlobal("fetch", fetchMock);

    const { apiFetch } = await import("./api-client");
    const { getTokens, setTokens } = await import("./auth-tokens");
    setTokens("old-access", "old-refresh");

    const firstRequest = apiFetch("/sessions/history");
    const secondRequest = apiFetch("/sessions/history");

    await expect(firstRequest).rejects.toMatchObject({
      status: 401,
      message: "Unauthorized",
    });
    await expect(secondRequest).rejects.toMatchObject({
      status: 401,
      message: "Unauthorized",
    });

    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(fetchMock.mock.calls.filter(([url]) => url === "/api/auth/refresh")).toHaveLength(1);
    expect(getTokens()).toEqual({
      accessToken: null,
      refreshToken: null,
    });
    expect(window.location.pathname).toBe("/login");
  });

  it("deduplicates concurrent refresh requests and retries both requests on success", async () => {
    let historyCallCount = 0;
    const unauthorizedResolvers: Array<() => void> = [];

    const fetchMock = vi.fn<(input: string, init?: RequestInit) => Promise<Response>>(
      async (input) => {
        if (input === "/api/sessions/history") {
          historyCallCount += 1;

          if (historyCallCount <= 2) {
            await new Promise<void>((resolve) => {
              unauthorizedResolvers.push(resolve);

              if (unauthorizedResolvers.length === 2) {
                for (const release of unauthorizedResolvers) {
                  release();
                }
              }
            });

            return jsonResponse(
              { detail: "Unauthorized" },
              { status: 401, statusText: "Unauthorized" },
            );
          }

          return jsonResponse({ ok: true });
        }

        if (input === "/api/auth/refresh") {
          return jsonResponse({
            access_token: "new-access",
            refresh_token: "new-refresh",
          });
        }

        return jsonResponse({ ok: true });
      },
    );
    vi.stubGlobal("fetch", fetchMock);

    const { apiFetch } = await import("./api-client");
    const { setTokens } = await import("./auth-tokens");
    setTokens("old-access", "old-refresh");

    const firstRequest = apiFetch<{ ok: boolean }>("/sessions/history");
    const secondRequest = apiFetch<{ ok: boolean }>("/sessions/history");

    await expect(firstRequest).resolves.toEqual({ ok: true });
    await expect(secondRequest).resolves.toEqual({ ok: true });

    expect(fetchMock.mock.calls.filter(([url]) => url === "/api/auth/refresh")).toHaveLength(1);
  });

  it("treats invalid refresh payloads as refresh failure", async () => {
    const fetchMock = vi
      .fn<(input: string, init?: RequestInit) => Promise<Response>>()
      .mockResolvedValueOnce(
        jsonResponse({ detail: "Unauthorized" }, { status: 401, statusText: "Unauthorized" }),
      )
      .mockResolvedValueOnce(jsonResponse({ token: "invalid-shape" }));
    vi.stubGlobal("fetch", fetchMock);

    const { apiFetch } = await import("./api-client");
    const { getTokens, setTokens } = await import("./auth-tokens");
    setTokens("old-access", "old-refresh");

    await expect(apiFetch("/sessions/history")).rejects.toMatchObject({
      status: 401,
      message: "Unauthorized",
    });
    expect(getTokens()).toEqual({
      accessToken: null,
      refreshToken: null,
    });
    expect(window.location.pathname).toBe("/login");
  });
});
