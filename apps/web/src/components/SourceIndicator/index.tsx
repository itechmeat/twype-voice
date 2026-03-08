import { useCallback, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { useResolveSources } from "../../hooks/use-resolve-sources";
import type { SourceType } from "../../lib/api-sources";
import { SourcePopover } from "../SourcePopover";
import styles from "./SourceIndicator.module.css";

type SourceIndicatorProps = {
  chunkIds: string[];
};

const SOURCE_TYPE_ORDER: SourceType[] = ["book", "article", "video", "podcast", "post"];

function CitationIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24">
      <path
        d="M7 6.25h8.5A2.25 2.25 0 0 1 17.75 8.5v9.25a.75.75 0 0 1-1.2.6L13 15.75H7A2.75 2.75 0 0 1 4.25 13V9A2.75 2.75 0 0 1 7 6.25Z"
        fill="currentColor"
      />
      <path d="M8.5 9.25h5v1.5h-5Zm0 3h3.5v1.5H8.5Z" fill="#f8fafc" />
    </svg>
  );
}

function BookIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24">
      <path
        d="M6.5 4.5h9.25A2.25 2.25 0 0 1 18 6.75V18a1 1 0 0 1-1.5.87l-2.5-1.43-2.5 1.43L9 17.44l-2.5 1.43A1 1 0 0 1 5 18V6A1.5 1.5 0 0 1 6.5 4.5Z"
        fill="currentColor"
      />
    </svg>
  );
}

function VideoIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24">
      <path
        d="M5.75 6.25h8.5A2.25 2.25 0 0 1 16.5 8.5v7a2.25 2.25 0 0 1-2.25 2.25h-8.5A2.25 2.25 0 0 1 3.5 15.5v-7a2.25 2.25 0 0 1 2.25-2.25Zm12.6 2.1 2.15-1.4a.75.75 0 0 1 1.16.63v8.84a.75.75 0 0 1-1.16.63l-2.15-1.4Z"
        fill="currentColor"
      />
    </svg>
  );
}

function PodcastIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24">
      <path
        d="M12 4.25a6.75 6.75 0 0 1 4.79 11.51.75.75 0 1 1-1.06-1.06A5.25 5.25 0 1 0 6.27 14.7a.75.75 0 0 1-1.06 1.06A6.75 6.75 0 0 1 12 4.25Zm0 3a3.75 3.75 0 0 1 2.65 6.4.75.75 0 1 1-1.06-1.06 2.25 2.25 0 1 0-3.18 0 .75.75 0 1 1-1.06 1.06A3.75 3.75 0 0 1 12 7.25Zm0 6.25a1.75 1.75 0 0 1 1.75 1.75v2.5a1.75 1.75 0 1 1-3.5 0v-2.5A1.75 1.75 0 0 1 12 13.5Z"
        fill="currentColor"
      />
    </svg>
  );
}

function ArticleIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24">
      <path
        d="M6 5.25h12A1.75 1.75 0 0 1 19.75 7v10A1.75 1.75 0 0 1 18 18.75H6A1.75 1.75 0 0 1 4.25 17V7A1.75 1.75 0 0 1 6 5.25Z"
        fill="currentColor"
      />
      <path d="M8 8h8v1.5H8Zm0 3h8v1.5H8Zm0 3h5v1.5H8Z" fill="#f8fafc" />
    </svg>
  );
}

function PostIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24">
      <path
        d="M6.5 5.25h11A1.75 1.75 0 0 1 19.25 7v10a1.75 1.75 0 0 1-1.75 1.75h-11A1.75 1.75 0 0 1 4.75 17V7A1.75 1.75 0 0 1 6.5 5.25Zm1.25 2.5v3.5H11v-3.5Zm0 5v1.5h8.5v-1.5Z"
        fill="currentColor"
      />
    </svg>
  );
}

function SourceTypeIcon({ sourceType }: { sourceType: SourceType | "generic" }) {
  switch (sourceType) {
    case "book":
      return <BookIcon />;
    case "video":
      return <VideoIcon />;
    case "podcast":
      return <PodcastIcon />;
    case "article":
      return <ArticleIcon />;
    case "post":
      return <PostIcon />;
    case "generic":
      return <CitationIcon />;
    default: {
      const exhaustiveCheck: never = sourceType;
      throw new Error(`Unsupported source type: ${String(exhaustiveCheck)}`);
    }
  }
}

const ICON_LABEL_KEYS: Record<SourceType | "generic", string> = {
  generic: "source.viewSources",
  article: "source.viewArticleSources",
  book: "source.viewBookSources",
  podcast: "source.viewPodcastSources",
  post: "source.viewPostSources",
  video: "source.viewVideoSources",
};

export function SourceIndicator({ chunkIds }: SourceIndicatorProps) {
  const { t } = useTranslation();
  const rootRef = useRef<HTMLDivElement | null>(null);
  const [isOpen, setIsOpen] = useState(false);
  const [filterType, setFilterType] = useState<SourceType | undefined>(undefined);
  const { data, isError, isFetching, refetch } = useResolveSources(chunkIds);

  const sourceTypes = useMemo(() => {
    if (data === undefined || data.length === 0) {
      return ["generic"] as const;
    }

    const uniqueTypes = new Set(data.map((source) => source.sourceType));
    const orderedTypes = SOURCE_TYPE_ORDER.filter((sourceType) => uniqueTypes.has(sourceType));

    return orderedTypes.length > 0 ? orderedTypes : (["generic"] as const);
  }, [data]);

  const handleOpen = useCallback(
    (sourceType: SourceType | "generic") => {
      // "generic" means show all sources; a specific type filters to that type only
      setFilterType(sourceType === "generic" ? undefined : sourceType);
      setIsOpen(true);

      if (data === undefined && !isFetching) {
        void refetch();
      }
    },
    [data, isFetching, refetch],
  );

  const handleClose = useCallback(() => {
    setIsOpen(false);
  }, []);

  const handleRetry = useCallback(() => {
    void refetch();
  }, [refetch]);

  return (
    <div className={styles.root} ref={rootRef}>
      <div className={styles.buttons}>
        {sourceTypes.map((sourceType) => (
          <button
            aria-label={t(ICON_LABEL_KEYS[sourceType])}
            className={styles.button}
            key={sourceType}
            onClick={() => handleOpen(sourceType)}
            type="button"
          >
            <SourceTypeIcon sourceType={sourceType} />
          </button>
        ))}
      </div>

      {isOpen ? (
        <SourcePopover
          filterType={filterType}
          isError={isError}
          isLoading={isFetching}
          onClose={handleClose}
          onRetry={handleRetry}
          rootRef={rootRef}
          sources={data ?? []}
        />
      ) : null}
    </div>
  );
}
