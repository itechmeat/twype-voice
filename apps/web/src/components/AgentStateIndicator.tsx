import { useAgentState } from "../hooks/use-agent-state";

const stateLabels = {
  connecting: "Connecting",
  listening: "Listening",
  thinking: "Thinking",
  speaking: "Speaking",
  reconnecting: "Reconnecting",
  disconnected: "Disconnected",
} as const;

export function AgentStateIndicator() {
  const agentState = useAgentState();

  return (
    <div className={`agent-state agent-state--${agentState}`} role="status">
      <span aria-hidden="true" className="agent-state__dot" />
      <span>{stateLabels[agentState]}</span>
    </div>
  );
}
