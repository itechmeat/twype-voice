import { QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import { type ReactElement } from "react";
import {
  type InitialEntry,
  RouterProvider,
  createMemoryRouter,
  type RouteObject,
} from "react-router";
import { AuthProvider } from "../lib/auth-context";
import { createAppQueryClient } from "../lib/query-client";

export function renderWithRouter(
  routes: RouteObject[],
  initialEntries: InitialEntry[] = ["/"],
): ReturnType<typeof render> {
  const queryClient = createAppQueryClient();
  const router = createMemoryRouter(routes, { initialEntries });

  return render(
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <RouterProvider router={router} />
      </AuthProvider>
    </QueryClientProvider>,
  );
}

export function renderWithProviders(element: ReactElement): ReturnType<typeof render> {
  const queryClient = createAppQueryClient();

  return render(
    <QueryClientProvider client={queryClient}>
      <AuthProvider>{element}</AuthProvider>
    </QueryClientProvider>,
  );
}
