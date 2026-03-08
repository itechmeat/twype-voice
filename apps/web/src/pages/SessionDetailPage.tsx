import { Link, useParams } from "react-router";
import { ChatMessage } from "../components/ChatMessage";
import { useSessionMessages } from "../hooks/use-session-messages";
import { transformMessageItem } from "../lib/message-transformer";

export function SessionDetailPage() {
  const params = useParams();
  const sessionId = params.sessionId ?? null;
  const { data, error, isError, isPending, refetch } = useSessionMessages(sessionId);

  if (sessionId === null) {
    return (
      <section className="history-page history-page--status">
        <h2>Session details</h2>
        <p>Session ID is missing.</p>
      </section>
    );
  }

  if (isPending) {
    return (
      <section className="history-page history-page--status">
        <h2>Session details</h2>
        <p>Loading session messages...</p>
      </section>
    );
  }

  if (isError) {
    return (
      <section className="history-page history-page--status">
        <h2>Session details</h2>
        <p>{error instanceof Error ? error.message : "Unable to load session messages."}</p>
        <button className="history-page__action" onClick={() => void refetch()} type="button">
          Retry
        </button>
      </section>
    );
  }

  if (data === undefined || data.length === 0) {
    return (
      <section className="history-page history-page--status">
        <h2>Session details</h2>
        <p>No messages were found for this session.</p>
        <Link className="history-page__back-link" to="/history">
          Back to history
        </Link>
      </section>
    );
  }

  const messages = data.map(transformMessageItem);

  return (
    <section className="history-page">
      <header className="history-page__header">
        <div>
          <p className="eyebrow">Replay</p>
          <h2>Session details</h2>
        </div>
        <Link className="history-page__back-link" to="/history">
          Back to history
        </Link>
      </header>

      <div className="history-page__messages">
        {messages.map((message) => (
          <ChatMessage key={message.id} message={message} />
        ))}
      </div>
    </section>
  );
}
