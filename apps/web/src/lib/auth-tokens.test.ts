import { afterEach, describe, expect, it } from "vitest";
import { clearTokens, getTokens, setTokens } from "./auth-tokens";

describe("auth token storage", () => {
  afterEach(() => {
    window.localStorage.clear();
  });

  it("stores and reads tokens", () => {
    setTokens("access-123", "refresh-456");

    expect(getTokens()).toEqual({
      accessToken: "access-123",
      refreshToken: "refresh-456",
    });
  });

  it("clears tokens", () => {
    setTokens("access-123", "refresh-456");

    clearTokens();

    expect(getTokens()).toEqual({
      accessToken: null,
      refreshToken: null,
    });
  });
});
