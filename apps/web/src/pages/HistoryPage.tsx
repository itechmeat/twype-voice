import { useEffect, useState } from "react";
import { Link } from "react-router";
import { useSessionHistory } from "../hooks/use-session-history";
import type { SessionHistoryItem } from "../lib/api-sessions";

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
  const [offset, setOffset] = useState(0);
  const [items, setItems] = useState<SessionHistoryItem[]>([]);
  const [total, setTotal] = useState(0);
  const { data, error, isError, isPending, isFetching, refetch } = useSessionHistory(offset, PAGE_SIZE);

  useEffect(() => {
    if (data === undefined) {
      return;
    }

    setItems((currentItems) => (offset === 0 ? data.items : mergeSessionPages(currentItems, data.items)));
    setTotal(data.total);
  }, [data, offset]);

  if (isPending && items.length === 0) {
    return (
      <section className="history-page history-page--status">
        <h2>Session history</h2>
        <p>Loading your previous sessions...</p>
      </section>
    );
  }

  if (isError && items.length === 0) {
    return (
      <section className="history-page history-page--status">
        <h2>Session history</h2>
        <p>{error instanceof Error ? error.message : "Unable to load session history."}</p>
        <button className="history-page__action" onClick={() => void refetch()} type="button">
          Retry
        </button>
      </section>
    );
  }

  if (items.length === 0) {
    return (
      <section className="history-page history-page--status">
        <h2>Session history</h2>
        <p>No past sessions are available yet.</p>
      </section>
    );
  }

  const canLoadMore = items.length < total;

  return (
    <section className="history-page">
      <header className="history-page__header">
        <div>
          <p className="eyebrow">Archive</p>
          <h2>Session history</h2>
        </div>
        <Link className="history-page__back-link" to="/">
          Back to chat
        </Link>
      </header>

      <ul className="history-page__list">
        {items.map((item) => (
          <li className="history-page__item" key={item.id}>
            <Link className="history-page__session-link" to={`/history/${item.id}`}>
              <div>
                <h3>{item.roomName}</h3>
                <p>Started {formatDateTime(item.startedAt)}</p>
                <p>{item.endedAt === null ? "In progress" : `Ended ${formatDateTime(item.endedAt)}`}</p>
              </div>
              <span className="history-page__status">{item.status}</span>
            </Link>
          </li>
        ))}
      </ul>

      {isError ? (
        <div className="history-page__footer">
          <p>Unable to load more sessions.</p>
          <button className="history-page__action" onClick={() => void refetch()} type="button">
            Retry
          </button>
        </div>
      ) : null}

      {canLoadMore ? (
        <button
          className="history-page__action"
          disabled={isFetching}
          onClick={() => setOffset(items.length)}
          type="button"
        >
          {isFetching ? "Loading..." : "Load more"}
        </button>
      ) : null}
    </section>
  );
}
