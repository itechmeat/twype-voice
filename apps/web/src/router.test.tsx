import { screen } from "@testing-library/react";
import { describe, expect, it, beforeEach } from "vitest";
import { createMemoryRouter, RouterProvider } from "react-router";
import { QueryClientProvider } from "@tanstack/react-query";
import { AuthProvider } from "./lib/auth-context";
import { createAppQueryClient } from "./lib/query-client";
import { appRoutes } from "./router";
import { render } from "@testing-library/react";
import { vi } from "vitest";

vi.mock("./pages/ChatPage", () => ({
  ChatPage: () => <h1>Chat workspace</h1>,
}));

function renderApp(initialEntries: string[]) {
  const queryClient = createAppQueryClient();
  const router = createMemoryRouter(appRoutes, { initialEntries });

  return render(
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <RouterProvider router={router} />
      </AuthProvider>
    </QueryClientProvider>,
  );
}

describe("route guards", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("redirects authenticated users away from public routes", async () => {
    window.localStorage.setItem("access_token", "access-123");
    window.localStorage.setItem("refresh_token", "refresh-456");

    renderApp(["/login"]);

    expect(await screen.findByRole("heading", { name: "Chat workspace" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Login" })).not.toBeInTheDocument();
  });

  it("redirects unauthenticated users away from protected routes", async () => {
    renderApp(["/"]);

    expect(await screen.findByRole("heading", { name: "Login" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Chat workspace" })).not.toBeInTheDocument();
  });
});
