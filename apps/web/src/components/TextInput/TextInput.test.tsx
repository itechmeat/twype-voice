import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { TextInput } from ".";

describe("TextInput", () => {
  it("submits on Enter and clears the field", async () => {
    const user = userEvent.setup();
    const onSend = vi.fn<(text: string) => Promise<void>>().mockResolvedValue();

    render(<TextInput disabled={false} onSend={onSend} />);

    await user.type(screen.getByLabelText("Message"), "Hello{enter}");

    expect(onSend).toHaveBeenCalledWith("Hello");
    expect(screen.getByLabelText("Message")).toHaveValue("");
  });

  it("keeps newline on Shift+Enter", async () => {
    const user = userEvent.setup();
    const onSend = vi.fn();

    render(<TextInput disabled={false} onSend={onSend} />);

    await user.type(screen.getByLabelText("Message"), "Hello{shift>}{enter}{/shift}World");

    expect(onSend).not.toHaveBeenCalled();
    expect(screen.getByLabelText("Message")).toHaveValue("Hello\nWorld");
  });

  it("prevents empty submission and respects disabled state", async () => {
    const user = userEvent.setup();
    const onSend = vi.fn();

    const { rerender } = render(<TextInput disabled={false} onSend={onSend} />);

    await user.type(screen.getByLabelText("Message"), "   ");
    expect(screen.getByRole("button", { name: "Send" })).toBeDisabled();

    rerender(<TextInput disabled onSend={onSend} />);

    expect(screen.getByLabelText("Message")).toBeDisabled();
    expect(screen.getByRole("button", { name: "Send" })).toBeDisabled();
  });
});
