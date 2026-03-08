import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ChatFeed } from "./ChatFeed";

describe("ChatFeed", () => {
  it("renders chat messages and interim transcript", () => {
    render(
      <ChatFeed
        interimTranscript="Working on it"
        messages={[
          {
            actor: "user",
            createdAt: "2026-03-07T10:00:00.000Z",
            deliveryStatus: "sent",
            id: "message-1",
            mode: "text",
            text: "Hello",
            type: "user-text",
          },
          {
            actor: "agent",
            createdAt: "2026-03-07T10:00:01.000Z",
            id: "message-2",
            mode: "text",
            text: "Hi there",
            type: "agent-plain",
          },
        ]}
        streamingResponse={null}
      />,
    );

    expect(screen.getByText("Hello")).toBeInTheDocument();
    expect(screen.getByText("Hi there")).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("Working on it");
  });

  it("shows a jump button when new messages arrive while scrolled up", () => {
    const scrollTo = vi.fn();

    const { rerender } = render(
      <ChatFeed
        interimTranscript={null}
        messages={[
          {
            actor: "user",
            createdAt: "2026-03-07T10:00:00.000Z",
            deliveryStatus: "sent",
            id: "message-1",
            mode: "text",
            text: "Hello",
            type: "user-text",
          },
        ]}
        streamingResponse={null}
      />,
    );

    const scrollContainer = screen.getByTestId("chat-feed-scroll");

    Object.defineProperty(scrollContainer, "scrollHeight", {
      configurable: true,
      value: 400,
    });
    Object.defineProperty(scrollContainer, "clientHeight", {
      configurable: true,
      value: 100,
    });
    Object.defineProperty(scrollContainer, "scrollTop", {
      configurable: true,
      value: 0,
      writable: true,
    });
    scrollContainer.scrollTo = scrollTo;

    fireEvent.scroll(scrollContainer);

    rerender(
      <ChatFeed
        interimTranscript={null}
        messages={[
          {
            actor: "user",
            createdAt: "2026-03-07T10:00:00.000Z",
            deliveryStatus: "sent",
            id: "message-1",
            mode: "text",
            text: "Hello",
            type: "user-text",
          },
          {
            actor: "agent",
            createdAt: "2026-03-07T10:00:01.000Z",
            id: "message-2",
            mode: "text",
            text: "New reply",
            type: "agent-plain",
          },
        ]}
        streamingResponse={null}
      />,
    );

    const jumpButton = screen.getByRole("button", { name: "New messages" });
    expect(jumpButton).toBeInTheDocument();

    fireEvent.click(jumpButton);
    expect(scrollTo).toHaveBeenCalled();
  });

  it("does not show unread button on rerender without new content", () => {
    const { rerender } = render(
      <ChatFeed
        interimTranscript={null}
        messages={[
          {
            actor: "user",
            createdAt: "2026-03-07T10:00:00.000Z",
            deliveryStatus: "sent",
            id: "message-1",
            mode: "text",
            text: "Hello",
            type: "user-text",
          },
        ]}
        streamingResponse={null}
      />,
    );

    rerender(
      <ChatFeed
        interimTranscript={null}
        messages={[
          {
            actor: "user",
            createdAt: "2026-03-07T10:00:00.000Z",
            deliveryStatus: "sent",
            id: "message-1",
            mode: "text",
            text: "Hello",
            type: "user-text",
          },
        ]}
        streamingResponse={null}
      />,
    );

    expect(screen.queryByRole("button", { name: "New messages" })).not.toBeInTheDocument();
  });
});
