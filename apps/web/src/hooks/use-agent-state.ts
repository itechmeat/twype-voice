import { useEffect, useState } from "react";
import { useConnectionState, useRoomContext } from "@livekit/components-react";
import { ConnectionState, ParticipantEvent } from "livekit-client";
import { useAgentParticipant } from "./use-agent-participant";

export type AgentUiState =
  | "connecting"
  | "listening"
  | "thinking"
  | "speaking"
  | "reconnecting"
  | "disconnected";

const agentStateKeys = ["lk.agent.state", "agent_state", "state"] as const;

function toAgentUiState(value: string | undefined): AgentUiState | null {
  switch (value) {
    case "listening":
    case "thinking":
    case "speaking":
      return value;
    default:
      return null;
  }
}

function readAgentAttributeState(attributes: Readonly<Record<string, string>>): AgentUiState | null {
  for (const key of agentStateKeys) {
    const state = toAgentUiState(attributes[key]);

    if (state !== null) {
      return state;
    }
  }

  return null;
}

export function useAgentState(): AgentUiState {
  const room = useRoomContext();
  const connectionState = useConnectionState(room);
  const agentParticipant = useAgentParticipant();
  const [agentState, setAgentState] = useState<AgentUiState | null>(() =>
    agentParticipant === null ? null : readAgentAttributeState(agentParticipant.attributes),
  );
  const [isSpeaking, setIsSpeaking] = useState<boolean>(agentParticipant?.isSpeaking ?? false);

  useEffect(() => {
    if (agentParticipant === null) {
      setAgentState(null);
      setIsSpeaking(false);
      return;
    }

    const syncAgentState = () => {
      setAgentState(readAgentAttributeState(agentParticipant.attributes));
      setIsSpeaking(agentParticipant.isSpeaking);
    };

    syncAgentState();
    agentParticipant.on(ParticipantEvent.AttributesChanged, syncAgentState);
    agentParticipant.on(ParticipantEvent.IsSpeakingChanged, setIsSpeaking);

    return () => {
      agentParticipant.off(ParticipantEvent.AttributesChanged, syncAgentState);
      agentParticipant.off(ParticipantEvent.IsSpeakingChanged, setIsSpeaking);
    };
  }, [agentParticipant]);

  if (connectionState === ConnectionState.Disconnected) {
    return "disconnected";
  }

  if (
    connectionState === ConnectionState.Reconnecting ||
    connectionState === ConnectionState.SignalReconnecting
  ) {
    return "reconnecting";
  }

  if (agentState !== null) {
    return agentState;
  }

  if (agentParticipant === null) {
    return "connecting";
  }

  return isSpeaking ? "speaking" : "listening";
}
