import { useTranslation } from "react-i18next";
import styles from "./InterimTranscript.module.css";

type InterimTranscriptProps = {
  text: string | null;
};

export function InterimTranscript({ text }: InterimTranscriptProps) {
  const { t } = useTranslation();

  if (text === null || text.trim().length === 0) {
    return null;
  }

  return (
    <p className={styles.root} role="status">
      {t("chat.listeningPrefix", { text })}
    </p>
  );
}
