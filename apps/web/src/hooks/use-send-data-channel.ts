import { useCallback } from "react";
import { ConnectionState } from "livekit-client";
import { useRoomContext } from "@livekit/components-react";
import {
  encodeLiveKitMessage,
  type OutgoingLiveKitMessage,
} from "../lib/livekit-messages";

type SendResult = Promise<boolean>;
type OutgoingMessageType = OutgoingLiveKitMessage["type"];
type OutgoingPayload<TType extends OutgoingMessageType> = Omit<
  Extract<OutgoingLiveKitMessage, { type: TType }>,
  "type"
>;

export function useSendDataChannel() {
  const room = useRoomContext();

  return useCallback(
    async <TType extends OutgoingMessageType>(
      type: TType,
      payload: OutgoingPayload<TType>,
    ): SendResult => {
      if (room.state !== ConnectionState.Connected) {
        console.warn("Skipping LiveKit data channel publish while disconnected.");
        return false;
      }

      try {
        const message = { type, ...payload } as Extract<OutgoingLiveKitMessage, { type: TType }>;

        await room.localParticipant.publishData(encodeLiveKitMessage(message), { reliable: true });

        return true;
      } catch (error) {
        console.warn("LiveKit data channel publish failed.", error);
        return false;
      }
    },
    [room],
  );
}
