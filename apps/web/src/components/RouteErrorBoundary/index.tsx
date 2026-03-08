import { useTranslation } from "react-i18next";
import { Link, isRouteErrorResponse, useRouteError } from "react-router";
import styles from "./RouteErrorBoundary.module.css";

export function RouteErrorBoundary() {
  const { t } = useTranslation();
  const error = useRouteError();

  if (isRouteErrorResponse(error)) {
    return (
      <section className={styles.root}>
        <p className={styles.eyebrow}>{t("common.twype")}</p>
        <h1>{error.status === 404 ? t("error.notFound") : t("error.statusError", { status: error.status })}</h1>
        <p>{error.status === 404 ? t("error.notFoundMessage") : error.statusText}</p>
        <Link to="/">{t("common.goHome")}</Link>
      </section>
    );
  }

  const message = error instanceof Error ? error.message : t("error.unexpectedError");

  return (
    <section className={styles.root}>
      <p className={styles.eyebrow}>{t("common.twype")}</p>
      <h1>{t("error.generic")}</h1>
      <p>{message}</p>
      <Link to="/">{t("common.goHome")}</Link>
    </section>
  );
}
