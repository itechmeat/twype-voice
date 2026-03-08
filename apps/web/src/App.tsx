import { QueryClientProvider } from "@tanstack/react-query";
import { RouterProvider } from "react-router";
import { NetworkStatusBanner } from "./components/NetworkStatusBanner";
import { AuthProvider } from "./lib/auth-context";
import { createAppQueryClient } from "./lib/query-client";
import { appRouter } from "./router";

const queryClient = createAppQueryClient();

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <NetworkStatusBanner />
        <RouterProvider router={appRouter} />
      </AuthProvider>
    </QueryClientProvider>
  );
}
