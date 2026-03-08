import {
  useIsSpeaking,
  useLocalParticipant,
  useParticipantTracks,
  useTrackVolume,
} from "@livekit/components-react";
import { type LocalAudioTrack, Track } from "livekit-client";
import { useAgentParticipant } from "../hooks/use-agent-participant";

type AudioLevelIndicatorProps = {
  source: "agent" | "local";
};

function buildBars(level: number) {
  return Array.from({ length: 4 }, (_, index) => {
    const threshold = (index + 1) / 5;
    const isActive = level >= threshold;

    return (
      <span
        aria-hidden="true"
        className={`audio-level__bar ${isActive ? "is-active" : ""}`}
        key={threshold}
      />
    );
  });
}

export function AudioLevelIndicator({ source }: AudioLevelIndicatorProps) {
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
  const label = source === "local" ? "Microphone level" : "Agent level";

  return (
    <div
      aria-label={label}
      className={`audio-level ${isDisabled ? "is-disabled" : ""}`}
      role="img"
    >
      {buildBars(level)}
    </div>
  );
}
