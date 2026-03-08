import { useMutation } from "@tanstack/react-query";
import { useState, type ComponentProps } from "react";
import { Link, useNavigate } from "react-router";
import { apiFetch } from "../lib/api-client";
import { ApiError } from "../lib/api-error";
import { readFormValue } from "../lib/form-utils";

type RegisterRequest = {
  email: string;
  password: string;
};

type RegisterResponse = {
  email: string;
  message: string;
};

export function RegisterPage() {
  const navigate = useNavigate();
  const [formError, setFormError] = useState<string | null>(null);
  const mutation = useMutation<RegisterResponse, ApiError, RegisterRequest>({
    mutationFn: (payload) =>
      apiFetch<RegisterResponse>("/auth/register", {
        method: "POST",
        body: payload,
      }),
    onSuccess: (result) => {
      void navigate(`/verify?email=${encodeURIComponent(result.email)}`, {
        replace: true,
        state: { email: result.email },
      });
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
        <p className="eyebrow">Create account</p>
        <h1>Register</h1>
        <p className="auth-card__description">
          Start with email verification and continue to the app.
        </p>
        <form className="auth-form" onSubmit={handleSubmit}>
          <label className="auth-form__field">
            <span>Email</span>
            <input name="email" type="email" autoComplete="email" required />
          </label>
          <label className="auth-form__field">
            <span>Password</span>
            <input
              name="password"
              type="password"
              autoComplete="new-password"
              minLength={8}
              required
            />
          </label>
          {formError !== null ? (
            <p className="auth-form__error" role="alert">
              {formError}
            </p>
          ) : null}
          <button className="auth-form__submit" type="submit" disabled={mutation.isPending}>
            {mutation.isPending ? "Creating account..." : "Create account"}
          </button>
        </form>
        <p className="auth-card__footer">
          Already have an account? <Link to="/login">Sign in</Link>
        </p>
      </div>
    </section>
  );
}
