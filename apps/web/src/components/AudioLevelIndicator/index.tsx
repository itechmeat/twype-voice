import {
  useIsSpeaking,
  useLocalParticipant,
  useParticipantTracks,
  useTrackVolume,
} from "@livekit/components-react";
import { type LocalAudioTrack, Track } from "livekit-client";
import clsx from "clsx";
import { useTranslation } from "react-i18next";
import { useAgentParticipant } from "../../hooks/use-agent-participant";
import styles from "./AudioLevelIndicator.module.css";

type AudioLevelIndicatorProps = {
  source: "agent" | "local";
};

// Thresholds tuned so the first bar lights up at low fallback levels (0.04+)
const BAR_THRESHOLDS = [0.03, 0.15, 0.35, 0.55] as const;

function buildBars(level: number) {
  return BAR_THRESHOLDS.map((threshold) => {
    const isActive = level >= threshold;

    return (
      <span
        aria-hidden="true"
        className={clsx(styles.bar, isActive && styles.barActive)}
        key={threshold}
      />
    );
  });
}

export function AudioLevelIndicator({ source }: AudioLevelIndicatorProps) {
  const { t } = useTranslation();
  const agentParticipant = useAgentParticipant();
  const { isMicrophoneEnabled, microphoneTrack } = useLocalParticipant();
  const [agentTrackRef] = useParticipantTracks(
    [Track.Source.Microphone],
    agentParticipant?.identity,
  );
  const localTrack = microphoneTrack?.track as LocalAudioTrack | undefined;
  const volume = useTrackVolume(source === "local" ? localTrack : agentTrackRef);
  const agentSpeaking = useIsSpeaking(agentParticipant ?? undefined);

  const isDisabled =
    source === "local"
      ? !isMicrophoneEnabled || localTrack === undefined
      : agentTrackRef === undefined;
  const level = isDisabled ? 0 : Math.max(volume, source === "agent" && agentSpeaking ? 0.14 : 0.04);
  const label = source === "local" ? t("chat.micLevel") : t("chat.agentLevel");

  return (
    <div
      aria-label={label}
      className={clsx(styles.root, isDisabled && styles.rootDisabled)}
      role="img"
    >
      {buildBars(level)}
    </div>
  );
}
