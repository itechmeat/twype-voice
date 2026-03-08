import { useState } from "react";
import { useConnectionState, useLocalParticipant } from "@livekit/components-react";
import { ConnectionState } from "livekit-client";

export function MicToggle() {
  const connectionState = useConnectionState();
  const { isMicrophoneEnabled, localParticipant } = useLocalParticipant();
  const [isUpdating, setIsUpdating] = useState(false);

  const isDisabled = connectionState !== ConnectionState.Connected || isUpdating;

  const handleToggle = async () => {
    setIsUpdating(true);

    try {
      await localParticipant.setMicrophoneEnabled(!isMicrophoneEnabled);
    } finally {
      setIsUpdating(false);
    }
  };

  return (
    <button
      aria-pressed={isMicrophoneEnabled}
      className={`chat-control-button ${isMicrophoneEnabled ? "is-active" : "is-muted"}`}
      disabled={isDisabled}
      onClick={() => {
        void handleToggle();
      }}
      type="button"
    >
      {isMicrophoneEnabled ? "Mute mic" : "Unmute mic"}
    </button>
  );
}
