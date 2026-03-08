import { useMutation } from "@tanstack/react-query";
import { useState, type ComponentProps } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router";
import { apiFetch } from "../lib/api-client";
import { ApiError } from "../lib/api-error";
import { setTokens } from "../lib/auth-tokens";
import { readFormValue } from "../lib/form-utils";

type VerifyRequest = {
  email: string;
  code: string;
};

type TokenResponse = {
  access_token: string;
  refresh_token: string;
  token_type: string;
};

type VerifyLocationState = {
  email?: string;
};

function resolveEmail(search: string, state: VerifyLocationState | null): string | null {
  if (typeof state?.email === "string" && state.email.length > 0) {
    return state.email;
  }

  const fromQuery = new URLSearchParams(search).get("email");
  return fromQuery !== null && fromQuery.length > 0 ? fromQuery : null;
}

export function VerifyPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const [formError, setFormError] = useState<string | null>(null);
  const email = resolveEmail(
    location.search,
    (location.state as VerifyLocationState | null) ?? null,
  );
  const mutation = useMutation<TokenResponse, ApiError, VerifyRequest>({
    mutationFn: (payload) =>
      apiFetch<TokenResponse>("/auth/verify", {
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

  if (email === null) {
    return <Navigate to="/register" replace />;
  }

  const handleSubmit: NonNullable<ComponentProps<"form">["onSubmit"]> = (event) => {
    event.preventDefault();
    const form = event.currentTarget;

    if (!form.reportValidity()) {
      return;
    }

    const formData = new FormData(form);
    setFormError(null);
    mutation.mutate({
      email,
      code: readFormValue(formData, "code"),
    });
  };

  return (
    <section className="auth-page">
      <div className="auth-card">
        <p className="eyebrow">Verify email</p>
        <h1>Enter verification code</h1>
        <p className="auth-card__description">
          We sent a 6-digit code to <strong>{email}</strong>.
        </p>
        <form className="auth-form" onSubmit={handleSubmit}>
          <label className="auth-form__field">
            <span>Code</span>
            <input
              name="code"
              type="text"
              inputMode="numeric"
              autoComplete="one-time-code"
              minLength={6}
              maxLength={6}
              pattern="[0-9]{6}"
              required
            />
          </label>
          {formError !== null ? (
            <p className="auth-form__error" role="alert">
              {formError}
            </p>
          ) : null}
          <button className="auth-form__submit" type="submit" disabled={mutation.isPending}>
            {mutation.isPending ? "Verifying..." : "Verify email"}
          </button>
        </form>
        <p className="auth-card__footer">
          Wrong email? <Link to="/register">Create another account</Link>
        </p>
      </div>
    </section>
  );
}
