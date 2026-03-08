import { useEffect, useRef, useState } from "react";
import type { ChatMessageEntry, StreamingResponse } from "../lib/chat-state";
import { ChatMessage } from "./ChatMessage";
import { InterimTranscript } from "./InterimTranscript";

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
    return <p className="chat-message__text">{streamingResponse.text}</p>;
  }

  return (
    <div className="chat-message__structured">
      {streamingResponse.items.map((item, index) => (
        <div className="chat-message__structured-item" key={`streaming-${index}`}>
          <p>{item.text}</p>
        </div>
      ))}
    </div>
  );
}

export function ChatFeed({ messages, interimTranscript, streamingResponse }: ChatFeedProps) {
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const previousMessageCountRef = useRef(messages.length);
  const previousInterimTranscriptRef = useRef(interimTranscript);
  const previousStreamingSignatureRef = useRef(JSON.stringify(streamingResponse));
  const [isPinnedToBottom, setIsPinnedToBottom] = useState(true);
  const [hasUnreadMessages, setHasUnreadMessages] = useState(false);

  useEffect(() => {
    const element = scrollRef.current;

    if (element === null) {
      return;
    }

    const nextStreamingSignature = JSON.stringify(streamingResponse);
    const hasNewContent =
      messages.length > previousMessageCountRef.current ||
      (interimTranscript !== null &&
        interimTranscript.length > 0 &&
        interimTranscript !== previousInterimTranscriptRef.current) ||
      (streamingResponse !== null && nextStreamingSignature !== previousStreamingSignatureRef.current);

    previousMessageCountRef.current = messages.length;
    previousInterimTranscriptRef.current = interimTranscript;
    previousStreamingSignatureRef.current = nextStreamingSignature;

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
    <section className="chat-feed">
      <div
        aria-label="Conversation"
        aria-live="polite"
        aria-relevant="additions text"
        className="chat-feed__scroll"
        data-testid="chat-feed-scroll"
        onScroll={handleScroll}
        ref={scrollRef}
        role="log"
      >
        {messages.length === 0 && interimTranscript === null && streamingResponse === null ? (
          <p className="chat-feed__empty">Start speaking or send a text message to begin.</p>
        ) : null}

        {messages.map((message) => (
          <ChatMessage key={message.id} message={message} />
        ))}

        {streamingResponse !== null ? (
          <article className="chat-message chat-message--agent chat-message--streaming">
            <header className="chat-message__meta">
              <span>Agent</span>
              <span className="chat-message__mode">live</span>
            </header>
            {renderStreamingResponse(streamingResponse)}
          </article>
        ) : null}

        <InterimTranscript text={interimTranscript} />
      </div>

      <div aria-live="polite">
        {hasUnreadMessages ? (
          <button className="chat-feed__jump" onClick={jumpToLatest} type="button">
            New messages
          </button>
        ) : null}
      </div>
    </section>
  );
}
