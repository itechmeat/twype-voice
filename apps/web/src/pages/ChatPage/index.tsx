import {
  LiveKitRoom,
  RoomAudioRenderer,
  useConnectionState,
} from "@livekit/components-react";
import { startTransition, useEffect, useReducer, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { ConnectionState } from "livekit-client";
import { AgentStateIndicator } from "../../components/AgentStateIndicator";
import { AudioLevelIndicator } from "../../components/AudioLevelIndicator";
import { ChatFeed } from "../../components/ChatFeed";
import { MicToggle } from "../../components/MicToggle";
import { TextInput } from "../../components/TextInput";
import { useDataChannel } from "../../hooks/use-data-channel";
import { useSendDataChannel } from "../../hooks/use-send-data-channel";
import { useStartSession, type StartSessionResponse } from "../../hooks/use-start-session";
import {
  chatStateReducer,
  createInitialChatState,
  createMessageId,
  type ChatMode,
} from "../../lib/chat-state";
import { resolveLiveKitUrl } from "../../lib/livekit-url";
import type { StructuredResponseItem } from "../../lib/livekit-messages";
import styles from "./ChatPage.module.css";

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
  const { t } = useTranslation();
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
      ? t("room.disconnected")
      : connectionState === ConnectionState.Connecting
        ? t("room.connecting")
        : t("room.reconnecting");

  return (
    <div className={styles.connectionBanner}>
      <p>{label}</p>
      {connectionState === ConnectionState.Disconnected ? (
        <button className={styles.reconnectButton} onClick={onReconnect} type="button">
          {t("room.reconnect")}
        </button>
      ) : null}
    </div>
  );
}

function ChatRoom({ onReconnect, roomName, sessionId }: ChatRoomProps) {
  const { t } = useTranslation();
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
    <section className={styles.page} data-session-id={sessionId}>
      <ConnectionStateBanner onReconnect={onReconnect} />

      <div className={styles.grid}>
        <aside className={styles.sidebar}>
          <div className={styles.sidebarCard}>
            <p className="eyebrow">{t("room.roomLabel")}</p>
            <h2>{t("room.liveConversation")}</h2>
            <p>{roomName}</p>
          </div>

          <div className={styles.sidebarCard}>
            <p className="eyebrow">{t("room.agentLabel")}</p>
            <AgentStateIndicator />
            <AudioLevelIndicator source="agent" />
          </div>

          <div className={styles.sidebarCard}>
            <p className="eyebrow">{t("room.voiceLabel")}</p>
            <MicToggle />
            <AudioLevelIndicator source="local" />
          </div>
        </aside>

        <div className={styles.panel}>
          <header className={styles.panelHeader}>
            <div>
              <p className="eyebrow">{t("room.sessionLabel")}</p>
              <h2>{t("room.chatWorkspace")}</h2>
            </div>
            <p className={styles.status}>
              {t("room.connectionStatus")}{" "}
              <strong>
                {connectionState === ConnectionState.SignalReconnecting
                  ? t("room.connectionReconnecting")
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
  const { t } = useTranslation();
  return (
    <section className={styles.statusCard}>
      <p className="eyebrow">{t("common.twype")}</p>
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
  const { t } = useTranslation();
  return (
    <section className={styles.statusCard}>
      <p className="eyebrow">{t("common.twype")}</p>
      <h2>{t("room.sessionFailed")}</h2>
      <p>{errorMessage}</p>
      <button className={styles.reconnectButton} onClick={onRetry} type="button">
        {t("common.retry")}
      </button>
    </section>
  );
}

const SESSION_STORAGE_KEY = "twype:active-session";

function isStartSessionResponse(value: unknown): value is StartSessionResponse {
  return (
    typeof value === "object" &&
    value !== null &&
    "sessionId" in value &&
    typeof value.sessionId === "string" &&
    "roomName" in value &&
    typeof value.roomName === "string" &&
    "livekitToken" in value &&
    typeof value.livekitToken === "string"
  );
}

function loadStoredSession(): StartSessionResponse | null {
  try {
    const raw = sessionStorage.getItem(SESSION_STORAGE_KEY);
    if (raw === null) return null;

    const parsed: unknown = JSON.parse(raw);
    if (isStartSessionResponse(parsed)) return parsed;

    // Stored data is malformed — discard it
    sessionStorage.removeItem(SESSION_STORAGE_KEY);
    return null;
  } catch {
    sessionStorage.removeItem(SESSION_STORAGE_KEY);
    return null;
  }
}

function saveSession(session: StartSessionResponse): void {
  try {
    sessionStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(session));
  } catch {
    // Storage full or unavailable — not critical, session still works in memory
  }
}

function clearStoredSession(): void {
  sessionStorage.removeItem(SESSION_STORAGE_KEY);
}

export function ChatPage() {
  const { t } = useTranslation();
  const livekitUrl = resolveLiveKitUrl();
  const {
    data,
    error,
    isError,
    mutate,
    reset,
    status,
  } = useStartSession();
  const [restoredSession, setRestoredSession] = useState<StartSessionResponse | null>(null);
  const [roomError, setRoomError] = useState<string | null>(null);
  const [roomMountKey, setRoomMountKey] = useState(0);

  useEffect(() => {
    if (status === "idle") {
      const stored = loadStoredSession();
      if (stored !== null) {
        setRestoredSession(stored);
      } else {
        mutate(undefined, {
          onSuccess: (session) => {
            saveSession(session);
          },
        });
      }
    }
  }, [mutate, status]);

  const handleRetry = () => {
    // Clear any stale stored session so we get a fresh one
    clearStoredSession();
    setRestoredSession(null);
    setRoomError(null);
    reset();
    mutate(undefined, {
      onSuccess: (session) => {
        saveSession(session);
      },
    });
  };

  const handleReconnect = () => {
    setRoomError(null);
    setRoomMountKey((currentKey) => currentKey + 1);
  };

  const session = restoredSession ?? data;

  if (session === undefined) {
    if (isError) {
      return <ErrorCard errorMessage={error.message} onRetry={handleRetry} />;
    }
    return <LoadingCard message={t("room.startingSession")} />;
  }

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
      onError={(roomErr) => {
        // Room-level errors likely mean the session/token is stale
        clearStoredSession();
        setRoomError(roomErr.message);
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
