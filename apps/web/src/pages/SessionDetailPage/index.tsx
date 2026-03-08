import clsx from "clsx";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router";
import { ChatMessage } from "../../components/ChatMessage";
import { useSessionMessages } from "../../hooks/use-session-messages";
import { transformMessageItem } from "../../lib/message-transformer";
import historyStyles from "../HistoryPage/HistoryPage.module.css";

export function SessionDetailPage() {
  const { t } = useTranslation();
  const params = useParams();
  const sessionId = params.sessionId ?? null;
  const { data, error, isError, isPending, refetch } = useSessionMessages(sessionId);

  if (sessionId === null) {
    return (
      <section className={clsx(historyStyles.root, historyStyles.statusCard)}>
        <h2>{t("history.sessionDetails")}</h2>
        <p>{t("history.sessionIdMissing")}</p>
      </section>
    );
  }

  if (isPending) {
    return (
      <section className={clsx(historyStyles.root, historyStyles.statusCard)}>
        <h2>{t("history.sessionDetails")}</h2>
        <p>{t("history.loadingMessages")}</p>
      </section>
    );
  }

  if (isError) {
    return (
      <section className={clsx(historyStyles.root, historyStyles.statusCard)}>
        <h2>{t("history.sessionDetails")}</h2>
        <p>{error instanceof Error ? error.message : t("history.messagesLoadError")}</p>
        <button className={historyStyles.action} onClick={() => void refetch()} type="button">
          {t("common.retry")}
        </button>
      </section>
    );
  }

  if (data === undefined || data.length === 0) {
    return (
      <section className={clsx(historyStyles.root, historyStyles.statusCard)}>
        <h2>{t("history.sessionDetails")}</h2>
        <p>{t("history.messagesEmpty")}</p>
        <Link className={historyStyles.backLink} to="/history">
          {t("history.backToHistory")}
        </Link>
      </section>
    );
  }

  const messages = data.map(transformMessageItem);

  return (
    <section className={historyStyles.root}>
      <header className={historyStyles.header}>
        <div>
          <p className="eyebrow">{t("history.replay")}</p>
          <h2>{t("history.sessionDetails")}</h2>
        </div>
        <Link className={historyStyles.backLink} to="/history">
          {t("history.backToHistory")}
        </Link>
      </header>

      <div className={historyStyles.messages}>
        {messages.map((message) => (
          <ChatMessage key={message.id} message={message} />
        ))}
      </div>
    </section>
  );
}
