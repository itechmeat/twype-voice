import { QueryClientProvider } from "@tanstack/react-query";
import { RouterProvider } from "react-router";
import { NetworkStatusBanner } from "./components/NetworkStatusBanner";
import { UpdatePrompt } from "./components/UpdatePrompt";
import { AuthProvider } from "./lib/auth-context";
import { createAppQueryClient } from "./lib/query-client";
import { appRouter } from "./router";

const queryClient = createAppQueryClient();

export type ServiceWorkerPromptState = {
  needRefresh: boolean;
  onUpdate: () => void;
  resetSignal: number;
};

type AppProps = {
  serviceWorkerPrompt: ServiceWorkerPromptState;
};

export function App({ serviceWorkerPrompt }: AppProps) {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <NetworkStatusBanner />
        <UpdatePrompt
          needRefresh={serviceWorkerPrompt.needRefresh}
          onUpdate={serviceWorkerPrompt.onUpdate}
          resetSignal={serviceWorkerPrompt.resetSignal}
        />
        <RouterProvider router={appRouter} />
      </AuthProvider>
    </QueryClientProvider>
  );
}
