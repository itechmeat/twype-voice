import { useMutation } from "@tanstack/react-query";
import { useState, type ComponentProps } from "react";
import { Link, useNavigate } from "react-router";
import { apiFetch } from "../lib/api-client";
import { ApiError } from "../lib/api-error";
import { setTokens } from "../lib/auth-tokens";
import { readFormValue } from "../lib/form-utils";

type LoginRequest = {
  email: string;
  password: string;
};

type TokenResponse = {
  access_token: string;
  refresh_token: string;
  token_type: string;
};

export function LoginPage() {
  const navigate = useNavigate();
  const [formError, setFormError] = useState<string | null>(null);
  const mutation = useMutation<TokenResponse, ApiError, LoginRequest>({
    mutationFn: (payload) =>
      apiFetch<TokenResponse>("/auth/login", {
        method: "POST",
        body: payload,
      }),
    onSuccess: (result) => {
      setTokens(result.access_token, result.refresh_token);
      void navigate("/", { replace: true });
    },
    onError: (error) => {
      setFormError(error.detail);
    },
  });

  const handleSubmit: NonNullable<ComponentProps<"form">["onSubmit"]> = (event) => {
    event.preventDefault();
    const form = event.currentTarget;

    if (!form.reportValidity()) {
      return;
    }

    const formData = new FormData(form);
    setFormError(null);
    mutation.mutate({
      email: readFormValue(formData, "email"),
      password: readFormValue(formData, "password"),
    });
  };

  return (
    <section className="auth-page">
      <div className="auth-card">
        <p className="eyebrow">Welcome back</p>
        <h1>Login</h1>
        <p className="auth-card__description">Sign in with your verified email and password.</p>
        <form className="auth-form" onSubmit={handleSubmit}>
          <label className="auth-form__field">
            <span>Email</span>
            <input name="email" type="email" autoComplete="email" required />
          </label>
          <label className="auth-form__field">
            <span>Password</span>
            <input name="password" type="password" autoComplete="current-password" required />
          </label>
          {formError !== null ? (
            <p className="auth-form__error" role="alert">
              {formError}
            </p>
          ) : null}
          <button className="auth-form__submit" type="submit" disabled={mutation.isPending}>
            {mutation.isPending ? "Signing in..." : "Sign in"}
          </button>
        </form>
        <p className="auth-card__footer">
          Need an account? <Link to="/register">Create one</Link>
        </p>
      </div>
    </section>
  );
}
