import type { ChatMessageEntry } from "../lib/chat-state";
import { SourceIndicator } from "./SourceIndicator";

type ChatMessageProps = {
  message: ChatMessageEntry;
};

function formatMessageTimestamp(value: string): string {
  return new Intl.DateTimeFormat(undefined, {
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function renderMessageBody(message: ChatMessageEntry) {
  switch (message.type) {
    case "user-voice":
    case "user-text":
      return <p className="chat-message__text">{message.text}</p>;
    case "agent-plain":
      return (
        <div className="chat-message__body">
          <p className="chat-message__text">{message.text}</p>
          {message.sourceIds !== undefined && message.sourceIds.length > 0 ? (
            <SourceIndicator chunkIds={message.sourceIds} />
          ) : null}
        </div>
      );
    case "agent-structured":
      return (
        <div className="chat-message__structured">
          {message.items.map((item, index) => (
            <div className="chat-message__structured-item" key={`${message.id}-${index}`}>
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
  const actorLabel = message.actor === "user" ? "You" : "Agent";
  let deliveryLabel: string | null = null;
  let deliveryStatusClass = "";

  if (message.type === "user-text") {
    deliveryStatusClass = `chat-message__delivery--${message.deliveryStatus}`;
    deliveryLabel =
      message.deliveryStatus === "failed"
        ? "Failed"
        : message.deliveryStatus === "sending"
          ? "Sending"
          : null;
  }

  return (
    <article className={`chat-message chat-message--${message.actor}`}>
      <header className="chat-message__meta">
        <span>{actorLabel}</span>
        <span className="chat-message__mode">{message.mode}</span>
        <time dateTime={message.createdAt}>{formatMessageTimestamp(message.createdAt)}</time>
        {deliveryLabel !== null ? (
          <span className={`chat-message__delivery ${deliveryStatusClass}`}>
            {deliveryLabel}
          </span>
        ) : null}
      </header>
      {renderMessageBody(message)}
    </article>
  );
}
