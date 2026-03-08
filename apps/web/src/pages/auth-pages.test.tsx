import { act, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { ApiError } from "../lib/api-error";
import { LoginPage } from "./LoginPage";
import { RegisterPage } from "./RegisterPage";
import { VerifyPage } from "./VerifyPage";
import { renderWithRouter } from "../test/test-utils";

const apiFetchMock = vi.fn<(path: string, options?: unknown) => Promise<unknown>>();

vi.mock("../lib/api-client", async (importOriginal) => {
  const original = await importOriginal<typeof import("../lib/api-client")>();
  return {
    ...original,
    apiFetch: (path: string, options?: unknown) => apiFetchMock(path, options),
  };
});

describe("auth pages", () => {
  beforeEach(() => {
    apiFetchMock.mockReset();
    window.localStorage.clear();
    window.history.pushState({}, "", "/");
  });

  it("prevents invalid register submission and exposes login link", async () => {
    const user = userEvent.setup();

    renderWithRouter(
      [
        { path: "/register", element: <RegisterPage /> },
        { path: "/login", element: <h1>Login destination</h1> },
      ],
      ["/register"],
    );

    const emailInput = screen.getByLabelText("Email");
    const passwordInput = screen.getByLabelText("Password");

    await user.type(emailInput, "invalid-email");
    await user.type(passwordInput, "short");
    await user.click(screen.getByRole("button", { name: "Create account" }));

    expect(apiFetchMock).not.toHaveBeenCalled();
    expect(emailInput).toBeInvalid();
    expect(passwordInput).toHaveAttribute("minlength", "8");
    expect(screen.getByRole("link", { name: "Sign in" })).toHaveAttribute("href", "/login");
  });

  it("submits registration and navigates to verify page with email", async () => {
    const user = userEvent.setup();
    apiFetchMock.mockResolvedValue({
      email: "user@example.com",
      message: "Registered",
    });

    renderWithRouter(
      [
        { path: "/register", element: <RegisterPage /> },
        { path: "/verify", element: <h1>Verify destination</h1> },
      ],
      ["/register"],
    );

    await user.type(screen.getByLabelText("Email"), "user@example.com");
    await user.type(screen.getByLabelText("Password"), "password123");
    await user.click(screen.getByRole("button", { name: "Create account" }));

    await screen.findByRole("heading", { name: "Verify destination" });
    expect(apiFetchMock).toHaveBeenCalledWith("/auth/register", {
      method: "POST",
      body: {
        email: "user@example.com",
        password: "password123",
      },
    });
  });

  it("shows API errors on register page", async () => {
    const user = userEvent.setup();
    apiFetchMock.mockRejectedValue(new ApiError(409, "Email is already registered"));

    renderWithRouter(
      [
        { path: "/register", element: <RegisterPage /> },
        { path: "/verify", element: <h1>Verify destination</h1> },
      ],
      ["/register"],
    );

    await user.type(screen.getByLabelText("Email"), "user@example.com");
    await user.type(screen.getByLabelText("Password"), "password123");
    await user.click(screen.getByRole("button", { name: "Create account" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Email is already registered");
  });

  it("shows loading state for register mutation", async () => {
    const user = userEvent.setup();
    let resolveRequest: ((value: unknown) => void) | undefined;
    apiFetchMock.mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveRequest = resolve;
        }),
    );

    renderWithRouter(
      [
        { path: "/register", element: <RegisterPage /> },
        { path: "/verify", element: <h1>Verify destination</h1> },
      ],
      ["/register"],
    );

    await user.type(screen.getByLabelText("Email"), "user@example.com");
    await user.type(screen.getByLabelText("Password"), "password123");
    await user.click(screen.getByRole("button", { name: "Create account" }));

    expect(screen.getByRole("button", { name: "Creating account..." })).toBeDisabled();

    act(() => {
      resolveRequest?.({
        email: "user@example.com",
        message: "Registered",
      });
    });

    await screen.findByRole("heading", { name: "Verify destination" });
  });

  it("redirects verify page to register when email is missing", async () => {
    renderWithRouter(
      [
        { path: "/verify", element: <VerifyPage /> },
        { path: "/register", element: <h1>Register destination</h1> },
      ],
      ["/verify"],
    );

    await screen.findByRole("heading", { name: "Register destination" });
  });

  it("verifies code, stores tokens, and navigates home", async () => {
    const user = userEvent.setup();
    apiFetchMock.mockResolvedValue({
      access_token: "access-123",
      refresh_token: "refresh-456",
      token_type: "bearer",
    });

    renderWithRouter(
      [
        { path: "/verify", element: <VerifyPage /> },
        { path: "/", element: <h1>Home destination</h1> },
      ],
      [{ pathname: "/verify", state: { email: "user@example.com" } }],
    );

    await user.type(screen.getByLabelText("Code"), "123456");
    await user.click(screen.getByRole("button", { name: "Verify email" }));

    await screen.findByRole("heading", { name: "Home destination" });
    expect(window.localStorage.getItem("access_token")).toBe("access-123");
    expect(window.localStorage.getItem("refresh_token")).toBe("refresh-456");
  });

  it("shows loading state for verify mutation", async () => {
    const user = userEvent.setup();
    let resolveRequest: ((value: unknown) => void) | undefined;
    apiFetchMock.mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveRequest = resolve;
        }),
    );

    renderWithRouter(
      [
        { path: "/verify", element: <VerifyPage /> },
        { path: "/", element: <h1>Home destination</h1> },
      ],
      [{ pathname: "/verify", state: { email: "user@example.com" } }],
    );

    await user.type(screen.getByLabelText("Code"), "123456");
    await user.click(screen.getByRole("button", { name: "Verify email" }));

    expect(screen.getByRole("button", { name: "Verifying..." })).toBeDisabled();

    act(() => {
      resolveRequest?.({
        access_token: "access-123",
        refresh_token: "refresh-456",
        token_type: "bearer",
      });
    });

    await screen.findByRole("heading", { name: "Home destination" });
  });

  it("shows API errors on verify page", async () => {
    const user = userEvent.setup();
    apiFetchMock.mockRejectedValue(new ApiError(400, "Invalid verification code"));

    renderWithRouter(
      [{ path: "/verify", element: <VerifyPage /> }],
      [{ pathname: "/verify", state: { email: "user@example.com" } }],
    );

    await user.type(screen.getByLabelText("Code"), "123456");
    await user.click(screen.getByRole("button", { name: "Verify email" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Invalid verification code");
  });

  it("logs in, shows loading state, and links to register", async () => {
    const user = userEvent.setup();
    let resolveRequest: ((value: unknown) => void) | undefined;
    apiFetchMock.mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveRequest = resolve;
        }),
    );

    renderWithRouter(
      [
        { path: "/login", element: <LoginPage /> },
        { path: "/register", element: <h1>Register destination</h1> },
        { path: "/", element: <h1>Home destination</h1> },
      ],
      ["/login"],
    );

    await user.type(screen.getByLabelText("Email"), "user@example.com");
    await user.type(screen.getByLabelText("Password"), "password123");
    await user.click(screen.getByRole("button", { name: "Sign in" }));

    expect(screen.getByRole("button", { name: "Signing in..." })).toBeDisabled();
    expect(screen.getByRole("link", { name: "Create one" })).toHaveAttribute("href", "/register");

    act(() => {
      resolveRequest?.({
        access_token: "access-999",
        refresh_token: "refresh-999",
        token_type: "bearer",
      });
    });

    await screen.findByRole("heading", { name: "Home destination" });
    expect(window.localStorage.getItem("access_token")).toBe("access-999");
  });

  it("shows API errors on login", async () => {
    const user = userEvent.setup();
    apiFetchMock.mockRejectedValue(new ApiError(401, "Invalid credentials"));

    renderWithRouter([{ path: "/login", element: <LoginPage /> }], ["/login"]);

    await user.type(screen.getByLabelText("Email"), "user@example.com");
    await user.type(screen.getByLabelText("Password"), "password123");
    await user.click(screen.getByRole("button", { name: "Sign in" }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("Invalid credentials");
    });
  });
});
