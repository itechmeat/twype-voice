import { useNetworkStatus } from "../hooks/use-network-status";

export function NetworkStatusBanner() {
  const isOnline = useNetworkStatus();

  if (isOnline) {
    return null;
  }

  return (
    <div className="network-banner" role="status">
      Offline. Twype shell is cached, but live voice and text features need a connection.
    </div>
  );
}
