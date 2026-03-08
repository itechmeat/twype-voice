import { useMemo } from "react";
import { useRemoteParticipants } from "@livekit/components-react";

export function useAgentParticipant() {
  const participants = useRemoteParticipants();

  return useMemo(
    () => participants.find((participant) => participant.isAgent) ?? null,
    [participants],
  );
}
