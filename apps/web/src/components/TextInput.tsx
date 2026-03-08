import { useId, useState } from "react";

type TextInputProps = {
  disabled: boolean;
  onSend: (text: string) => Promise<void> | void;
};

export function TextInput({ disabled, onSend }: TextInputProps) {
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
    <div className="text-input">
      <label className="text-input__field" htmlFor={fieldId}>
        <span className="text-input__label">Message</span>
        <textarea
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
          placeholder="Type your message"
          rows={3}
          value={value}
        />
      </label>

      <button
        className="chat-primary-button text-input__send"
        disabled={isBlocked || value.trim().length === 0}
        onClick={() => {
          void handleSubmit();
        }}
        type="button"
      >
        Send
      </button>
    </div>
  );
}
