import { useId, useState } from "react";
import { useTranslation } from "react-i18next";
import styles from "./TextInput.module.css";

type TextInputProps = {
  disabled: boolean;
  onSend: (text: string) => Promise<void> | void;
};

export function TextInput({ disabled, onSend }: TextInputProps) {
  const { t } = useTranslation();
  const fieldId = useId();
  const [value, setValue] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const isBlocked = disabled || isSubmitting;

  const handleSubmit = async () => {
    const trimmedValue = value.trim();

    if (trimmedValue.length === 0 || isBlocked) {
      return;
    }

    setIsSubmitting(true);

    try {
      await onSend(trimmedValue);
      setValue("");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className={styles.root}>
      <label className={styles.field} htmlFor={fieldId}>
        <span className={styles.label}>{t("chat.messageLabel")}</span>
        <textarea
          className={styles.textarea}
          disabled={isBlocked}
          id={fieldId}
          onChange={(event) => {
            setValue(event.target.value);
          }}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              void handleSubmit();
            }
          }}
          placeholder={t("chat.messagePlaceholder")}
          rows={3}
          value={value}
        />
      </label>

      <button
        className={styles.send}
        disabled={isBlocked || value.trim().length === 0}
        onClick={() => {
          void handleSubmit();
        }}
        type="button"
      >
        {t("chat.send")}
      </button>
    </div>
  );
}
