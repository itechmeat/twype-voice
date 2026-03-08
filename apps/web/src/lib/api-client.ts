import { ApiError } from "./api-error";
import { clearTokens, getTokens, setTokens, type AuthTokens } from "./auth-tokens";
import { redirectToLogin } from "./navigation";

type JsonRequestBody = BodyInit | Record<string, unknown> | unknown[] | null;

type ApiFetchOptions = Omit<RequestInit, "body"> & {
  body?: JsonRequestBody;
  skipAuthRefresh?: boolean;
};

type ApiRequestOptions = Omit<ApiFetchOptions, "skipAuthRefresh">;

type ErrorResponseBody = {
  detail?: string;
};

type TokenResponse = {
  access_token: string;
  refresh_token: string;
};

let refreshRequest: Promise<AuthTokens | null> | null = null;

function buildUrl(path: string): string {
  return path.startsWith("/api") ? path : `/api${path}`;
}

function isBodyInit(value: JsonRequestBody): value is BodyInit {
  return (
    typeof value === "string" ||
    value instanceof Blob ||
    value instanceof FormData ||
    value instanceof URLSearchParams ||
    value instanceof ArrayBuffer ||
    ArrayBuffer.isView(value)
  );
}

async function parseResponseBody(response: Response): Promise<unknown> {
  if (response.status === 204) {
    return undefined;
  }

  const contentType = response.headers.get("content-type") ?? "";

  if (contentType.includes("application/json")) {
    return response.json() as Promise<unknown>;
  }

  const text = await response.text();
  return text.length > 0 ? text : undefined;
}

function toApiError(response: Response, body: unknown): ApiError {
  if (typeof body === "object" && body !== null && "detail" in body) {
    const maybeDetail = (body as ErrorResponseBody).detail;

    if (typeof maybeDetail === "string") {
      return new ApiError(response.status, maybeDetail);
    }
  }

  const detail = response.statusText.length > 0 ? response.statusText : "Request failed";
  return new ApiError(response.status, detail);
}

function buildRequestInit(options: ApiRequestOptions): RequestInit {
  const { body, headers, ...rest } = options;
  const requestHeaders = new Headers(headers);
  const { accessToken } = getTokens();

  if (accessToken !== null) {
    requestHeaders.set("Authorization", `Bearer ${accessToken}`);
  }

  if (body === undefined) {
    return {
      ...rest,
      headers: requestHeaders,
    };
  }

  if (isBodyInit(body) || body === null) {
    return {
      ...rest,
      body,
      headers: requestHeaders,
    };
  }

  if (!requestHeaders.has("Content-Type")) {
    requestHeaders.set("Content-Type", "application/json");
  }

  return {
    ...rest,
    body: JSON.stringify(body),
    headers: requestHeaders,
  };
}

function isTokenResponse(value: unknown): value is TokenResponse {
  return (
    typeof value === "object" &&
    value !== null &&
    "access_token" in value &&
    typeof value.access_token === "string" &&
    "refresh_token" in value &&
    typeof value.refresh_token === "string"
  );
}

async function refreshTokens(): Promise<AuthTokens | null> {
  const { refreshToken } = getTokens();

  if (refreshToken === null) {
    clearTokens();
    redirectToLogin();
    return null;
  }

  try {
    const response = await fetch(buildUrl("/auth/refresh"), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        refresh_token: refreshToken,
      }),
    });

    if (!response.ok) {
      clearTokens();
      redirectToLogin();
      return null;
    }

    const body = await parseResponseBody(response);

    if (!isTokenResponse(body)) {
      clearTokens();
      redirectToLogin();
      return null;
    }

    setTokens(body.access_token, body.refresh_token);

    return {
      accessToken: body.access_token,
      refreshToken: body.refresh_token,
    };
  } catch {
    clearTokens();
    redirectToLogin();
    return null;
  }
}

async function getRefreshedTokens(): Promise<AuthTokens | null> {
  if (refreshRequest !== null) {
    return refreshRequest;
  }

  refreshRequest = refreshTokens().finally(() => {
    refreshRequest = null;
  });

  return refreshRequest;
}

export async function apiFetch<TResponse>(
  path: string,
  options: ApiFetchOptions = {},
): Promise<TResponse> {
  const { skipAuthRefresh = false, ...requestOptions } = options;
  const response = await fetch(buildUrl(path), buildRequestInit(requestOptions));
  const body = await parseResponseBody(response);

  if (response.ok) {
    return body as TResponse;
  }

  if (response.status === 401 && !skipAuthRefresh && path !== "/auth/refresh") {
    const tokens = await getRefreshedTokens();

    if (tokens !== null) {
      return apiFetch<TResponse>(path, {
        ...options,
        skipAuthRefresh: true,
      });
    }
  }

  throw toApiError(response, body);
}
