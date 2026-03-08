import clsx from "clsx";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";
import { useSessionHistory } from "../../hooks/use-session-history";
import type { SessionHistoryItem } from "../../lib/api-sessions";
import styles from "./HistoryPage.module.css";

const PAGE_SIZE = 20;
const DATE_TIME_FORMATTER = new Intl.DateTimeFormat(undefined, {
  dateStyle: "medium",
  timeStyle: "short",
});

function formatDateTime(value: string): string {
  return DATE_TIME_FORMATTER.format(new Date(value));
}

function mergeSessionPages(currentItems: SessionHistoryItem[], nextItems: SessionHistoryItem[]) {
  const itemsById = new Map(currentItems.map((item) => [item.id, item]));

  for (const item of nextItems) {
    itemsById.set(item.id, item);
  }

  return Array.from(itemsById.values()).sort((left, right) =>
    right.startedAt.localeCompare(left.startedAt),
  );
}

export function HistoryPage() {
  const { t } = useTranslation();
  const [offset, setOffset] = useState(0);
  const [items, setItems] = useState<SessionHistoryItem[]>([]);
  const [total, setTotal] = useState(0);
  // Tracks how many rows the backend has paged through, independent of
  // deduplication in the UI list. Without this, overlapping pages cause
  // items.length < actual rows consumed, leading to repeated fetches.
  const [nextOffset, setNextOffset] = useState(0);
  const { data, error, isError, isPending, isFetching, refetch } = useSessionHistory(offset, PAGE_SIZE);

  useEffect(() => {
    if (data === undefined) {
      return;
    }

    setItems((currentItems) => (offset === 0 ? data.items : mergeSessionPages(currentItems, data.items)));
    setTotal(data.total);
    setNextOffset(offset + data.items.length);
  }, [data, offset]);

  if (isPending && items.length === 0) {
    return (
      <section className={clsx(styles.root, styles.statusCard)}>
        <h2>{t("history.heading")}</h2>
        <p>{t("history.loadingHistory")}</p>
      </section>
    );
  }

  if (isError && items.length === 0) {
    return (
      <section className={clsx(styles.root, styles.statusCard)}>
        <h2>{t("history.heading")}</h2>
        <p>{error instanceof Error ? error.message : t("history.loadError")}</p>
        <button className={styles.action} onClick={() => void refetch()} type="button">
          {t("common.retry")}
        </button>
      </section>
    );
  }

  if (items.length === 0) {
    return (
      <section className={clsx(styles.root, styles.statusCard)}>
        <h2>{t("history.heading")}</h2>
        <p>{t("history.emptyState")}</p>
      </section>
    );
  }

  const canLoadMore = nextOffset < total;

  return (
    <section className={styles.root}>
      <header className={styles.header}>
        <div>
          <p className="eyebrow">{t("history.archive")}</p>
          <h2>{t("history.heading")}</h2>
        </div>
        <Link className={styles.backLink} to="/">
          {t("history.backToChat")}
        </Link>
      </header>

      <ul className={styles.list}>
        {items.map((item) => (
          <li className={styles.item} key={item.id}>
            <Link className={styles.sessionLink} to={`/history/${item.id}`}>
              <div>
                <h3>{item.roomName}</h3>
                <p>{t("history.started", { time: formatDateTime(item.startedAt) })}</p>
                <p>{item.endedAt === null ? t("history.inProgress") : t("history.ended", { time: formatDateTime(item.endedAt) })}</p>
              </div>
              <span className={styles.status}>{item.status}</span>
            </Link>
          </li>
        ))}
      </ul>

      {isError ? (
        <div className={styles.footer}>
          <p>{t("history.loadMoreError")}</p>
          <button className={styles.action} onClick={() => void refetch()} type="button">
            {t("common.retry")}
          </button>
        </div>
      ) : null}

      {canLoadMore ? (
        <button
          className={styles.action}
          disabled={isFetching}
          onClick={() => setOffset(nextOffset)}
          type="button"
        >
          {isFetching ? t("common.loading") : t("history.loadMore")}
        </button>
      ) : null}
    </section>
  );
}
