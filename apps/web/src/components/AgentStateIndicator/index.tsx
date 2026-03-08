import { useTranslation } from "react-i18next";
import { useAgentState } from "../../hooks/use-agent-state";
import styles from "./AgentStateIndicator.module.css";

const stateKeys = {
  connecting: "agent.connecting",
  listening: "agent.listening",
  thinking: "agent.thinking",
  speaking: "agent.speaking",
  reconnecting: "agent.reconnecting",
  disconnected: "agent.disconnected",
} as const;

export function AgentStateIndicator() {
  const { t } = useTranslation();
  const agentState = useAgentState();

  return (
    <div className={styles.root} data-state={agentState} role="status">
      <span aria-hidden="true" className={styles.dot} />
      <span>{t(stateKeys[agentState])}</span>
    </div>
  );
}
