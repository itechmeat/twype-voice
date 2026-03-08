import clsx from "clsx";
import { useTranslation } from "react-i18next";
import { NavLink, Navigate, Outlet } from "react-router";
import { useAuth } from "../../lib/use-auth";
import styles from "./ProtectedLayout.module.css";

function navLinkClassName({ isActive }: { isActive: boolean }): string {
  return clsx(styles.navLink, isActive && styles.navLinkActive);
}

export function ProtectedLayout() {
  const { t } = useTranslation();
  const { isAuthenticated, logout } = useAuth();

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return (
    <div className={styles.root}>
      <header className={styles.header}>
        <div className={styles.headerCopy}>
          <p className="eyebrow">{t("common.twype")}</p>
          <h1>{t("nav.workspace")}</h1>
        </div>
        <div className={styles.headerActions}>
          <nav aria-label={t("nav.primary")} className={styles.nav}>
            <NavLink className={navLinkClassName} end to="/">
              {t("nav.chat")}
            </NavLink>
            <NavLink className={navLinkClassName} to="/history">
              {t("nav.history")}
            </NavLink>
          </nav>
          <button className={styles.logout} onClick={logout} type="button">
            {t("nav.logout")}
          </button>
        </div>
      </header>
      <main className={styles.content}>
        <Outlet />
      </main>
    </div>
  );
}
