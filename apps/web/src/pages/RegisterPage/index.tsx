import { useMutation } from "@tanstack/react-query";
import { useState, type ComponentProps } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router";
import { apiFetch } from "../../lib/api-client";
import { ApiError } from "../../lib/api-error";
import { readFormValue } from "../../lib/form-utils";
import authStyles from "../../styles/auth.module.css";

type RegisterRequest = {
  email: string;
  password: string;
};

type RegisterResponse = {
  email: string;
  message: string;
};

export function RegisterPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [formError, setFormError] = useState<string | null>(null);
  const mutation = useMutation<RegisterResponse, ApiError, RegisterRequest>({
    mutationFn: (payload) =>
      apiFetch<RegisterResponse>("/auth/register", {
        method: "POST",
        body: payload,
      }),
    onSuccess: (result) => {
      void navigate("/verify", {
        replace: true,
        state: { email: result.email },
      });
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
        <p className="eyebrow">{t("auth.registerEyebrow")}</p>
        <h1>{t("auth.registerHeading")}</h1>
        <p className={authStyles.description}>
          {t("auth.registerDescription")}
        </p>
        <form className={authStyles.form} onSubmit={handleSubmit}>
          <label className={authStyles.field}>
            <span>{t("auth.email")}</span>
            <input className={authStyles.fieldInput} name="email" type="email" autoComplete="email" required />
          </label>
          <label className={authStyles.field}>
            <span>{t("auth.password")}</span>
            <input
              className={authStyles.fieldInput}
              name="password"
              type="password"
              autoComplete="new-password"
              minLength={8}
              required
            />
          </label>
          {formError !== null ? (
            <p className={authStyles.error} role="alert">
              {formError}
            </p>
          ) : null}
          <button className={authStyles.submit} type="submit" disabled={mutation.isPending}>
            {mutation.isPending ? t("auth.creatingAccount") : t("auth.createAccount")}
          </button>
        </form>
        <p className={authStyles.footer}>
          {t("auth.haveAccount")} <Link to="/login">{t("auth.signIn")}</Link>
        </p>
      </div>
    </section>
  );
}
