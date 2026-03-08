import { useEffect, useRef } from "react";
import type { RemoteParticipant } from "livekit-client";
import { RoomEvent } from "livekit-client";
import { useRoomContext } from "@livekit/components-react";
import {
  isIncomingLiveKitMessage,
  type IncomingLiveKitMessage,
} from "../lib/livekit-messages";

type HandlerMap = {
  [TType in IncomingLiveKitMessage["type"]]?: (
    message: Extract<IncomingLiveKitMessage, { type: TType }>,
  ) => void;
};

const textDecoder = new TextDecoder();

export function useDataChannel(handlers: HandlerMap): void {
  const room = useRoomContext();
  const handlersRef = useRef(handlers);

  useEffect(() => {
    handlersRef.current = handlers;
  }, [handlers]);

  useEffect(() => {
    const handleDataReceived = (
      payload: Uint8Array,
      participant?: RemoteParticipant,
    ) => {
      if (participant?.identity === room.localParticipant.identity) {
        return;
      }

      let parsedMessage: unknown;

      try {
        parsedMessage = JSON.parse(textDecoder.decode(payload));
      } catch {
        console.warn("Ignoring malformed LiveKit data channel payload.");
        return;
      }

      if (!isIncomingLiveKitMessage(parsedMessage)) {
        return;
      }

      const handler = handlersRef.current[parsedMessage.type] as
        | ((message: IncomingLiveKitMessage) => void)
        | undefined;

      if (handler !== undefined) {
        handler(parsedMessage);
      }
    };

    room.on(RoomEvent.DataReceived, handleDataReceived);

    return () => {
      room.off(RoomEvent.DataReceived, handleDataReceived);
    };
  }, [room]);
}
