import type {
  EmotionalStateMessage,
  StructuredResponseItem,
} from "./livekit-messages";

export type ChatMode = "voice" | "text";
export type MessageDeliveryStatus = "sending" | "sent" | "failed";

type ChatActor = "user" | "agent";

type BaseChatMessage = {
  id: string;
  actor: ChatActor;
  mode: ChatMode;
  createdAt: string;
};

export type UserVoiceMessage = BaseChatMessage & {
  type: "user-voice";
  actor: "user";
  mode: "voice";
  text: string;
};

export type UserTextMessage = BaseChatMessage & {
  type: "user-text";
  actor: "user";
  mode: "text";
  text: string;
  deliveryStatus: MessageDeliveryStatus;
};

export type AgentPlainMessage = BaseChatMessage & {
  type: "agent-plain";
  actor: "agent";
  text: string;
  sourceIds?: string[];
};

export type AgentStructuredMessage = BaseChatMessage & {
  type: "agent-structured";
  actor: "agent";
  items: StructuredResponseItem[];
  sourceIds?: string[];
};

export type ChatMessageEntry =
  | UserVoiceMessage
  | UserTextMessage
  | AgentPlainMessage
  | AgentStructuredMessage;

export type StreamingResponse =
  | {
      type: "plain";
      text: string;
    }
  | {
      type: "structured";
      items: StructuredResponseItem[];
    };

export type EmotionalStateSnapshot = Omit<EmotionalStateMessage, "type">;

export type ChatState = {
  readonly messages: ChatMessageEntry[];
  readonly interimTranscript: string | null;
  readonly streamingResponse: StreamingResponse | null;
  readonly emotionalState: EmotionalStateSnapshot | null;
  readonly currentMode: ChatMode;
};

type AddMessageAction = {
  type: "add-message";
  message: ChatMessageEntry;
};

type SetInterimTranscriptAction = {
  type: "set-interim-transcript";
  text: string;
};

type ClearInterimTranscriptAction = {
  type: "clear-interim-transcript";
};

type SetStreamingResponseAction = {
  type: "set-streaming-response";
  streamingResponse: StreamingResponse;
};

type ClearStreamingResponseAction = {
  type: "clear-streaming-response";
};

type SetEmotionalStateAction = {
  type: "set-emotional-state";
  emotionalState: EmotionalStateSnapshot;
};

type UpdateUserTextMessageStatusAction = {
  type: "update-user-text-message-status";
  id: string;
  deliveryStatus: Exclude<MessageDeliveryStatus, "sending">;
};

export type ChatStateAction =
  | AddMessageAction
  | SetInterimTranscriptAction
  | ClearInterimTranscriptAction
  | SetStreamingResponseAction
  | ClearStreamingResponseAction
  | SetEmotionalStateAction
  | UpdateUserTextMessageStatusAction;

export function createInitialChatState(): ChatState {
  return {
    messages: [],
    interimTranscript: null,
    streamingResponse: null,
    emotionalState: null,
    currentMode: "voice",
  };
}

export function createMessageId(prefix: string): string {
  return `${prefix}-${crypto.randomUUID()}`;
}

function nextModeForMessage(message: ChatMessageEntry, currentMode: ChatMode): ChatMode {
  switch (message.type) {
    case "user-text":
      return "text";
    case "user-voice":
      return "voice";
    case "agent-plain":
    case "agent-structured":
      return currentMode;
    default: {
      const exhaustiveCheck: never = message;
      throw new Error(`Unsupported chat message: ${String(exhaustiveCheck)}`);
    }
  }
}

export function chatStateReducer(state: ChatState, action: ChatStateAction): ChatState {
  switch (action.type) {
    case "add-message":
      return {
        ...state,
        currentMode: nextModeForMessage(action.message, state.currentMode),
        messages: [...state.messages, action.message],
      };
    case "set-interim-transcript":
      return {
        ...state,
        interimTranscript: action.text,
      };
    case "clear-interim-transcript":
      return {
        ...state,
        interimTranscript: null,
      };
    case "set-streaming-response":
      return {
        ...state,
        streamingResponse: action.streamingResponse,
      };
    case "clear-streaming-response":
      return {
        ...state,
        streamingResponse: null,
      };
    case "set-emotional-state":
      return {
        ...state,
        emotionalState: action.emotionalState,
      };
    case "update-user-text-message-status":
      return {
        ...state,
        messages: state.messages.map((message) => {
          if (message.type !== "user-text" || message.id !== action.id) {
            return message;
          }

          return {
            ...message,
            deliveryStatus: action.deliveryStatus,
          };
        }),
      };
    default: {
      const exhaustiveCheck: never = action;
      throw new Error(`Unsupported chat state action: ${String(exhaustiveCheck)}`);
    }
  }
}
