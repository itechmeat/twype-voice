import { describe, expect, it } from "vitest";
import { resolveLiveKitUrl } from "./livekit-url";

describe("resolveLiveKitUrl", () => {
  it("prefers env override", () => {
    expect(
      resolveLiveKitUrl({
        envUrl: "wss://voice.example.com/custom",
        location: {
          host: "localhost:5173",
          protocol: "http:",
        },
      }),
    ).toBe("wss://voice.example.com/custom");
  });

  it("builds secure websocket URL from location", () => {
    expect(
      resolveLiveKitUrl({
        location: {
          host: "app.example.com",
          protocol: "https:",
        },
      }),
    ).toBe("wss://app.example.com/livekit-signaling/");
  });

  it("builds insecure websocket URL for local development", () => {
    expect(
      resolveLiveKitUrl({
        location: {
          host: "localhost:5173",
          protocol: "http:",
        },
      }),
    ).toBe("ws://localhost:5173/livekit-signaling/");
  });
});
