import { useRef, type ComponentProps } from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { SourceIndicator } from "./SourceIndicator";
import { SourcePopover } from "./SourcePopover";

const useResolveSourcesMock = vi.fn();

vi.mock("../hooks/use-resolve-sources", () => ({
  useResolveSources: (chunkIds: string[]) => useResolveSourcesMock(chunkIds),
}));

describe("SourceIndicator", () => {
  beforeEach(() => {
    useResolveSourcesMock.mockReset();
  });

  it("renders a generic source button before resolution and refetches on click", async () => {
    const refetch = vi.fn().mockResolvedValue(undefined);
    const user = userEvent.setup();
    useResolveSourcesMock.mockReturnValue({
      data: undefined,
      isError: false,
      isFetching: false,
      refetch,
    });

    render(<SourceIndicator chunkIds={["chunk-1"]} />);

    await user.click(screen.getByRole("button", { name: "View sources" }));

    expect(refetch).toHaveBeenCalledTimes(1);
    expect(screen.getByRole("dialog", { name: "Source details" })).toBeInTheDocument();
  });

  it("renders one button per unique resolved source type", () => {
    useResolveSourcesMock.mockReturnValue({
      data: [
        {
          author: null,
          chunkId: "chunk-1",
          pageRange: null,
          section: null,
          sourceType: "book",
          title: "Medical Guide",
          url: null,
        },
        {
          author: null,
          chunkId: "chunk-2",
          pageRange: null,
          section: null,
          sourceType: "video",
          title: "Explainer",
          url: null,
        },
      ],
      isError: false,
      isFetching: false,
      refetch: vi.fn(),
    });

    render(<SourceIndicator chunkIds={["chunk-1", "chunk-2"]} />);

    expect(screen.getByRole("button", { name: "View book sources" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "View video sources" })).toBeInTheDocument();
  });
});

function SourcePopoverHarness(props: Omit<ComponentProps<typeof SourcePopover>, "rootRef">) {
  const rootRef = useRef<HTMLDivElement | null>(null);

  return (
    <div>
      <button type="button">Outside</button>
      <div ref={rootRef}>
        <SourcePopover {...props} rootRef={rootRef} />
      </div>
    </div>
  );
}

describe("SourcePopover", () => {
  it("renders loading and error states, and retries failed requests", async () => {
    const user = userEvent.setup();
    const onRetry = vi.fn();
    const onClose = vi.fn();

    const { rerender } = render(
      <SourcePopoverHarness
        isError={false}
        isLoading
        onClose={onClose}
        onRetry={onRetry}
        sources={[]}
      />,
    );

    expect(screen.getByText("Loading sources...")).toBeInTheDocument();

    rerender(
      <SourcePopoverHarness
        isError
        isLoading={false}
        onClose={onClose}
        onRetry={onRetry}
        sources={[]}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Retry" }));
    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  it("dismisses on Escape, outside click, and close button", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();

    render(
      <SourcePopoverHarness
        isError={false}
        isLoading={false}
        onClose={onClose}
        onRetry={vi.fn()}
        sources={[
          {
            author: "Dr. Smith",
            chunkId: "chunk-1",
            pageRange: "45-47",
            section: "Chapter 3",
            sourceType: "book",
            title: "Medical Guide",
            url: "https://example.com/source",
          },
        ]}
      />,
    );

    await user.keyboard("{Escape}");
    await user.click(screen.getByRole("button", { name: "Outside" }));
    await user.click(screen.getByRole("button", { name: "Close sources" }));

    expect(onClose).toHaveBeenCalledTimes(3);
    expect(screen.getByRole("link", { name: "Open source" })).toHaveAttribute(
      "href",
      "https://example.com/source",
    );
  });
});
