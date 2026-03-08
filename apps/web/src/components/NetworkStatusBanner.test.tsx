import { act, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { NetworkStatusBanner } from "./NetworkStatusBanner";

describe("NetworkStatusBanner", () => {
  const originalNavigatorOnLine = navigator.onLine;

  afterEach(() => {
    Object.defineProperty(window.navigator, "onLine", {
      configurable: true,
      value: originalNavigatorOnLine,
    });
  });

  it("toggles the offline indicator when network status changes", () => {
    Object.defineProperty(window.navigator, "onLine", {
      configurable: true,
      value: true,
    });

    render(<NetworkStatusBanner />);
    expect(screen.queryByRole("status")).not.toBeInTheDocument();

    act(() => {
      Object.defineProperty(window.navigator, "onLine", {
        configurable: true,
        value: false,
      });
      window.dispatchEvent(new Event("offline"));
    });

    expect(screen.getByRole("status")).toHaveTextContent("Offline.");

    act(() => {
      Object.defineProperty(window.navigator, "onLine", {
        configurable: true,
        value: true,
      });
      window.dispatchEvent(new Event("online"));
    });

    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });
});
