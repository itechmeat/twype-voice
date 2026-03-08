import { useEffect, useRef, type RefObject } from "react";
import type { ResolvedSource, SourceType } from "../lib/api-sources";

type SourcePopoverProps = {
  rootRef: RefObject<HTMLElement | null>;
  sources: ResolvedSource[];
  isLoading: boolean;
  isError: boolean;
  onRetry: () => void;
  onClose: () => void;
};

const SOURCE_TYPE_LABELS: Record<SourceType, string> = {
  article: "Article",
  book: "Book",
  podcast: "Podcast",
  post: "Post",
  video: "Video",
};

function SourceTypeBadge({ sourceType }: { sourceType: SourceType }) {
  return <span className="source-popover__type">{SOURCE_TYPE_LABELS[sourceType]}</span>;
}

export function SourcePopover({
  rootRef,
  sources,
  isLoading,
  isError,
  onRetry,
  onClose,
}: SourcePopoverProps) {
  const popoverRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const handlePointerDown = (event: MouseEvent) => {
      const root = rootRef.current;

      if (root === null) {
        return;
      }

      if (event.target instanceof Node && !root.contains(event.target)) {
        onClose();
      }
    };

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
      }
    };

    document.addEventListener("mousedown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);

    return () => {
      document.removeEventListener("mousedown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [onClose, rootRef]);

  useEffect(() => {
    popoverRef.current?.focus();
  }, []);

  return (
    <div
      aria-label="Source details"
      className="source-popover"
      ref={popoverRef}
      role="dialog"
      tabIndex={-1}
    >
      <div className="source-popover__header">
        <h3>Sources</h3>
        <button aria-label="Close sources" onClick={onClose} type="button">
          Close
        </button>
      </div>

      {isLoading ? <p className="source-popover__state">Loading sources...</p> : null}

      {!isLoading && isError ? (
        <div className="source-popover__state source-popover__state--error">
          <p>Unable to load sources.</p>
          <button onClick={onRetry} type="button">
            Retry
          </button>
        </div>
      ) : null}

      {!isLoading && !isError && sources.length === 0 ? (
        <p className="source-popover__state">No source metadata was found.</p>
      ) : null}

      {!isLoading && !isError && sources.length > 0 ? (
        <ul className="source-popover__list">
          {sources.map((source) => (
            <li className="source-popover__item" key={source.chunkId}>
              <div className="source-popover__item-header">
                <h4>{source.title}</h4>
                <SourceTypeBadge sourceType={source.sourceType} />
              </div>
              <dl className="source-popover__meta">
                {source.author !== null ? (
                  <>
                    <dt>Author</dt>
                    <dd>{source.author}</dd>
                  </>
                ) : null}
                {source.section !== null ? (
                  <>
                    <dt>Section</dt>
                    <dd>{source.section}</dd>
                  </>
                ) : null}
                {source.pageRange !== null ? (
                  <>
                    <dt>Page range</dt>
                    <dd>{source.pageRange}</dd>
                  </>
                ) : null}
                {source.url !== null ? (
                  <>
                    <dt>Link</dt>
                    <dd>
                      <a href={source.url} rel="noopener noreferrer" target="_blank">
                        Open source
                      </a>
                    </dd>
                  </>
                ) : null}
              </dl>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
