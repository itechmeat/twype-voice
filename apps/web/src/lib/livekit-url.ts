type LocationLike = Pick<Location, "host" | "protocol">;

type ResolveLiveKitUrlOptions = {
  envUrl?: string | undefined;
  location?: LocationLike;
};

function normalizeEnvUrl(envUrl?: string | undefined): string | null {
  const trimmedValue = envUrl?.trim();

  if (trimmedValue === undefined || trimmedValue.length === 0) {
    return null;
  }

  return trimmedValue;
}

export function resolveLiveKitUrl(options: ResolveLiveKitUrlOptions = {}): string {
  const envUrl = normalizeEnvUrl(options.envUrl ?? import.meta.env.VITE_LIVEKIT_URL);

  if (envUrl !== null) {
    return envUrl;
  }

  const currentLocation = options.location ?? window.location;
  const protocol = currentLocation.protocol === "https:" ? "wss:" : "ws:";

  return `${protocol}//${currentLocation.host}/livekit-signaling/`;
}
