import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import type { ChatMessageEntry, StreamingResponse } from "../../lib/chat-state";
import { ChatMessage } from "../ChatMessage";
import { InterimTranscript } from "../InterimTranscript";
import chatMessageStyles from "../ChatMessage/ChatMessage.module.css";
import styles from "./ChatFeed.module.css";

type ChatFeedProps = {
  messages: ChatMessageEntry[];
  interimTranscript: string | null;
  streamingResponse: StreamingResponse | null;
};

function scrollToBottom(element: HTMLDivElement) {
  if (typeof element.scrollTo === "function") {
    element.scrollTo({ top: element.scrollHeight, behavior: "smooth" });
    return;
  }

  element.scrollTop = element.scrollHeight;
}

function renderStreamingResponse(streamingResponse: StreamingResponse) {
  if (streamingResponse.type === "plain") {
    return <p className={chatMessageStyles.text}>{streamingResponse.text}</p>;
  }

  return (
    <div className={chatMessageStyles.structured}>
      {streamingResponse.items.map((item, index) => (
        <div className={chatMessageStyles.structuredItem} key={`streaming-${index}`}>
          <p>{item.text}</p>
        </div>
      ))}
    </div>
  );
}

export function ChatFeed({ messages, interimTranscript, streamingResponse }: ChatFeedProps) {
  const { t } = useTranslation();
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const previousMessageCountRef = useRef(messages.length);
  const previousInterimTranscriptRef = useRef(interimTranscript);
  const previousStreamingResponseRef = useRef(streamingResponse);
  const [isPinnedToBottom, setIsPinnedToBottom] = useState(true);
  const [hasUnreadMessages, setHasUnreadMessages] = useState(false);

  useEffect(() => {
    const element = scrollRef.current;

    if (element === null) {
      return;
    }

    const hasNewContent =
      messages.length > previousMessageCountRef.current ||
      (interimTranscript !== null &&
        interimTranscript.length > 0 &&
        interimTranscript !== previousInterimTranscriptRef.current) ||
      streamingResponse !== previousStreamingResponseRef.current;

    previousMessageCountRef.current = messages.length;
    previousInterimTranscriptRef.current = interimTranscript;
    previousStreamingResponseRef.current = streamingResponse;

    if (isPinnedToBottom) {
      scrollToBottom(element);
      setHasUnreadMessages(false);
      return;
    }

    if (hasNewContent) {
      setHasUnreadMessages(true);
    }
  }, [interimTranscript, isPinnedToBottom, messages, streamingResponse]);

  const handleScroll = () => {
    const element = scrollRef.current;

    if (element === null) {
      return;
    }

    const distanceFromBottom = element.scrollHeight - element.scrollTop - element.clientHeight;
    const nextPinnedState = distanceFromBottom < 24;

    setIsPinnedToBottom(nextPinnedState);

    if (nextPinnedState) {
      setHasUnreadMessages(false);
    }
  };

  const jumpToLatest = () => {
    const element = scrollRef.current;

    if (element === null) {
      return;
    }

    scrollToBottom(element);
    setIsPinnedToBottom(true);
    setHasUnreadMessages(false);
  };

  return (
    <section className={styles.root}>
      <div
        aria-label={t("chat.conversation")}
        aria-live="polite"
        aria-relevant="additions text"
        className={styles.scroll}
        data-testid="chat-feed-scroll"
        onScroll={handleScroll}
        ref={scrollRef}
        role="log"
      >
        {messages.length === 0 && interimTranscript === null && streamingResponse === null ? (
          <p className={styles.empty}>{t("chat.emptyState")}</p>
        ) : null}

        {messages.map((message) => (
          <ChatMessage key={message.id} message={message} />
        ))}

        {streamingResponse !== null ? (
          <article className={styles.streamingMessage}>
            <header className={chatMessageStyles.meta}>
              <span>{t("chat.agentActor")}</span>
              <span className={chatMessageStyles.mode}>{t("chat.live")}</span>
            </header>
            {renderStreamingResponse(streamingResponse)}
          </article>
        ) : null}

        <InterimTranscript text={interimTranscript} />
      </div>

      <div aria-live="polite">
        {hasUnreadMessages ? (
          <button className={styles.jump} onClick={jumpToLatest} type="button">
            {t("chat.newMessages")}
          </button>
        ) : null}
      </div>
    </section>
  );
}
