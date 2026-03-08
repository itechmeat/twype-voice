import clsx from "clsx";
import { useTranslation } from "react-i18next";
import type { ChatMessageEntry } from "../../lib/chat-state";
import { SourceIndicator } from "../SourceIndicator";
import styles from "./ChatMessage.module.css";

type ChatMessageProps = {
  message: ChatMessageEntry;
};

const timestampFormatter = new Intl.DateTimeFormat(undefined, {
  hour: "2-digit",
  minute: "2-digit",
});

function formatMessageTimestamp(value: string): string {
  return timestampFormatter.format(new Date(value));
}

function renderMessageBody(message: ChatMessageEntry) {
  switch (message.type) {
    case "user-voice":
    case "user-text":
      return <p className={styles.text}>{message.text}</p>;
    case "agent-plain":
      return (
        <div className={styles.body}>
          <p className={styles.text}>{message.text}</p>
          {message.sourceIds !== undefined && message.sourceIds.length > 0 ? (
            <SourceIndicator chunkIds={message.sourceIds} />
          ) : null}
        </div>
      );
    case "agent-structured":
      return (
        <div className={styles.structured}>
          {message.items.map((item, index) => (
            <div className={styles.structuredItem} key={`${message.id}-${index}`}>
              <p>{item.text}</p>
              {item.chunk_ids.length > 0 ? (
                <SourceIndicator chunkIds={item.chunk_ids} />
              ) : null}
            </div>
          ))}
        </div>
      );
    default: {
      const exhaustiveCheck: never = message;
      throw new Error(`Unsupported chat message: ${String(exhaustiveCheck)}`);
    }
  }
}

export function ChatMessage({ message }: ChatMessageProps) {
  const { t } = useTranslation();
  const actorLabel = message.actor === "user" ? t("chat.you") : t("chat.agentActor");
  let deliveryLabel: string | null = null;
  let isDeliveryFailed = false;

  if (message.type === "user-text") {
    isDeliveryFailed = message.deliveryStatus === "failed";
    deliveryLabel =
      message.deliveryStatus === "failed"
        ? t("chat.failed")
        : message.deliveryStatus === "sending"
          ? t("chat.sending")
          : null;
  }

  return (
    <article className={clsx(styles.root, message.actor === "user" ? styles.user : styles.agent)}>
      <header className={styles.meta}>
        <span>{actorLabel}</span>
        <span className={styles.mode}>{message.mode}</span>
        <time dateTime={message.createdAt}>{formatMessageTimestamp(message.createdAt)}</time>
        {deliveryLabel !== null ? (
          <span className={clsx(styles.delivery, isDeliveryFailed && styles.deliveryFailed)}>
            {deliveryLabel}
          </span>
        ) : null}
      </header>
      {renderMessageBody(message)}
    </article>
  );
}
