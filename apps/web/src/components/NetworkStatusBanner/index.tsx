import { useTranslation } from "react-i18next";
import { useNetworkStatus } from "../../hooks/use-network-status";
import styles from "./NetworkStatusBanner.module.css";

export function NetworkStatusBanner() {
  const { t } = useTranslation();
  const isOnline = useNetworkStatus();

  if (isOnline) {
    return null;
  }

  return (
    <div className={styles.root} role="status">
      {t("network.offline")}
    </div>
  );
}
