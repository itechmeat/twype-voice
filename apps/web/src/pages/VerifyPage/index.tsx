import { useMutation } from "@tanstack/react-query";
import { useState, type ComponentProps } from "react";
import { useTranslation } from "react-i18next";
import { Link, Navigate, useLocation, useNavigate } from "react-router";
import { apiFetch, isTokenResponse, type TokenResponse } from "../../lib/api-client";
import { ApiError } from "../../lib/api-error";
import { setTokens } from "../../lib/auth-tokens";
import { readFormValue } from "../../lib/form-utils";
import authStyles from "../../styles/auth.module.css";

type VerifyRequest = {
  email: string;
  code: string;
};

function resolveEmail(state: unknown): string | null {
  if (typeof state !== "object" || state === null || !("email" in state)) {
    return null;
  }
  const email = (state as Record<string, unknown>).email;
  return typeof email === "string" && email.length > 0 ? email : null;
}

export function VerifyPage() {
  const { t } = useTranslation();
  const location = useLocation();
  const navigate = useNavigate();
  const [formError, setFormError] = useState<string | null>(null);
  const email = resolveEmail(location.state);
  const mutation = useMutation<TokenResponse, ApiError, VerifyRequest>({
    mutationFn: async (payload) => {
      const body = await apiFetch<unknown>("/auth/verify", {
        method: "POST",
        body: payload,
      });
      if (!isTokenResponse(body)) {
        throw new ApiError(0, "Invalid token response from server");
      }
      return body;
    },
    onSuccess: (result) => {
      setTokens(result.access_token, result.refresh_token);
      void navigate("/", { replace: true });
    },
    onError: (error) => {
      setFormError(error.message);
    },
  });

  if (email === null) {
    return <Navigate to="/register" replace />;
  }

  const handleSubmit: NonNullable<ComponentProps<"form">["onSubmit"]> = (event) => {
    event.preventDefault();
    if (mutation.isPending) {
      return;
    }
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
    <section className={authStyles.page}>
      <div className={authStyles.card}>
        <p className="eyebrow">{t("auth.verifyEyebrow")}</p>
        <h1>{t("auth.verifyHeading")}</h1>
        <p className={authStyles.description}>
          {t("auth.verifyDescription", { email })}
        </p>
        <form className={authStyles.form} onSubmit={handleSubmit}>
          <label className={authStyles.field}>
            <span>{t("auth.code")}</span>
            <input
              className={authStyles.fieldInput}
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
            <p className={authStyles.error} role="alert">
              {formError}
            </p>
          ) : null}
          <button className={authStyles.submit} type="submit" disabled={mutation.isPending}>
            {mutation.isPending ? t("auth.verifying") : t("auth.verifyButton")}
          </button>
        </form>
        <p className={authStyles.footer}>
          {t("auth.wrongEmail")} <Link to="/register">{t("auth.createAnother")}</Link>
        </p>
      </div>
    </section>
  );
}
