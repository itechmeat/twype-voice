import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import styles from "./UpdatePrompt.module.css";

type UpdatePromptProps = {
  needRefresh: boolean;
  onUpdate: () => void;
  resetSignal: number;
};

export function UpdatePrompt({ needRefresh, onUpdate, resetSignal }: UpdatePromptProps) {
  const { t } = useTranslation();
  const [isDismissed, setIsDismissed] = useState(false);

  useEffect(() => {
    if (needRefresh) {
      setIsDismissed(false);
    }
  }, [needRefresh, resetSignal]);

  useEffect(() => {
    if (!needRefresh) {
      return undefined;
    }

    const revealPrompt = () => {
      setIsDismissed(false);
    };

    window.addEventListener("focus", revealPrompt);

    return () => {
      window.removeEventListener("focus", revealPrompt);
    };
  }, [needRefresh]);

  if (!needRefresh || isDismissed) {
    return null;
  }

  return (
    <section className={styles.root} role="status" aria-live="polite">
      <div className={styles.content}>
        <p className={styles.title}>{t("pwa.updateTitle")}</p>
        <p className={styles.body}>{t("pwa.updateBody")}</p>
      </div>
      <div className={styles.actions}>
        <button
          className={styles.secondary}
          type="button"
          onClick={() => {
            setIsDismissed(true);
          }}
        >
          {t("pwa.updateLater")}
        </button>
        <button className={styles.primary} type="button" onClick={onUpdate}>
          {t("pwa.updateNow")}
        </button>
      </div>
    </section>
  );
}
