import { useMutation } from "@tanstack/react-query";
import { useState, type ComponentProps } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router";
import { apiFetch, isTokenResponse, type TokenResponse } from "../../lib/api-client";
import { ApiError } from "../../lib/api-error";
import { setTokens } from "../../lib/auth-tokens";
import { readFormValue } from "../../lib/form-utils";
import authStyles from "../../styles/auth.module.css";

type LoginRequest = {
  email: string;
  password: string;
};

export function LoginPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [formError, setFormError] = useState<string | null>(null);
  const mutation = useMutation<TokenResponse, ApiError, LoginRequest>({
    mutationFn: async (payload) => {
      const body = await apiFetch<unknown>("/auth/login", {
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
      email: readFormValue(formData, "email"),
      password: readFormValue(formData, "password"),
    });
  };

  return (
    <section className={authStyles.page}>
      <div className={authStyles.card}>
        <p className="eyebrow">{t("auth.loginEyebrow")}</p>
        <h1>{t("auth.loginHeading")}</h1>
        <p className={authStyles.description}>{t("auth.loginDescription")}</p>
        <form className={authStyles.form} onSubmit={handleSubmit}>
          <label className={authStyles.field}>
            <span>{t("auth.email")}</span>
            <input className={authStyles.fieldInput} name="email" type="email" autoComplete="email" required />
          </label>
          <label className={authStyles.field}>
            <span>{t("auth.password")}</span>
            <input className={authStyles.fieldInput} name="password" type="password" autoComplete="current-password" required />
          </label>
          {formError !== null ? (
            <p className={authStyles.error} role="alert">
              {formError}
            </p>
          ) : null}
          <button className={authStyles.submit} type="submit" disabled={mutation.isPending}>
            {mutation.isPending ? t("auth.signingIn") : t("auth.signIn")}
          </button>
        </form>
        <p className={authStyles.footer}>
          {t("auth.needAccount")} <Link to="/register">{t("auth.createOne")}</Link>
        </p>
      </div>
    </section>
  );
}
