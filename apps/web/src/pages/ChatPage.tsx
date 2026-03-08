import {
  LiveKitRoom,
  RoomAudioRenderer,
  useConnectionState,
} from "@livekit/components-react";
import { startTransition, useEffect, useReducer, useRef, useState } from "react";
import { ConnectionState } from "livekit-client";
import { AgentStateIndicator } from "../components/AgentStateIndicator";
import { AudioLevelIndicator } from "../components/AudioLevelIndicator";
import { ChatFeed } from "../components/ChatFeed";
import { MicToggle } from "../components/MicToggle";
import { TextInput } from "../components/TextInput";
import { useDataChannel } from "../hooks/use-data-channel";
import { useSendDataChannel } from "../hooks/use-send-data-channel";
import { useStartSession } from "../hooks/use-start-session";
import {
  chatStateReducer,
  createInitialChatState,
  createMessageId,
  type ChatMode,
} from "../lib/chat-state";
import { resolveLiveKitUrl } from "../lib/livekit-url";
import type { StructuredResponseItem } from "../lib/livekit-messages";

type ChatRoomProps = {
  onReconnect: () => void;
  roomName: string;
  sessionId: string;
};

function createTimestamp(): string {
  return new Date().toISOString();
}

function normalizeStructuredItems(items: StructuredResponseItem[]): StructuredResponseItem[] {
  return items.map((item) => ({
    chunk_ids: item.chunk_ids,
    text: item.text,
  }));
}

export function ConnectionStateBanner({ onReconnect }: { onReconnect: () => void }) {
  const connectionState = useConnectionState();

  if (
    connectionState !== ConnectionState.Connecting &&
    connectionState !== ConnectionState.Reconnecting &&
    connectionState !== ConnectionState.SignalReconnecting &&
    connectionState !== ConnectionState.Disconnected
  ) {
    return null;
  }

  const label =
    connectionState === ConnectionState.Disconnected
      ? "Disconnected from the room."
      : connectionState === ConnectionState.Connecting
        ? "Connecting to the room..."
        : "Reconnecting to the room...";

  return (
    <div className={`connection-banner connection-banner--${connectionState}`}>
      <p>{label}</p>
      {connectionState === ConnectionState.Disconnected ? (
        <button className="connection-banner__button" onClick={onReconnect} type="button">
          Reconnect
        </button>
      ) : null}
    </div>
  );
}

function ChatRoom({ onReconnect, roomName, sessionId }: ChatRoomProps) {
  const connectionState = useConnectionState();
  const [chatState, dispatch] = useReducer(chatStateReducer, undefined, createInitialChatState);
  const modeRef = useRef<ChatMode>("voice");
  const sendDataChannelMessage = useSendDataChannel();

  useEffect(() => {
    modeRef.current = chatState.currentMode;
  }, [chatState.currentMode]);

  useDataChannel({
    chat_response: (message) => {
      if (!message.is_final) {
        dispatch({
          type: "set-streaming-response",
          streamingResponse: {
            text: message.text,
            type: "plain",
          },
        });
        return;
      }

      startTransition(() => {
        dispatch({ type: "clear-streaming-response" });
        dispatch({
          type: "add-message",
          message: {
            actor: "agent",
            createdAt: createTimestamp(),
            id: message.message_id ?? createMessageId("agent-plain"),
            mode: modeRef.current,
            text: message.text,
            type: "agent-plain",
          },
        });
      });
    },
    emotional_state: (message) => {
      const emotionalState = {
        arousal: message.arousal,
        is_refined: message.is_refined,
        quadrant: message.quadrant,
        trend_arousal: message.trend_arousal,
        trend_valence: message.trend_valence,
        valence: message.valence,
        ...(message.message_id === undefined ? {} : { message_id: message.message_id }),
      };

      dispatch({
        type: "set-emotional-state",
        emotionalState,
      });
    },
    structured_response: (message) => {
      const items = normalizeStructuredItems(message.items);

      if (!message.is_final) {
        dispatch({
          type: "set-streaming-response",
          streamingResponse: {
            items,
            type: "structured",
          },
        });
        return;
      }

      startTransition(() => {
        dispatch({ type: "clear-streaming-response" });
        dispatch({
          type: "add-message",
          message: {
            actor: "agent",
            createdAt: createTimestamp(),
            id: message.message_id ?? createMessageId("agent-structured"),
            items,
            mode: modeRef.current,
            type: "agent-structured",
          },
        });
      });
    },
    transcript: (message) => {
      if (message.role !== "user") {
        return;
      }

      if (!message.is_final) {
        dispatch({
          type: "set-interim-transcript",
          text: message.text,
        });
        return;
      }

      startTransition(() => {
        dispatch({ type: "clear-interim-transcript" });
        dispatch({
          type: "add-message",
          message: {
            actor: "user",
            createdAt: createTimestamp(),
            id: message.message_id ?? createMessageId("user-voice"),
            mode: "voice",
            text: message.text,
            type: "user-voice",
          },
        });
      });
    },
  });

  const handleSendMessage = async (text: string) => {
    const messageId = createMessageId("user-text");

    dispatch({
      type: "add-message",
      message: {
        actor: "user",
        createdAt: createTimestamp(),
        deliveryStatus: "sending",
        id: messageId,
        mode: "text",
        text,
        type: "user-text",
      },
    });

    try {
      const wasSent = await sendDataChannelMessage("chat_message", { text });

      dispatch({
        type: "update-user-text-message-status",
        id: messageId,
        deliveryStatus: wasSent ? "sent" : "failed",
      });
    } catch {
      dispatch({
        type: "update-user-text-message-status",
        id: messageId,
        deliveryStatus: "failed",
      });
    }
  };

  return (
    <section className="chat-page" data-session-id={sessionId}>
      <ConnectionStateBanner onReconnect={onReconnect} />

      <div className="chat-page__grid">
        <aside className="chat-sidebar">
          <div className="chat-sidebar__card">
            <p className="eyebrow">Room</p>
            <h2>Live conversation</h2>
            <p>{roomName}</p>
          </div>

          <div className="chat-sidebar__card">
            <p className="eyebrow">Agent</p>
            <AgentStateIndicator />
            <AudioLevelIndicator source="agent" />
          </div>

          <div className="chat-sidebar__card">
            <p className="eyebrow">Voice</p>
            <MicToggle />
            <AudioLevelIndicator source="local" />
          </div>
        </aside>

        <div className="chat-panel">
          <header className="chat-panel__header">
            <div>
              <p className="eyebrow">Session</p>
              <h2>Chat workspace</h2>
            </div>
            <p className="chat-panel__status">
              Connection:{" "}
              <strong>
                {connectionState === ConnectionState.SignalReconnecting
                  ? "reconnecting"
                  : connectionState}
              </strong>
            </p>
          </header>

          <ChatFeed
            interimTranscript={chatState.interimTranscript}
            messages={chatState.messages}
            streamingResponse={chatState.streamingResponse}
          />

          <TextInput
            disabled={connectionState !== ConnectionState.Connected}
            onSend={handleSendMessage}
          />
        </div>
      </div>
    </section>
  );
}

function LoadingCard({ message }: { message: string }) {
  return (
    <section className="chat-status-card">
      <p className="eyebrow">Twype</p>
      <h2>{message}</h2>
    </section>
  );
}

function ErrorCard({
  errorMessage,
  onRetry,
}: {
  errorMessage: string;
  onRetry: () => void;
}) {
  return (
    <section className="chat-status-card">
      <p className="eyebrow">Twype</p>
      <h2>Session start failed</h2>
      <p>{errorMessage}</p>
      <button className="auth-form__submit" onClick={onRetry} type="button">
        Retry
      </button>
    </section>
  );
}

export function ChatPage() {
  const livekitUrl = resolveLiveKitUrl();
  const {
    data,
    error,
    isError,
    isPending,
    mutate,
    reset,
    status,
  } = useStartSession();
  const [roomError, setRoomError] = useState<string | null>(null);
  const [roomMountKey, setRoomMountKey] = useState(0);

  useEffect(() => {
    if (status === "idle") {
      mutate();
    }
  }, [mutate, status]);

  const handleRetry = () => {
    setRoomError(null);
    reset();
    mutate();
  };

  const handleReconnect = () => {
    setRoomError(null);
    setRoomMountKey((currentKey) => currentKey + 1);
  };

  if (isPending || status === "idle") {
    return <LoadingCard message="Starting your session..." />;
  }

  if (isError) {
    return <ErrorCard errorMessage={error.message} onRetry={handleRetry} />;
  }

  const session = data;

  if (roomError !== null) {
    return <ErrorCard errorMessage={roomError} onRetry={handleRetry} />;
  }

  return (
    <LiveKitRoom
      audio={{
        echoCancellation: true,
        noiseSuppression: true,
      }}
      connect
      connectOptions={{
        autoSubscribe: true,
      }}
      key={[session.sessionId, roomMountKey.toString()].join(":")}
      onError={(error) => {
        setRoomError(error.message);
      }}
      serverUrl={livekitUrl}
      token={session.livekitToken}
      video={false}
    >
      <RoomAudioRenderer />
      <ChatRoom
        onReconnect={handleReconnect}
        roomName={session.roomName}
        sessionId={session.sessionId}
      />
    </LiveKitRoom>
  );
}
