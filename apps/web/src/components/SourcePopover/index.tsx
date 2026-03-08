import { useEffect, useRef, type RefObject } from "react";
import { useTranslation } from "react-i18next";
import FocusTrap from "focus-trap-react";
import type { ResolvedSource, SourceType } from "../../lib/api-sources";
import styles from "./SourcePopover.module.css";

type SourcePopoverProps = {
  rootRef: RefObject<HTMLElement | null>;
  sources: ResolvedSource[];
  filterType?: SourceType | undefined;
  isLoading: boolean;
  isError: boolean;
  onRetry: () => void;
  onClose: () => void;
};

const SOURCE_TYPE_LABEL_KEYS: Record<SourceType, string> = {
  article: "source.typeArticle",
  book: "source.typeBook",
  podcast: "source.typePodcast",
  post: "source.typePost",
  video: "source.typeVideo",
};

function SourceTypeBadge({ sourceType }: { sourceType: SourceType }) {
  const { t } = useTranslation();
  return <span className={styles.type}>{t(SOURCE_TYPE_LABEL_KEYS[sourceType])}</span>;
}

export function SourcePopover({
  rootRef,
  sources,
  filterType,
  isLoading,
  isError,
  onRetry,
  onClose,
}: SourcePopoverProps) {
  const { t } = useTranslation();
  const popoverRef = useRef<HTMLDivElement | null>(null);
  const filtered = filterType !== undefined ? sources.filter((s) => s.sourceType === filterType) : sources;

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
    <FocusTrap
      focusTrapOptions={{
        initialFocus: false,
        fallbackFocus: () => popoverRef.current ?? document.body,
        clickOutsideDeactivates: true,
        escapeDeactivates: false,
        returnFocusOnDeactivate: true,
      }}
    >
      <div
        aria-label={t("source.details")}
        aria-modal="true"
        className={styles.root}
        ref={popoverRef}
        role="dialog"
        tabIndex={-1}
      >
        <div className={styles.header}>
          <h3>{t("source.heading")}</h3>
          <button aria-label={t("source.close")} className={styles.headerButton} onClick={onClose} type="button">
            {t("source.close")}
          </button>
        </div>

        {isLoading ? <p className={styles.state}>{t("source.loadingSources")}</p> : null}

        {!isLoading && isError ? (
          <div className={styles.stateError}>
            <p>{t("source.loadError")}</p>
            <button className={styles.stateButton} onClick={onRetry} type="button">
              {t("common.retry")}
            </button>
          </div>
        ) : null}

        {!isLoading && !isError && filtered.length === 0 ? (
          <p className={styles.state}>{t("source.emptyState")}</p>
        ) : null}

        {!isLoading && !isError && filtered.length > 0 ? (
          <ul className={styles.list}>
            {filtered.map((source) => (
              <li className={styles.item} key={source.chunkId}>
                <div className={styles.itemHeader}>
                  <h4>{source.title}</h4>
                  <SourceTypeBadge sourceType={source.sourceType} />
                </div>
                <dl className={styles.meta}>
                  {source.author !== null ? (
                    <>
                      <dt>{t("source.author")}</dt>
                      <dd>{source.author}</dd>
                    </>
                  ) : null}
                  {source.section !== null ? (
                    <>
                      <dt>{t("source.section")}</dt>
                      <dd>{source.section}</dd>
                    </>
                  ) : null}
                  {source.pageRange !== null ? (
                    <>
                      <dt>{t("source.pageRange")}</dt>
                      <dd>{source.pageRange}</dd>
                    </>
                  ) : null}
                  {source.url !== null ? (
                    <>
                      <dt>{t("source.link")}</dt>
                      <dd>
                        <a href={source.url} rel="noopener noreferrer" target="_blank">
                          {t("source.openSource")}
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
    </FocusTrap>
  );
}
