import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ChatMessage } from "./ChatMessage";

vi.mock("./SourceIndicator", () => ({
  SourceIndicator: ({ chunkIds }: { chunkIds: string[] }) => (
    <div data-testid="source-indicator">{chunkIds.join(",")}</div>
  ),
}));

describe("ChatMessage", () => {
  it("renders a source indicator for agent-plain messages with sourceIds", () => {
    render(
      <ChatMessage
        message={{
          actor: "agent",
          createdAt: "2026-03-07T10:05:00Z",
          id: "message-1",
          mode: "text",
          sourceIds: ["chunk-1", "chunk-2"],
          text: "Historical reply",
          type: "agent-plain",
        }}
      />,
    );

    expect(screen.getByText("Historical reply")).toBeInTheDocument();
    expect(screen.getByTestId("source-indicator")).toHaveTextContent("chunk-1,chunk-2");
  });
});
