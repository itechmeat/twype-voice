import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { UpdatePrompt } from ".";

describe("UpdatePrompt", () => {
  it("renders the prompt and calls update when confirmed", async () => {
    const user = userEvent.setup();
    const onUpdate = vi.fn();

    render(<UpdatePrompt needRefresh onUpdate={onUpdate} resetSignal={0} />);

    expect(screen.getByRole("status")).toHaveTextContent("A new version of Twype is ready.");

    await user.click(screen.getByRole("button", { name: "Update" }));

    expect(onUpdate).toHaveBeenCalledTimes(1);
  });

  it("dismisses on Later and reappears on focus", async () => {
    const user = userEvent.setup();

    render(<UpdatePrompt needRefresh onUpdate={vi.fn()} resetSignal={0} />);

    await user.click(screen.getByRole("button", { name: "Later" }));

    expect(screen.queryByRole("status")).not.toBeInTheDocument();

    act(() => {
      window.dispatchEvent(new Event("focus"));
    });

    expect(screen.getByRole("status")).toBeInTheDocument();
  });
});
