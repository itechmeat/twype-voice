import { useState } from "react";
import { useConnectionState, useLocalParticipant } from "@livekit/components-react";
import { ConnectionState } from "livekit-client";
import clsx from "clsx";
import { useTranslation } from "react-i18next";
import styles from "./MicToggle.module.css";

export function MicToggle() {
  const { t } = useTranslation();
  const connectionState = useConnectionState();
  const { isMicrophoneEnabled, localParticipant } = useLocalParticipant();
  const [isUpdating, setIsUpdating] = useState(false);

  const isDisabled = connectionState !== ConnectionState.Connected || isUpdating;

  const handleToggle = async () => {
    setIsUpdating(true);

    try {
      await localParticipant.setMicrophoneEnabled(!isMicrophoneEnabled);
    } catch (error) {
      console.error("Failed to toggle microphone:", error);
    } finally {
      setIsUpdating(false);
    }
  };

  return (
    <button
      aria-pressed={isMicrophoneEnabled}
      className={clsx(styles.root, isMicrophoneEnabled ? styles.active : styles.muted)}
      disabled={isDisabled}
      onClick={() => {
        void handleToggle();
      }}
      type="button"
    >
      {isMicrophoneEnabled ? t("chat.micMute") : t("chat.micUnmute")}
    </button>
  );
}
